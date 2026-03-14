# Plan: Task 3 - The System Agent

## Overview
Extend agent.py with a `query_api` tool to query the deployed backend API and answer questions about system state and data.

## New Tool: `query_api`

### Purpose
Call the deployed backend API to fetch real-time data (items, analytics, etc.)

### Parameters
- `method` (string) — HTTP method: GET, POST, PUT, DELETE
- `path` (string) — API endpoint path (e.g., `/items/`, `/analytics/scores`)
- `body` (string, optional) — JSON request body for POST/PUT

### Returns
JSON string with:
- `status_code` — HTTP status code
- `body` — Response body (parsed JSON or text)

### Authentication
- Use `LMS_API_KEY` from `.env.docker.secret`
- Send as `Authorization: Bearer <LMS_API_KEY>` header

### Implementation
```python
def query_api(method: str, path: str, body: str = None) -> str:
    """Call the backend API with authentication."""
    import httpx
    
    api_base = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")
    lms_api_key = os.getenv("LMS_API_KEY")
    
    url = f"{api_base}{path}"
    headers = {"Authorization": f"Bearer {lms_api_key}"}
    
    if body:
        headers["Content-Type"] = "application/json"
    
    response = httpx.request(
        method=method,
        url=url,
        headers=headers,
        json=json.loads(body) if body else None,
        timeout=30,
    )
    
    return json.dumps({
        "status_code": response.status_code,
        "body": response.text,
    })
```

## Tool Schema (OpenAI Function Calling)

```python
{
    "type": "function",
    "function": {
        "name": "query_api",
        "description": "Call the backend API to fetch data or perform actions. Use for questions about database content, analytics, or system status.",
        "parameters": {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "description": "HTTP method (GET, POST, PUT, DELETE)"
                },
                "path": {
                    "type": "string",
                    "description": "API endpoint path (e.g., /items/, /analytics/scores)"
                },
                "body": {
                    "type": "string",
                    "description": "JSON request body (optional, for POST/PUT)"
                }
            },
            "required": ["method", "path"]
        }
    }
}
```

## Environment Variables

The agent must read all configuration from environment variables:

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for query_api auth | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for query_api | Optional, defaults to `http://localhost:42002` |

Update agent.py to load these at startup.

## System Prompt Update

Update the system prompt to guide tool selection:

```
You are a helpful assistant that answers questions using:
- The project wiki (for documentation)
- The backend API (for live data)
- Source code files (for implementation details)

Available tools:
- list_files: List files in a directory
- read_file: Read the contents of a file
- query_api: Call the backend API

Tool selection strategy:
1. For documentation questions (how-to, workflows, concepts) → use list_files and read_file on wiki/
2. For data questions (how many items, scores, analytics) → use query_api
3. For system questions (framework, ports, endpoints) → use read_file on source code or query_api
4. For bug diagnosis → use read_file on relevant source files

Always provide accurate source references when using wiki or code files.
For API queries, include the endpoint path in your answer.
```

## Agentic Loop

No changes to the loop structure — just add `query_api` to the TOOLS list.

## Security

- Validate API paths: reject paths with `..` or outside `/` prefix
- Only allow HTTP methods: GET, POST, PUT, DELETE, PATCH
- Never expose LMS_API_KEY in tool results or answers

## Benchmark Evaluation

Run the local evaluation:

```bash
uv run run_eval.py
```

Expected question types:
1. Wiki lookup (e.g., branch protection steps)
2. System facts (e.g., web framework, ports)
3. Data queries (e.g., item count, scores)
4. Bug diagnosis (e.g., analyze API errors)
5. Reasoning (e.g., explain request lifecycle)

### Iteration Strategy

1. Run `run_eval.py` to get initial score
2. For each failure:
   - Check if wrong tool was used → improve system prompt
   - Check if tool returned error → fix implementation
   - Check if answer doesn't match keywords → adjust phrasing
3. Re-run until all 10 questions pass

## Testing

Add 2 regression tests:
1. `"What framework does the backend use?"` → expects `read_file` tool, source references backend code
2. `"How many items are in the database?"` → expects `query_api` tool with GET /items/

## Deliverables

1. `plans/task-3.md` — this plan with benchmark results added
2. `agent.py` — query_api tool, env var loading, updated system prompt
3. `AGENT.md` — documentation with lessons learned (200+ words)
4. 2 new regression tests
5. Pass all 10 questions in `run_eval.py`
