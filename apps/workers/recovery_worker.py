"""
Mandate Gateway — Recovery Worker Process Entrypoint
Section M09 — Production Platform & Recovery Worker Separation
"""

from __future__ import annotations

import asyncio
import logging
import signal
from typing import Optional, Sequence

from apps.api.adapters.razorpay_adapter import MockRazorpayAdapter, RazorpayAdapterInterface
from apps.api.domain.recovery_engine import TransactionRecoveryService
from db.session import get_async_session_factory
from db.unit_of_work import AsyncUnitOfWork

logger = logging.getLogger("mandate_gateway.recovery_worker")


class RecoveryWorker:
    """
    Independent worker process for scanning stuck transactions and performing provider reconciliation.
    Guarantees fail-closed safety and atomicity via transaction row locking.
    """

    def __init__(
        self,
        stuck_threshold_seconds: int = 30,
        poll_interval_seconds: float = 5.0,
        adapter: Optional[RazorpayAdapterInterface] = None,
    ) -> None:
        self.stuck_threshold_seconds = stuck_threshold_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.adapter = adapter or MockRazorpayAdapter()
        self.recovery_service = TransactionRecoveryService(self.adapter)
        self.running = False

    async def process_batch(self) -> int:
        """Scan and reconcile stuck transactions."""
        session_factory = get_async_session_factory()
        if session_factory is None:
            return 0

        reconciled_count = 0
        async with AsyncUnitOfWork(session_factory) as uow:
            stuck_tx_ids: Sequence[str] = await self.recovery_service.scan_stuck_transactions(
                uow=uow, stuck_threshold_seconds=self.stuck_threshold_seconds
            )
            if not stuck_tx_ids:
                return 0

            logger.info(f"Recovery worker discovered {len(stuck_tx_ids)} stuck transaction(s).")
            for tx_id in stuck_tx_ids:
                try:
                    rec = await self.recovery_service.reconcile_transaction(uow, tx_id)
                    if rec.recovered:
                        reconciled_count += 1
                        logger.info(
                            f"Reconciled transaction {tx_id}: {rec.previous_state} -> {rec.final_state}"
                        )
                    else:
                        logger.warning(f"Transaction {tx_id} reconciliation pending: {rec.message}")
                except Exception as err:
                    logger.error(f"Failed to reconcile transaction {tx_id}: {err}")

            await uow.commit()
        return reconciled_count

    async def run(self) -> None:
        """Run continuous worker loop until stopped."""
        self.running = True
        logger.info("Recovery worker process started.")
        while self.running:
            try:
                count = await self.process_batch()
                if count == 0:
                    await asyncio.sleep(self.poll_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as err:
                logger.error(f"Error in recovery worker loop: {err}")
                await asyncio.sleep(self.poll_interval_seconds)
        logger.info("Recovery worker process stopped cleanly.")

    def stop(self) -> None:
        """Signal worker to stop running."""
        self.running = False


async def _main() -> None:
    worker = RecoveryWorker()

    loop = asyncio.get_running_loop()

    def handle_signal() -> None:
        logger.info("Received termination signal. Shutting down recovery worker...")
        worker.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            pass

    await worker.run()


if __name__ == "__main__":
    asyncio.run(_main())
