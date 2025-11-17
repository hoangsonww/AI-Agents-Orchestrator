"""
Enhanced CLI communication utilities for robust agent interaction.
"""

import subprocess
import tempfile
import os
import time
import logging
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import json


class CLICommunicator:
    """
    Robust CLI communication handler that supports multiple interaction patterns.

    This class handles:
    - Non-interactive command execution
    - File-based input/output (for CLIs that prefer files)
    - Streaming output capture
    - Proper error handling and retries
    """

    def __init__(self, command: str, logger: Optional[logging.Logger] = None):
        self.command = command
        self.logger = logger or logging.getLogger(__name__)
        self.temp_dir = tempfile.mkdtemp(prefix='ai-orchestrator-')

    def execute_with_prompt(
        self,
        prompt: str,
        method: str = 'stdin',
        timeout: int = 300,
        working_dir: Optional[str] = None
    ) -> Tuple[bool, str, str]:
        """
        Execute CLI command with a prompt using the specified method.

        Args:
            prompt: The prompt to send to the CLI
            method: Communication method ('stdin', 'file', 'arg', 'heredoc')
            timeout: Timeout in seconds
            working_dir: Working directory for execution

        Returns:
            Tuple of (success, stdout, stderr)
        """
        if method == 'stdin':
            return self._execute_stdin(prompt, timeout, working_dir)
        elif method == 'file':
            return self._execute_file_based(prompt, timeout, working_dir)
        elif method == 'arg':
            return self._execute_argument(prompt, timeout, working_dir)
        elif method == 'heredoc':
            return self._execute_heredoc(prompt, timeout, working_dir)
        else:
            raise ValueError(f"Unknown method: {method}")

    def _execute_stdin(
        self,
        prompt: str,
        timeout: int,
        working_dir: Optional[str]
    ) -> Tuple[bool, str, str]:
        """Execute by passing prompt via stdin."""
        try:
            self.logger.debug(f"Executing {self.command} with stdin input")

            process = subprocess.Popen(
                [self.command],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=working_dir
            )

            stdout, stderr = process.communicate(input=prompt, timeout=timeout)
            success = process.returncode == 0

            return success, stdout, stderr

        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out after {timeout}s")
            process.kill()
            stdout, stderr = process.communicate()
            return False, stdout, f"Timeout after {timeout}s\n{stderr}"

        except Exception as e:
            self.logger.error(f"Execution failed: {e}")
            return False, "", str(e)

    def _execute_file_based(
        self,
        prompt: str,
        timeout: int,
        working_dir: Optional[str]
    ) -> Tuple[bool, str, str]:
        """
        Execute using file-based input/output.

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
                [self.command, '--input', str(input_file), '--output', str(output_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=working_dir
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
        self,
        prompt: str,
        timeout: int,
        working_dir: Optional[str]
    ) -> Tuple[bool, str, str]:
        """Execute by passing prompt as command-line argument."""
        try:
            self.logger.debug(f"Executing {self.command} with argument")

            # Common patterns: cli "prompt" or cli --prompt "prompt"
            process = subprocess.Popen(
                [self.command, prompt],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=working_dir
            )

            stdout, stderr = process.communicate(timeout=timeout)
            success = process.returncode == 0

            return success, stdout, stderr

        except Exception as e:
            return False, "", str(e)

    def _execute_heredoc(
        self,
        prompt: str,
        timeout: int,
        working_dir: Optional[str]
    ) -> Tuple[bool, str, str]:
        """Execute using heredoc (for bash-based CLIs)."""
        try:
            # Create a shell script with heredoc
            script = f"""{self.command} << 'EOF'
{prompt}
EOF
"""

            process = subprocess.Popen(
                ['bash', '-c', script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=working_dir
            )

            stdout, stderr = process.communicate(timeout=timeout)
            success = process.returncode == 0

            return success, stdout, stderr

        except Exception as e:
            return False, "", str(e)

    def execute_in_workspace(
        self,
        prompt: str,
        workspace_dir: str,
        timeout: int = 300
    ) -> Tuple[bool, str, str, List[str]]:
        """
        Execute CLI in a workspace directory and track file changes.

        This is useful for tools that modify files directly.

        Args:
            prompt: The prompt to send
            workspace_dir: Directory to execute in
            timeout: Timeout in seconds

        Returns:
            Tuple of (success, stdout, stderr, modified_files)
        """
        workspace_path = Path(workspace_dir)
        workspace_path.mkdir(parents=True, exist_ok=True)

        # Get initial file state
        initial_files = self._get_file_state(workspace_path)

        # Execute command in workspace
        success, stdout, stderr = self._execute_stdin(prompt, timeout, workspace_dir)

        # Get modified files
        modified_files = self._get_modified_files(workspace_path, initial_files)

        return success, stdout, stderr, modified_files

    def _get_file_state(self, directory: Path) -> Dict[str, float]:
        """Get modification times of all files in directory."""
        file_state = {}

        for file_path in directory.rglob('*'):
            if file_path.is_file():
                try:
                    file_state[str(file_path)] = file_path.stat().st_mtime
                except Exception:
                    pass

        return file_state

    def _get_modified_files(
        self,
        directory: Path,
        initial_state: Dict[str, float]
    ) -> List[str]:
        """Determine which files were modified or created."""
        modified = []

        for file_path in directory.rglob('*'):
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
        self,
        prompt: str,
        max_retries: int = 3,
        backoff: float = 1.0,
        **kwargs
    ) -> Tuple[bool, str, str]:
        """
        Execute with automatic retry on failure.

        Args:
            prompt: The prompt to send
            max_retries: Maximum number of retry attempts
            backoff: Backoff multiplier between retries
            **kwargs: Additional arguments for execute_with_prompt

        Returns:
            Tuple of (success, stdout, stderr)
        """
        last_error = ""

        for attempt in range(max_retries):
            if attempt > 0:
                sleep_time = backoff * (2 ** (attempt - 1))
                self.logger.info(f"Retry attempt {attempt + 1}/{max_retries} after {sleep_time}s")
                time.sleep(sleep_time)

            success, stdout, stderr = self.execute_with_prompt(prompt, **kwargs)

            if success:
                return success, stdout, stderr

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
    """
    Registry of known CLI tool communication patterns.

    This helps adapters know how to communicate with each tool.
    """

    PATTERNS = {
        'claude': {
            'command': 'claude',
            'method': 'arg',
            'prompt_flag': '--message',
            'supports_workspace': True,
            'output_format': 'text'
        },
        'codex': {
            'command': 'codex',
            'method': 'stdin',
            'supports_workspace': True,
            'output_format': 'text'
        },
        'gemini': {
            'command': 'gemini',
            'method': 'arg',
            'prompt_flag': '--prompt',
            'supports_workspace': False,
            'output_format': 'text'
        },
        'github-copilot-cli': {
            'command': 'gh',
            'subcommand': 'copilot',
            'method': 'arg',
            'supports_workspace': False,
            'output_format': 'text'
        },
        'openai': {
            'command': 'openai',
            'method': 'arg',
            'prompt_flag': '--prompt',
            'supports_workspace': False,
            'output_format': 'json'
        }
    }

    @classmethod
    def get_pattern(cls, tool_name: str) -> Dict[str, Any]:
        """Get communication pattern for a tool."""
        return cls.PATTERNS.get(tool_name, {
            'method': 'stdin',
            'supports_workspace': True,
            'output_format': 'text'
        })

    @classmethod
    def register_pattern(cls, tool_name: str, pattern: Dict[str, Any]):
        """Register a new tool pattern."""
        cls.PATTERNS[tool_name] = pattern
