# Agent Architecture — Task 1, 2 & 3

## Overview

This document describes the architecture of `agent.py` — a CLI agent with three tools (`read_file`, `list_files`, `query_api`) and an agentic loop that answers questions using the project wiki, source code, and live backend API.

## LLM Provider

- **Provider:** Qwen Code API
- **Model:** `qwen3-coder-plus`
- **API Base:** `http://<vm-ip>:42005/v1` (OpenAI-compatible endpoint)
- **Authentication:** API key stored in `.env.agent.secret`

## Architecture

### Task 1: Basic LLM CLI

```
User question → agent.py → LLM API → JSON answer
```

### Task 2: Agentic Loop with Documentation Tools

```
Question ──▶ LLM ──▶ tool call? ──yes──▶ execute tool ──▶ back to LLM
                     │
                     no
                     │
                     ▼
                JSON output (answer + source + tool_calls)
```

### Task 3: System Agent with API Access

Added `query_api` tool to fetch live data from the backend.

## Components

### 1. CLI Argument Parsing
Reads the question from `sys.argv[1]`

### 2. Environment Loading
Loads credentials from two files:
- `.env.agent.secret` — LLM credentials (`LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`)
- `.env.docker.secret` — Backend API credentials (`LMS_API_KEY`)

Also reads optional `AGENT_API_BASE_URL` (defaults to `http://localhost:42002`).

### 3. LLM Client
OpenAI-compatible client using the `openai` Python package

### 4. Tools

#### `read_file(path: str) -> str`
- **Purpose:** Read file contents from the project repository
- **Parameters:** `path` — relative path from project root
- **Returns:** File contents as string, or error message
- **Security:** Blocks `../` path traversal, validates paths stay within project root

#### `list_files(path: str) -> str`
- **Purpose:** List files and directories at a given path
- **Parameters:** `path` — relative directory path from project root
- **Returns:** Newline-separated list of entries
- **Security:** Blocks `../` path traversal, validates paths stay within project root

#### `query_api(method: str, path: str, body: str = None) -> str`
- **Purpose:** Call the backend API to fetch data or perform actions
- **Parameters:**
  - `method` — HTTP method (GET, POST, PUT, DELETE, PATCH)
  - `path` — API endpoint path (e.g., `/items/`, `/analytics/scores`)
  - `body` — Optional JSON request body for POST/PUT
- **Returns:** JSON string with `status_code` and `body`
- **Authentication:** Uses `LMS_API_KEY` from environment via `Authorization: Bearer` header
- **Security:** Validates paths (must start with `/`, no `..`), validates HTTP methods

### 5. Agentic Loop

The agentic loop enables the LLM to iteratively gather information:

1. **Send question** — User question + tool definitions sent to LLM
2. **Parse response** — Check if LLM wants to call tools
3. **Execute tools** — If `tool_calls` present:
   - Execute each tool (`read_file`, `list_files`, or `query_api`)
   - Append results as `tool` role messages
   - Send back to LLM with accumulated context
4. **Repeat** — Continue until LLM provides final answer or max 10 iterations
5. **Output** — Return JSON with `answer`, `source`, and `tool_calls`

### 6. Response Formatter
Returns JSON with:
- `answer` — The LLM's final answer
- `source` — Reference to wiki file, source code, or API endpoint
- `tool_calls` — Array of all tool calls with `tool`, `args`, and `result`

## System Prompt Strategy

The system prompt guides the LLM to select the right tool for each question type:

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

## Data Flow

```python
Question (CLI arg)
    → run_agentic_loop()
    → messages = [system, user]
    → Loop:
        → call_llm(messages, tools)
        → If tool_calls: execute_tool() → messages.append(tool response)
        → If no tool_calls: extract answer + source → return JSON
```

## How to Run

```bash
# Task 1: Simple Q&A
uv run agent.py "What is 2+2?"

# Task 2: Wiki-based Q&A with tools
uv run agent.py "How do you resolve a merge conflict?"
uv run agent.py "What files are in the wiki?"

# Task 3: System and data questions
uv run agent.py "What framework does the backend use?"
uv run agent.py "How many items are in the database?"
uv run agent.py "Query the /analytics/scores endpoint for lab-04"
```

### Expected Output (Task 3)

```json
{
  "answer": "There are 120 items in the database.",
  "source": "",
  "tool_calls": [
    {
      "tool": "query_api",
      "args": {"method": "GET", "path": "/items/"},
      "result": "{\"status_code\": 200, \"body\": \"[...]\"}"
    }
  ]
}
```

## Environment Variables

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for query_api auth | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for query_api | Optional, defaults to `http://localhost:42002` |

Create `.env.agent.secret` and `.env.docker.secret` (both gitignored) with appropriate values.

## Output Format

- **stdout:** Single JSON line with `answer`, `source`, and `tool_calls`
- **stderr:** Debug logs prefixed with `[DEBUG]`
- **Exit code:** 0 on success, 1 on error

## Error Handling

- **Timeout:** 60 seconds for LLM requests
- **Invalid input:** Prints usage to stderr, exits with code 1
- **API errors:** Returns JSON with `error` field, exits with code 1
- **Max iterations:** Returns partial answer after 10 tool calls
- **Path security:** Returns error message for paths outside project root
- **API connection errors:** Returns status_code 0 with error message in body

## Security

- All paths validated to prevent `../` traversal
- Paths resolved using `Path.resolve()` and checked against project root
- Tool execution restricted to files within project directory
- API paths validated (must start with `/`, no `..`)
- HTTP methods restricted to safe set (GET, POST, PUT, DELETE, PATCH)
- `LMS_API_KEY` never exposed in tool results or answers

## Testing

Run regression tests:

```bash
uv run pytest tests/test_agent.py -v
```

Tests verify:
- Valid JSON output with required fields
- Debug logs go to stderr, not stdout
- Tool calls are executed and logged
- Source references are extracted correctly
- `query_api` tool is used for data questions

## Benchmark Evaluation

Run the local evaluation benchmark:

```bash
uv run run_eval.py
```

This runs 10 questions across all classes:
1. Wiki lookup (documentation questions)
2. System facts (framework, ports, status codes)
3. Data queries (item count, scores, analytics)
4. Bug diagnosis (analyze API errors)
5. Reasoning (explain request lifecycle)

## Lessons Learned

### Tool Design

1. **Clear descriptions matter:** The LLM needs precise tool descriptions to know when to use each tool. Initially, the `query_api` description was too vague, causing the agent to use `read_file` for data questions. After clarifying "Use for questions about database content, analytics, or system status," the LLM correctly chose `query_api`.

2. **Result truncation helps:** Long API responses (e.g., listing all items) can exceed the LLM context window. Truncating tool results to 500 characters prevents context overflow while still providing enough information for the LLM to answer.

3. **Error messages guide recovery:** When `query_api` returns a connection error, the LLM can explain what went wrong and suggest fixes. This makes the agent more helpful even when tools fail.

### Environment Variable Management

4. **Two-file separation is critical:** Keeping LLM credentials (`.env.agent.secret`) separate from backend credentials (`.env.docker.secret`) prevents confusion and follows security best practices. The autochecker injects different values for each, so hardcoding fails.

5. **Defaults matter:** Providing a sensible default for `AGENT_API_BASE_URL` (`http://localhost:42002`) allows local testing without configuration, while still allowing the autochecker to override it.

### Agentic Behavior

6. **Max iterations prevents loops:** The 10-iteration limit prevents infinite loops when the LLM can't find an answer. However, most questions complete in 2-5 iterations.

7. **Source extraction is imperfect:** The regex-based source extraction works for wiki files but may miss API-based answers. For Task 3, the `source` field is optional since API queries don't have a file reference.

8. **LLM can misinterpret schemas:** Initially, the LLM called `query_api` with `path: "items/"` (missing leading `/`). Adding "Must start with /" to the parameter description fixed this.

### Debugging Workflow

9. **Run single questions for debugging:** Using `uv run run_eval.py --index N` isolates failures and speeds up iteration.

10. **Check tool usage, not just answers:** The autochecker verifies that the correct tools were used. A correct answer with wrong tool usage still fails.

## Final Eval Score

After iteration, the agent passes all 10 local questions in `run_eval.py`. The autochecker bot tests additional hidden questions with LLM-based judging for open-ended answers.
