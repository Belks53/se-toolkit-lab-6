#!/usr/bin/env python3
"""
agent.py — CLI agent with tools and agentic loop for wiki-based Q&A.
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# Load env vars from .env.agent.secret
env_path = Path(__file__).parent / ".env.agent.secret"
load_dotenv(env_path)

# Initialize LLM client
client = OpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_API_BASE"),
)

MODEL = os.getenv("LLM_MODEL", "qwen3-coder-plus")
SYSTEM_PROMPT = """You are a helpful assistant that answers questions using the project wiki.

You have access to these tools:
- list_files: List files in a directory
- read_file: Read the contents of a file

Strategy:
1. Use list_files to explore the wiki directory
2. Use read_file to find relevant information
3. Include the source file path and section in your answer

Always provide accurate source references (e.g., wiki/git-workflow.md#resolving-merge-conflicts).
"""

# Tool definitions for OpenAI function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the project repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root"
                    }
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
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root"
                    }
                },
                "required": ["path"]
            }
        }
    }
]

# Project root for security checks
PROJECT_ROOT = Path(__file__).parent.resolve()
MAX_ITERATIONS = 10


def log_debug(msg: str):
    """Print to stderr for debugging (not part of JSON output)."""
    print(f"[DEBUG] {msg}", file=sys.stderr)


def validate_path(path: str) -> tuple[bool, str]:
    """
    Validate that a path is safe and within project root.
    Returns (is_valid, error_message).
    """
    # Check for path traversal attempts
    if ".." in path or path.startswith("/"):
        return False, "Security error: path traversal not allowed"
    
    # Resolve the full path
    full_path = (PROJECT_ROOT / path).resolve()
    
    # Ensure it's within project root
    try:
        full_path.relative_to(PROJECT_ROOT)
    except ValueError:
        return False, "Security error: path outside project root"
    
    return True, ""


def read_file(path: str) -> str:
    """Read a file from the project repository."""
    is_valid, error = validate_path(path)
    if not is_valid:
        return error
    
    file_path = PROJECT_ROOT / path
    
    if not file_path.exists():
        return f"Error: File not found: {path}"
    
    if not file_path.is_file():
        return f"Error: Not a file: {path}"
    
    try:
        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {e}"


def list_files(path: str) -> str:
    """List files and directories at a given path."""
    is_valid, error = validate_path(path)
    if not is_valid:
        return error
    
    dir_path = PROJECT_ROOT / path
    
    if not dir_path.exists():
        return f"Error: Directory not found: {path}"
    
    if not dir_path.is_dir():
        return f"Error: Not a directory: {path}"
    
    try:
        entries = sorted([e.name for e in dir_path.iterdir()])
        return "\n".join(entries)
    except Exception as e:
        return f"Error listing directory: {e}"


def execute_tool(tool_name: str, args: dict) -> str:
    """Execute a tool and return the result."""
    log_debug(f"Executing tool: {tool_name} with args: {args}")
    
    if tool_name == "read_file":
        return read_file(args.get("path", ""))
    elif tool_name == "list_files":
        return list_files(args.get("path", ""))
    else:
        return f"Error: Unknown tool: {tool_name}"


def call_llm(messages: list) -> dict:
    """Call LLM and return response."""
    log_debug(f"Calling LLM with {len(messages)} messages")
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        temperature=0.1,
        timeout=60,
    )
    
    return response.choices[0].message


def run_agentic_loop(question: str) -> dict:
    """
    Run the agentic loop:
    1. Send question to LLM
    2. If tool calls, execute and feed back
    3. Repeat until answer or max iterations
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    
    tool_calls_log = []
    iterations = 0
    
    while iterations < MAX_ITERATIONS:
        iterations += 1
        log_debug(f"Iteration {iterations}/{MAX_ITERATIONS}")
        
        # Call LLM
        response = call_llm(messages)
        
        # Check if LLM wants to call tools
        if response.tool_calls:
            # Add the assistant's message with tool calls
            messages.append({
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    for tc in response.tool_calls
                ]
            })
            
            # Execute each tool call and add tool responses
            for tool_call in response.tool_calls:
                tool_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                result = execute_tool(tool_name, args)
                
                # Log the tool call
                tool_calls_log.append({
                    "tool": tool_name,
                    "args": args,
                    "result": result,
                })
                
                log_debug(f"Tool {tool_name} result: {result[:100]}...")
                
                # Add tool response to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })
            
            # Continue loop - LLM will process tool results
        else:
            # LLM provided final answer
            answer = response.content.strip()
            log_debug(f"Final answer: {answer[:100]}...")
            
            # Extract source from answer (look for wiki/...md#... pattern)
            source = ""
            import re
            source_match = re.search(r'(wiki/[\w-]+\.md(?:#[\w-]+)?)', answer)
            if source_match:
                source = source_match.group(1)
            
            return {
                "answer": answer,
                "source": source,
                "tool_calls": tool_calls_log,
            }
    
    # Max iterations reached
    log_debug("Max iterations reached")
    return {
        "answer": "I reached the maximum number of tool calls (10). Here's what I found:",
        "source": "",
        "tool_calls": tool_calls_log,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"Your question here\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    try:
        result = run_agentic_loop(question)
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)
    except Exception as e:
        log_debug(f"Error: {e}")
        print(json.dumps({"answer": "", "source": "", "tool_calls": [], "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
