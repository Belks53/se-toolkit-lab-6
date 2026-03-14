"""Regression tests for agent.py.

These tests run the agent CLI as a subprocess and validate the JSON output.
Run with: uv run pytest tests/test_agent.py -v
"""

import json
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).parent.parent
AGENT_PATH = ROOT_DIR / "agent.py"


class TestAgentOutput:
    """Tests for agent.py JSON output structure."""

    def test_agent_returns_valid_json_with_required_fields(self):
        """Test that agent.py outputs valid JSON with 'answer' and 'tool_calls' fields."""
        question = "What is 2+2?"

        result = subprocess.run(
            ["uv", "run", str(AGENT_PATH), question],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Exit code should be 0 on success
        assert result.returncode == 0, f"Agent failed with: {result.stderr}"

        # Stdout should be valid JSON
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise AssertionError(f"Agent output is not valid JSON: {e}\nStdout: {result.stdout}")

        # Check required fields
        assert "answer" in output, "Missing 'answer' field in output"
        assert "tool_calls" in output, "Missing 'tool_calls' field in output"

        # Answer should be a non-empty string
        assert isinstance(output["answer"], str), "'answer' should be a string"
        assert len(output["answer"]) > 0, "'answer' should not be empty"

        # tool_calls should be a list (empty for Task 1)
        assert isinstance(output["tool_calls"], list), "'tool_calls' should be a list"

    def test_agent_logs_debug_to_stderr(self):
        """Test that debug output goes to stderr, not stdout."""
        question = "Hi"

        result = subprocess.run(
            ["uv", "run", str(AGENT_PATH), question],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Stdout should only contain JSON (no debug logs)
        assert "[DEBUG]" not in result.stdout, "Debug logs should not appear in stdout"

        # Stderr should contain debug logs
        assert "[DEBUG]" in result.stderr, "Debug logs should be printed to stderr"


class TestAgentTools:
    """Tests for agent.py tool-calling functionality (Task 2)."""

    def test_agent_uses_read_file_tool_for_wiki_question(self):
        """Test that agent uses read_file tool when answering wiki questions."""
        question = "What is Git?"

        result = subprocess.run(
            ["uv", "run", str(AGENT_PATH), question],
            capture_output=True,
            text=True,
            timeout=90,
        )

        # Exit code should be 0 on success
        assert result.returncode == 0, f"Agent failed with: {result.stderr}"

        # Parse JSON output
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise AssertionError(f"Agent output is not valid JSON: {e}\nStdout: {result.stdout}")

        # Check required fields
        assert "answer" in output, "Missing 'answer' field in output"
        assert "source" in output, "Missing 'source' field in output"
        assert "tool_calls" in output, "Missing 'tool_calls' field in output"

        # Should have used read_file tool
        tool_names = [tc["tool"] for tc in output["tool_calls"]]
        assert "read_file" in tool_names, "Expected read_file to be called"

        # Source should reference git.md
        assert "git.md" in output["source"], \
            f"Expected source to reference git.md, got: {output['source']}"

    def test_agent_uses_list_files_tool(self):
        """Test that agent uses list_files tool when asked about directory contents."""
        question = "What files are in the wiki directory?"

        result = subprocess.run(
            ["uv", "run", str(AGENT_PATH), question],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Exit code should be 0 on success
        assert result.returncode == 0, f"Agent failed with: {result.stderr}"

        # Parse JSON output
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise AssertionError(f"Agent output is not valid JSON: {e}\nStdout: {result.stdout}")

        # Check required fields
        assert "answer" in output, "Missing 'answer' field in output"
        assert "tool_calls" in output, "Missing 'tool_calls' field in output"

        # Should have used list_files tool
        tool_names = [tc["tool"] for tc in output["tool_calls"]]
        assert "list_files" in tool_names, "Expected list_files to be called"

        # Verify tool result contains expected wiki files
        list_files_result = next(
            (tc["result"] for tc in output["tool_calls"] if tc["tool"] == "list_files"),
            ""
        )
        assert "git-workflow.md" in list_files_result, \
            "Expected list_files result to contain git-workflow.md"
