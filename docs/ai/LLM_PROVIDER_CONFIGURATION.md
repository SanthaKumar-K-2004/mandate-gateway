# RAZERPAY — LLM Provider Configuration Guide (M23)

## Provider Selection & Environment Variables

Provider selection is environment-driven via `LLM_PROVIDER`:

### 1. OpenRouter Integration
```bash
export LLM_PROVIDER=openrouter
export OPENROUTER_API_KEY=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
```
Uses fast/free models: `google/gemini-2.0-flash-exp:free`, `meta-llama/llama-3.3-70b-instruct:free`, `qwen/qwen-2.5-72b-instruct`.

### 2. Gemini REST API Integration
```bash
export LLM_PROVIDER=gemini
export GEMINI_API_KEY=AQ.Ab8RN6LDMNGJNzjMudBKcg8mS_MFgfZSTCLhBHJvnzMbhTlBbA
```
Uses Gemini 2.0 Flash (`gemini-2.0-flash`) or Gemini 1.5 Flash (`gemini-1.5-flash`).

### 3. OpenAI Integration
```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-proj-xxxx...
```

## Security & Credential Protection Rules
- `MockLLMProvider` is restricted to automated unit testing. Production startup (`APP_ENV=production`) strictly rejects `MockLLMProvider`.
- API keys are masked via `mask_secret` (e.g. `sk-or-v1-40...****`) and NEVER appear in logs, API responses, or repr outputs.
- Observability without credential exposure: `provider.check_health()` returns health state and masked key info.
