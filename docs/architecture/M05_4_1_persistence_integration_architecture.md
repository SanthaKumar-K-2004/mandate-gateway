# M05 / S05.4.1 — Persistence Integration Architecture & Transaction Boundary Mapping

## 1. Executive Summary

This document specifies the persistence integration architecture and transaction boundary mapping for migrating the **Mandate Gateway / Razorpay MCP** system from process-local in-memory state stores to the durable database repository layer completed in **M05.3** (`BaseRepository`, `MerchantRepository`, `MandateRepository`, `TransactionRepository`, `BudgetRepository`, `StepUpRepository`, `ReplayRepository`, `NonceRepository`, `AuditRepository`, `ReceiptRepository`).

The fundamental goal is to achieve **real production persistence and crash consistency** while preserving 100% of the security guarantees, fail-closed invariants, and deterministic authorization rules established in M00–M04.

---

## 2. In-Memory State Store Discovery & Inventory

A comprehensive code audit across `apps/`, `agent/`, and `db/` identified the following in-memory state structures currently operating in the codebase:

| Component File | Object / Class Name | Internal In-Memory State Fields | Synchronization | Classification |
| :--- | :--- | :--- | :--- | :--- |
| `apps/api/domain/audit_ledger.py` | `AuditLedger` | `self._events: list[AuditEvent]`, `self._head_hash: str` | `threading.RLock` | **Security Critical** — Audit Log |
| `apps/api/domain/budget_engine.py` | `BudgetEngine` | `self._budgets: dict[str, DailyBudget]`, `self._reservations: dict[str, BudgetReservation]` | `threading.RLock` + per-mandate `RLock` | **Security Critical** — Financial Budget |
| `apps/api/domain/execution_engine.py` | `PaymentExecutionService` | `self._transactions: dict[str, Transaction]`, `self._results: dict[str, ExecutionResult]`, `self._audit_events: list` | `threading.RLock` | **Security Critical** — Transaction Execution |
| `apps/api/domain/nonce_engine.py` | `NonceEngine` | `self._records: dict[str, NonceRecord]` | `threading.RLock` | **Security Critical** — Cryptographic Nonces |
| `apps/api/domain/replay_engine.py` | `ReplayProtectionEngine` | `self._records: dict[str, ReplayRecord]` | `threading.RLock` | **Security Critical** — Replay Protection |
| `apps/api/domain/step_up_engine.py` | `StepUpEngine` | `self._challenges: dict[str, StepUpChallengeRecord]` | `threading.RLock` | **Security Critical** — Human Step-Up Approval |
| `apps/api/domain/security_hardening.py` | `SlidingWindowRateLimiter` | `self._requests: dict[tuple, deque[float]]` | `threading.Lock` | **Security/Infrastructure** — Rate Limiting |
| `agent/stepup/manager.py` | `AgentStepUpManager` | `self._challenges: dict[str, AgentStepUpChallenge]`, `self._session_index: dict` | `threading.RLock` | **Agent Integration** — Human Challenge Proxy |
| `agent/tools/registry.py` | `ToolRegistry` | `self._tools: dict[str, ToolInterface]`, `self._invocation_counts: dict` | `threading.RLock` | **Agent Infrastructure** — Tool Masking |
| `agent/graph/state.py` | `AgentExecutionGraphState` | `self._pending_tool_call`, `self._proposal_payload` | `threading.RLock` | **Ephemeral** — Agent Turn Session |

---

## 3. Persistence Migration Matrix

The following matrix maps every domain component and state store to its durable PostgreSQL repository target, multi-worker locking strategy, and transaction boundary owner:

| Domain Component | Current State Mechanism | Security Critical? | Durable Repository Target | Migration Required? | Locking Strategy | Transaction Boundary Owner |
| :--- | :--- | :---: | :--- | :---: | :--- | :--- |
| **Merchant & Policy State** | In-memory Config DTOs | YES | `MerchantRepository` (`MerchantModel`, `MerchantPolicyModel`, `ProductModel`) | **YES** | `SELECT ... FOR UPDATE` on merchant/policy lookup | Service / Unit of Work Layer |
| **Mandate Lifecycle** | Pure DTOs / `BuyerMandate` | YES | `MandateRepository` (`MandateModel`) | **YES** | `SELECT ... FOR UPDATE` on mandate status & cap checks | Service / Unit of Work Layer |
| **Transaction State Machine** | `PaymentExecutionService._transactions` | YES | `TransactionRepository` (`TransactionModel`) | **YES** | `SELECT ... FOR UPDATE` on state transitions | Service / Unit of Work Layer |
| **Budget & Accounting** | `BudgetEngine._budgets` & `_reservations` | YES | `BudgetRepository` (`DailyBudgetModel`, `BudgetReservationModel`) | **YES** | `SELECT ... FOR UPDATE` on `DailyBudgetModel` | Service / Unit of Work Layer |
| **Human Step-Up Challenge** | `StepUpEngine._challenges` | YES | `StepUpRepository` (`StepUpChallengeModel`) | **YES** | `SELECT ... FOR UPDATE` on challenge approval/rejection | Service / Unit of Work Layer |
| **Replay Protection** | `ReplayProtectionEngine._records` | YES | `ReplayRepository` (`ReplayFingerprintModel`) | **YES** | DB PK Unique Constraint + Atomic Insert / Row Lock | Service / Unit of Work Layer |
| **Cryptographic Nonces** | `NonceEngine._records` | YES | `NonceRepository` (`NonceRecordModel`) | **YES** | DB PK Unique Constraint + `SELECT ... FOR UPDATE` | Service / Unit of Work Layer |
| **Cryptographic Audit Log** | `AuditLedger._events` | YES | `AuditRepository` (`AuditEventModel`) | **YES** | `SELECT ... FOR UPDATE` on latest event sequence | Service / Unit of Work Layer |
| **Action Receipts** | `PaymentExecutionService._audit_events` | YES | `ReceiptRepository` (`ActionReceiptModel`) | **YES** | FK Constraint + Atomic Insert | Service / Unit of Work Layer |
| **Sliding Rate Limiter** | `SlidingWindowRateLimiter._requests` | NO (Infrastructure) | Redis (via `db/redis.py`) or Process-local | **OPTIONAL** | Redis atomic key TTL / Lua script | API Gateway Middleware |
| **Tool Registry & Counters** | `ToolRegistry._invocation_counts` | NO (Infrastructure) | Static Registry + Redis for Session Counts | **NO** | Process `RLock` / Redis counter | Agent Orchestrator |

---

## 4. Transaction Boundary Design

### 4.1 `AsyncSession` Lifecycle & Ownership
1. **Creation**: `AsyncSession` instances are instantiated at the entry point of top-level application service calls (or via FastAPI request scope dependency injection `get_db_session()`).
2. **Ownership Layer**: Session lifecycle and transaction ownership belong **strictly to the Application Service / Unit of Work Layer** (`AsyncUnitOfWork`).
3. **Commit & Rollback Rules**:
   - `begin()`: Executed by the Application Service / Unit of Work upon entering a multi-repository operation.
   - `commit()`: Executed **ONLY** by the Application Service / Unit of Work after all repository operations in the phase succeed.
   - `rollback()`: Executed **ONLY** by the Application Service / Unit of Work on any policy rejection, validation failure, domain exception, or database infrastructure error.
   - **Repositories NEVER call `commit()` or `rollback()`.** Repositories call `await self._session.flush()` to surface database constraint failures into Python exceptions without committing the transaction.

### 4.2 Atomic Transaction Boundaries

#### Phase A: Authorization & Budget Reservation (Single Atomic Transaction)
The entire payment proposal authorization and budget reservation flow MUST execute inside **one atomic database transaction**:

```text
[Begin DB Transaction]
   │
   ├── 1. Lock & Fetch Mandate (MandateRepository.get_by_id_for_update)
   ├── 2. Lock & Fetch Merchant & Policy (MerchantRepository.get_merchant_by_account_for_update)
   ├── 3. Register & Validate Replay Fingerprint (ReplayRepository.register_fingerprint)
   ├── 4. Consume Execution Nonce (NonceRepository.consume_nonce)
   ├── 5. Lock Daily Budget & Reserve Amount (BudgetRepository.reserve_budget)
   ├── 6. Create Transaction in PROPOSED/AUTHORIZED state (TransactionRepository.create_transaction)
   ├── 7. If Step-Up Required: Create Challenge (StepUpRepository.create_challenge)
   └── 8. Append Audit Event (AuditRepository.append_event)
   │
[Commit DB Transaction]  <-- If any step fails -> Rollback DB Transaction (Zero partial state!)
```

#### Phase B: External Payment Execution & Settlement (Separated DB Transactions)
External HTTP payment gateway calls (Razorpay API adapter) MUST execute **outside of database transaction locks** to prevent holding database connections open during network I/O:

```text
[Step 1: Atomic Pre-Execution DB Transaction]
   ├── Lock Transaction & Update State: AUTHORIZED -> EXECUTING
   ├── Append Audit Event (PAYMENT_EXECUTING)
   └── Commit DB Transaction

[Step 2: External Gateway HTTP Request (NO DB LOCK HELD)]
   └── Invoke Razorpay Adapter HTTP API (e.g. create_order / capture)

[Step 3: Atomic Post-Execution DB Transaction]
   ├── IF Payment SUCCESS:
   │     ├── Update Transaction State: EXECUTING -> SUCCESS
   │     ├── Commit Budget Reservation: RESERVED -> COMMITTED (BudgetRepository)
   │     ├── Store Signed Ed25519 Action Receipt (ReceiptRepository)
   │     ├── Append Audit Event (PAYMENT_SUCCESS)
   │     └── Commit DB Transaction
   ├── IF Payment FAILURE:
   │     ├── Update Transaction State: EXECUTING -> FAILURE
   │     ├── Release Budget Reservation: RESERVED -> RELEASED (BudgetRepository)
   │     ├── Append Audit Event (PAYMENT_FAILED)
   │     └── Commit DB Transaction
   └── IF Provider UNKNOWN (Timeout/Crash):
         ├── Keep Transaction in EXECUTING state with provider_status UNKNOWN
         └── Handled asynchronously by RecoveryReconciliationEngine
```

---

## 5. Security & Concurrency Analysis

### 5.1 Security Invariants Preserved Across Migration
1. **Fail-Closed Isolation**: Any database disconnect, row lock timeout, or constraint violation immediately raises an exception and triggers transaction rollback.
2. **Multi-Tenant Buyer/Merchant Isolation**: Query parameters filter strictly by `merchant_id` and `buyer_id`. Foreign key constraints prevent cross-tenant record leakage.
3. **Single-Use Cryptographic Nonces & Replay Protection**: Database primary key unique constraints on `nonce_value` and `fingerprint` eliminate race condition bypasses across multi-worker deployments.
4. **Human Step-Up Approval Boundary**: Step-Up challenges require explicit human confirmation. State transitions (`PENDING` -> `APPROVED` / `REJECTED`) operate under row locks with `LLM != APPROVER` validation.
5. **Financial Budget Overspend Prevention**: `DailyBudgetModel` rows are locked with `SELECT ... FOR UPDATE` during budget calculation, guaranteeing `spent + reserved + requested <= daily_limit` holds under concurrent worker requests.
6. **Audit Hash-Chain Integrity**: Audit sequence numbers advance monotonically under latest event row lock, guaranteeing unbroken SHA-256 hash chains (`previous_hash = prior event_hash`).
7. **Action Receipt Non-Repudiation**: Ed25519 signatures and canonical payload hashes are persisted immutably and verified offline.

### 5.2 Multi-Worker Concurrency Controls
- **`SELECT ... FOR UPDATE`**: Utilized for Mandate, Budget, Step-Up Challenge, Nonce, and Transaction state transitions.
- **Database Unique Constraints**: `replay_fingerprints.fingerprint`, `nonce_records.nonce_value`, `audit_events.sequence_number`, `action_receipts.receipt_id`.
- **Unit of Work Pattern**: Single atomic commit per application phase.

---

## 6. Migration Test Plan & Phased Strategy

### 6.1 Required Test Coverage Matrix
- **Unit Tests**: Verify repository dependency injection, model mapping, and method contracts.
- **Integration Tests**: Verify database persistence against SQLite in-memory and PostgreSQL.
- **Security Regression Tests**: Verify fail-closed behavior, zero mutation escape hatches, and controlled security failure proofs (Mutations A, B, C, D, E).
- **Multi-Worker Concurrency Tests**: Verify 10-worker parallel requests for nonces, replays, step-up approvals, budget reservations, and audit append logs.
- **Rollback Tests**: Verify transaction rollbacks leave zero partial DB state.
- **Crash / Restart Persistence Tests**: Verify state survives session re-creation and process restarts.

### 6.2 Recommended Sub-Module Order (S05.4.2 Onward)
1. **S05.4.2**: Unit of Work & Transaction Manager Abstraction (`AsyncUnitOfWork`).
2. **S05.4.3**: Merchant & Mandate Domain Engine Migration to Persistence.
3. **S05.4.4**: Budget & Step-Up Domain Engine Migration to Persistence.
4. **S05.4.5**: Replay & Nonce Domain Engine Migration to Persistence.
5. **S05.4.6**: Execution & Audit/Receipt Service Migration to Persistence.
6. **S05.4.7**: Full End-to-End Persistence Integration & Multi-Worker Verification.

---

## 7. Status & Quality Gate Compliance

- **Architecture Plan**: Documented in [`docs/architecture/M05_4_1_persistence_integration_architecture.md`](file:///home/santhakumar/Desktop/Raserpay/docs/architecture/M05_4_1_persistence_integration_architecture.md).
- **Existing M00–M04 Codebase**: 100% UNCHANGED.
- **`PROJECT_CONTEXT.md` SHA-256**: `2b62d52aa707bc9bb5df60d93b04f60933562e69af8068c46cc3b6cdc2eb670a` (INTACT).
- **Automated Test Suite**: 500 / 500 PASS.
