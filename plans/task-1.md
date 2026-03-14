# Plan: Task 1 - Call an LLM from Code

## LLM Provider
- Provider: Qwen Code API (или OpenRouter)
- Model: qwen3-coder-plus
- API Base: https://api.qwen.ai/v1 (пример)

## Architecture
1. Parse CLI argument (question)
2. Load env vars from .env.agent.secret
3. Build OpenAI-compatible request to LLM
4. Parse response, extract answer text
5. Output JSON: {"answer": "...", "tool_calls": []}
6. All logs → stderr, JSON → stdout

## Error handling
- Timeout 60s
- Exit code 0 on success, non-zero on error
- Validate JSON output before printing