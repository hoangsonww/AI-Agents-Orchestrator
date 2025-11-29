"""Enhanced CLI communication utilities for robust agent interaction."""

import logging
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class CLICommunicator:
    """Robust CLI communication handler that supports multiple interaction patterns.

    This class handles:
    - Non-interactive command execution
    - File-based input/output (for CLIs that prefer files)
    - Streaming output capture
    - Proper error handling and retries
    """

    def __init__(self, command: str, logger: Optional[logging.Logger] = None):
        """Initializes the CLI communicator."""
        self.command = command
        self.logger = logger or logging.getLogger(__name__)
        self.temp_dir = tempfile.mkdtemp(prefix="ai-orchestrator-")

    def execute_with_prompt(
        self,
        prompt: str,
        method: str = "stdin",
        timeout: int = 300,
        working_dir: Optional[str] = None,
    ) -> Tuple[bool, str, str]:
        """Execute CLI command with a prompt using the specified method.

        Args:
            prompt: The prompt to send to the CLI
            method: Communication method ('stdin', 'file', 'arg', 'heredoc')
            timeout: Timeout in seconds
            working_dir: Working directory for execution

        Returns:
            Tuple of (success, stdout, stderr)
        """
        if method == "stdin":
            return self._execute_stdin(prompt, timeout, working_dir)
        elif method == "file":
            return self._execute_file_based(prompt, timeout, working_dir)
        elif method == "arg":
            return self._execute_argument(prompt, timeout, working_dir)
        elif method == "heredoc":
            return self._execute_heredoc(prompt, timeout, working_dir)
        else:
            raise ValueError(f"Unknown method: {method}")

    def _execute_stdin(
        self, prompt: str, timeout: int, working_dir: Optional[str]
    ) -> Tuple[bool, str, str]:
        """Execute by passing prompt via stdin with TTY support using script command."""
        try:
            return self._run_script_command(prompt, timeout, working_dir)
        except Exception as script_error:
            self.logger.debug(
                f"Script method failed, falling back to argument method: {script_error}"
            )
            return self._execute_argument(prompt, timeout, working_dir)

    def _run_script_command(
        self, prompt: str, timeout: int, working_dir: Optional[str]
    ) -> Tuple[bool, str, str]:
        """Run the script command with a prompt."""
        temp_file_path, input_file_path = None, None
        try:
            with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt") as temp_file:
                temp_file_path = temp_file.name
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as input_file:
                input_file_path = input_file.name
                input_file.write(prompt)

            script_cmd = f"cat {input_file_path} | script -q {temp_file_path} {self.command}"
            process = subprocess.Popen(
                script_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=working_dir,
            )
            stdout, stderr = process.communicate(timeout=timeout)

            with open(temp_file_path) as f:
                output_content = f.read()

            return process.returncode == 0, output_content or stdout, stderr
        finally:
            if temp_file_path:
                os.unlink(temp_file_path)
            if input_file_path:
                os.unlink(input_file_path)

    def _execute_file_based(
        self, prompt: str, timeout: int, working_dir: Optional[str]
    ) -> Tuple[bool, str, str]:
        """Execute using file-based input/output.

        Many AI CLIs can read prompts from files and write output to files.
        """
        input_file = Path(self.temp_dir) / "input.txt"
        output_file = Path(self.temp_dir) / "output.txt"

        try:
            # Write prompt to input file
            input_file.write_text(prompt)

            self.logger.debug(f"Executing {self.command} with file I/O")

            # Execute command
            # Common patterns: cli --input input.txt --output output.txt
            process = subprocess.Popen(
                [self.command, "--input", str(input_file), "--output", str(output_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=working_dir,
            )

            stdout, stderr = process.communicate(timeout=timeout)

            # Read output file if it exists
            if output_file.exists():
                output = output_file.read_text()
            else:
                output = stdout

            success = process.returncode == 0
            return success, output, stderr

        except subprocess.TimeoutExpired:
            process.kill()
            return False, "", f"Timeout after {timeout}s"

        except Exception as e:
            self.logger.error(f"File-based execution failed: {e}")
            return False, "", str(e)

        finally:
            # Cleanup
            if input_file.exists():
                input_file.unlink()
            if output_file.exists():
                output_file.unlink()

    def _execute_argument(
        self, prompt: str, timeout: int, working_dir: Optional[str]
    ) -> Tuple[bool, str, str]:
        """Execute by passing prompt as command-line argument."""
        try:
            self.logger.debug(f"Executing {self.command} with argument")

            env = os.environ.copy()
            if self.command in ["gemini", "gemini-cli"]:
                env["NODE_OPTIONS"] = "--no-warnings"

            cmd = self._build_command_for_tool(prompt)

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=working_dir,
                env=env,
            )

            stdout, stderr = process.communicate(timeout=timeout)
            success = process.returncode == 0

            if not success:
                self.logger.error(f"Command failed with stderr: {stderr[:500]}")

            return success, stdout, stderr
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out after {timeout}s")
            return False, "", f"Timeout after {timeout}s"
        except Exception as e:
            self.logger.error(f"Execution failed: {e}")
            return False, "", str(e)

    def _build_command_for_tool(self, prompt: str) -> List[str]:
        """Build the command and arguments for a specific CLI tool."""
        if self.command == "codex":
            return [self.command, "exec", prompt]
        if self.command in ["gemini", "gemini-cli"]:
            return [self.command, prompt]
        if self.command == "claude":
            return [self.command, "--print", prompt]
        return [self.command, prompt]

    def _execute_heredoc(
        self, prompt: str, timeout: int, working_dir: Optional[str]
    ) -> Tuple[bool, str, str]:
        """Execute using heredoc (for bash-based CLIs)."""
        try:
            # Create a shell script with heredoc
            script = f"""{self.command} << 'EOF'
{prompt}
EOF
"""

            process = subprocess.Popen(
                ["bash", "-c", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=working_dir,
            )

            stdout, stderr = process.communicate(timeout=timeout)
            success = process.returncode == 0

            return success, stdout, stderr

        except Exception as e:
            return False, "", str(e)

    def execute_in_workspace(
        self, prompt: str, workspace_dir: str, timeout: int = 300, method: str = "arg"
    ) -> Tuple[bool, str, str, List[str]]:
        """Execute CLI in a workspace directory and track file changes.

        This is useful for tools that modify files directly.

        Args:
            prompt: The prompt to send
            workspace_dir: Directory to execute in
            timeout: Timeout in seconds
            method: Communication method to use (default: 'arg')

        Returns:
            Tuple of (success, stdout, stderr, modified_files)
        """
        workspace_path = Path(workspace_dir)
        workspace_path.mkdir(parents=True, exist_ok=True)

        # Get initial file state
        initial_files = self._get_file_state(workspace_path)

        # Execute command in workspace using the specified method
        success, stdout, stderr = self.execute_with_prompt(prompt, method, timeout, workspace_dir)

        # Get modified files
        modified_files = self._get_modified_files(workspace_path, initial_files)

        return success, stdout, stderr, modified_files

    def _get_file_state(self, directory: Path) -> Dict[str, float]:
        """Get modification times of all files in directory."""
        file_state = {}

        for file_path in directory.rglob("*"):
            if file_path.is_file():
                try:
                    file_state[str(file_path)] = file_path.stat().st_mtime
                except Exception:
                    pass

        return file_state

    def _get_modified_files(self, directory: Path, initial_state: Dict[str, float]) -> List[str]:
        """Determine which files were modified or created."""
        modified = []

        for file_path in directory.rglob("*"):
            if not file_path.is_file():
                continue

            file_str = str(file_path)

            # New file
            if file_str not in initial_state:
                modified.append(file_str)
                continue

            # Modified file
            try:
                current_mtime = file_path.stat().st_mtime
                if current_mtime > initial_state[file_str]:
                    modified.append(file_str)
            except Exception:
                pass

        return modified

    def execute_with_retry(
        self, prompt: str, max_retries: int = 3, backoff: float = 1.0, **kwargs
    ) -> Tuple[bool, str, str]:
        """Execute with automatic retry on failure and method fallback.

        Args:
            prompt: The prompt to send
            max_retries: Maximum number of retry attempts
            backoff: Backoff multiplier between retries
            **kwargs: Additional arguments for execute_with_prompt

        Returns:
            Tuple of (success, stdout, stderr)
        """
        last_error = ""
        method = kwargs.get("method", "stdin")

        # Define fallback methods to try
        fallback_methods = []
        if method == "stdin":
            fallback_methods = ["stdin", "arg", "heredoc"]
        elif method == "arg":
            fallback_methods = ["arg", "stdin", "heredoc"]
        else:
            fallback_methods = [method, "stdin", "arg"]

        for attempt in range(max_retries):
            if attempt > 0:
                sleep_time = backoff * (2 ** (attempt - 1))
                self.logger.info(f"Retry attempt {attempt + 1}/{max_retries} after {sleep_time}s")
                time.sleep(sleep_time)

            # Try current method
            current_method = fallback_methods[min(attempt, len(fallback_methods) - 1)]
            kwargs["method"] = current_method

            self.logger.debug(f"Trying method: {current_method}")
            success, stdout, stderr = self.execute_with_prompt(prompt, **kwargs)

            if success:
                return success, stdout, stderr

            # Check if error is due to Node.js compatibility
            if "File is not defined" in stderr or "ReferenceError" in stderr:
                self.logger.warning(f"Node.js compatibility issue detected with {self.command}")
                # Try to provide helpful error message
                if attempt == max_retries - 1:
                    last_error = (
                        f"Node.js compatibility error. "
                        f"Try upgrading Node.js to v20+: nvm install 20 && nvm use 20\n"
                        f"Original error: {stderr}"
                    )
                    break

            last_error = stderr

        return False, "", f"Failed after {max_retries} attempts. Last error: {last_error}"

    def cleanup(self):
        """Clean up temporary directory."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def __del__(self):
        """Cleanup on deletion."""
        self.cleanup()


class AgentCLIRegistry:
    """Registry of known CLI tool communication patterns.

    This helps adapters know how to communicate with each tool.
    """

    PATTERNS = {
        "claude": {
            "command": "claude",
            "method": "arg",
            "prompt_flag": "--print",
            "supports_workspace": True,
            "output_format": "text",
        },
        "codex": {
            "command": "codex",
            "method": "arg",
            "supports_workspace": True,
            "output_format": "text",
        },
        "gemini": {
            "command": "gemini",
            "method": "arg",
            "prompt_flag": "--prompt",
            "supports_workspace": False,
            "output_format": "text",
        },
        "copilot": {
            "command": "copilot",
            "method": "arg",
            "supports_workspace": False,
            "output_format": "text",
        },
        "openai": {
            "command": "openai",
            "method": "arg",
            "prompt_flag": "--prompt",
            "supports_workspace": False,
            "output_format": "json",
        },
    }

    @classmethod
    def get_pattern(cls, tool_name: str) -> Dict[str, Any]:
        """Get communication pattern for a tool."""
        return cls.PATTERNS.get(
            tool_name, {"method": "stdin", "supports_workspace": True, "output_format": "text"}
        )

    @classmethod
    def register_pattern(cls, tool_name: str, pattern: Dict[str, Any]):
        """Register a new tool pattern."""
        cls.PATTERNS[tool_name] = pattern
