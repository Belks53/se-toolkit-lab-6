# Plan: Task 2 - The Documentation Agent

## Overview
Extend agent.py with tools (`read_file`, `list_files`) and an agentic loop to answer questions using the project wiki.

## Tool Definitions

### `read_file`
- **Purpose:** Read file contents from the project repository
- **Parameters:** `path` (string) — relative path from project root
- **Returns:** File contents as string, or error message
- **Security:** Block `../` path traversal, ensure path stays within project root

### `list_files`
- **Purpose:** List files/directories at a given path
- **Parameters:** `path` (string) — relative directory path from project root
- **Returns:** Newline-separated list of entries
- **Security:** Block `../` path traversal, ensure path stays within project root

## Tool Schema (OpenAI Function Calling)

Define tools using OpenAI's function-calling format:

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the project repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path from project root"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative directory path from project root"}
                },
                "required": ["path"]
            }
        }
    }
]
```

## Agentic Loop

```
1. Send user question + tool definitions to LLM
2. Parse response:
   - If LLM returns tool_calls:
     a. Execute each tool (read_file or list_files)
     b. Append tool results as "tool" role messages
     c. Send back to LLM with accumulated context
     d. Repeat (max 10 iterations)
   - If LLM returns text answer (no tool_calls):
     a. Extract answer and source
     b. Output JSON and exit
3. If max iterations (10) reached → return best answer available
```

## System Prompt Strategy

Tell the LLM:
- Use `list_files` to discover wiki files
- Use `read_file` to find specific information
- Always include source reference (file path + section anchor) in the answer
- Call tools step by step, not all at once

Example system prompt:
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

## Output Format

```json
{
  "answer": "...",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "..."},
    {"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": "..."}
  ]
}
```

## Security Considerations

- Validate all paths: reject `../` or absolute paths
- Use `Path.resolve()` to ensure paths stay within project root
- Return error message if path is invalid

## Error Handling

- File not found → return error in tool result, continue loop
- Invalid path → return security error
- LLM timeout → exit with error after 60s
- Max iterations → return partial answer with tool_calls made

## Testing

Add 2 regression tests:
1. Question: "How do you resolve a merge conflict?" → expects `read_file` in tool_calls, `wiki/git-workflow.md` in source
2. Question: "What files are in the wiki?" → expects `list_files` in tool_calls
