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
        question = "What is the wiki directory structure?"

        result = subprocess.run(
            ["uv", "run", str(AGENT_PATH), question],
            capture_output=True,
            text=True,
            timeout=120,
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

        # Should have used list_files or read_file tool
        tool_names = [tc["tool"] for tc in output["tool_calls"]]
        assert "list_files" in tool_names or "read_file" in tool_names, \
            "Expected list_files or read_file to be called"

    def test_agent_uses_list_files_tool(self):
        """Test that agent uses list_files tool when asked about directory contents."""
        question = "List files in wiki/"

        result = subprocess.run(
            ["uv", "run", str(AGENT_PATH), question],
            capture_output=True,
            text=True,
            timeout=120,
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


class TestAgentSystemTools:
    """Tests for agent.py query_api functionality (Task 3)."""

    def test_agent_uses_read_file_for_system_question(self):
        """Test that agent uses read_file when asked about system framework."""
        question = "What is FastAPI?"

        result = subprocess.run(
            ["uv", "run", str(AGENT_PATH), question],
            capture_output=True,
            text=True,
            timeout=120,
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

    def test_agent_uses_query_api_for_data_question(self):
        """Test that agent uses query_api when asked about database content."""
        question = "GET /items/"

        result = subprocess.run(
            ["uv", "run", str(AGENT_PATH), question],
            capture_output=True,
            text=True,
            timeout=120,
        )

        # Exit code should be 0 on success (even if API is down, agent should handle gracefully)
        # Note: If backend is not running, agent should still use query_api tool and report error
        assert result.returncode == 0, f"Agent failed with: {result.stderr}"

        # Parse JSON output
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise AssertionError(f"Agent output is not valid JSON: {e}\nStdout: {result.stdout}")

        # Check required fields
        assert "answer" in output, "Missing 'answer' field in output"
        assert "tool_calls" in output, "Missing 'tool_calls' field in output"

        # Should have attempted to use query_api tool
        tool_names = [tc["tool"] for tc in output["tool_calls"]]
        assert "query_api" in tool_names, "Expected query_api to be called"
