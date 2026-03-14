# Agent Architecture — Task 1 & 2

## Overview

This document describes the architecture of `agent.py` — a CLI agent with tools and an agentic loop that answers questions using the project wiki.

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

### Task 2: Agentic Loop with Tools

```
Question ──▶ LLM ──▶ tool call? ──yes──▶ execute tool ──▶ back to LLM
                     │
                     no
                     │
                     ▼
                JSON output (answer + source + tool_calls)
```

## Components

### 1. CLI Argument Parsing
Reads the question from `sys.argv[1]`

### 2. Environment Loading
Loads LLM credentials from `.env.agent.secret`

### 3. LLM Client
OpenAI-compatible client using the `openai` Python package

### 4. Tools (Task 2)

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

### 5. Agentic Loop (Task 2)

The agentic loop enables the LLM to iteratively gather information:

1. **Send question** — User question + tool definitions sent to LLM
2. **Parse response** — Check if LLM wants to call tools
3. **Execute tools** — If `tool_calls` present:
   - Execute each tool (`read_file` or `list_files`)
   - Append results as `tool` role messages
   - Send back to LLM with accumulated context
4. **Repeat** — Continue until LLM provides final answer or max 10 iterations
5. **Output** — Return JSON with `answer`, `source`, and `tool_calls`

### 6. Response Formatter
Returns JSON with:
- `answer` — The LLM's final answer
- `source` — Wiki file reference (e.g., `wiki/git-workflow.md#resolving-merge-conflicts`)
- `tool_calls` — Array of all tool calls with `tool`, `args`, and `result`

## System Prompt Strategy

The system prompt guides the LLM to:
- Use `list_files` to discover wiki files
- Use `read_file` to find specific information
- Always include source references in answers
- Call tools step by step, not all at once

```
You are a helpful assistant that answers questions using the project wiki.

You have access to these tools:
- list_files: List files in a directory
- read_file: Read the contents of a file

Strategy:
1. Use list_files to explore the wiki directory
2. Use read_file to find relevant information
3. Include the source file path and section in your answer

Always provide accurate source references (e.g., wiki/git-workflow.md#resolving-merge-conflicts).
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
```

### Expected Output (Task 2)

```json
{
  "answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.",
  "source": "wiki/git-workflow.md",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git-workflow.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "..."
    }
  ]
}
```

## Environment Variables

Create `.env.agent.secret` (gitignored) with:

```text
LLM_API_KEY=your-api-key-here
LLM_API_BASE=http://<vm-ip>:42005/v1
LLM_MODEL=qwen3-coder-plus
```

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

## Security

- All paths validated to prevent `../` traversal
- Paths resolved using `Path.resolve()` and checked against project root
- Tool execution restricted to files within project directory

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
