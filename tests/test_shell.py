"""
Tests for the interactive shell.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import json

from orchestrator.shell import InteractiveShell, ConversationHistory


class TestConversationHistory:
    """Test ConversationHistory functionality."""

    def test_initialization(self):
        """Test history initialization."""
        history = ConversationHistory()

        assert history.messages == []
        assert history.current_agent is None
        assert history.workflow == "default"
        assert history.context == {}

    def test_add_message(self):
        """Test adding messages."""
        history = ConversationHistory()

        history.add_message('user', 'Hello')
        history.add_message('assistant', 'Hi there', {'agent': 'claude'})

        assert len(history.messages) == 2
        assert history.messages[0]['role'] == 'user'
        assert history.messages[0]['content'] == 'Hello'
        assert history.messages[1]['metadata']['agent'] == 'claude'

    def test_get_context(self):
        """Test getting context."""
        history = ConversationHistory()
        history.add_message('user', 'Test message')
        history.current_agent = 'claude'
        history.workflow = 'thorough'

        context = history.get_context()

        assert context['current_agent'] == 'claude'
        assert context['workflow'] == 'thorough'
        assert len(context['history']) == 1

    def test_clear(self):
        """Test clearing history."""
        history = ConversationHistory()
        history.add_message('user', 'Test')
        history.context['test'] = 'value'

        history.clear()

        assert len(history.messages) == 0
        assert len(history.context) == 0

    def test_save_and_load(self, tmp_path):
        """Test saving and loading history."""
        history = ConversationHistory()
        history.add_message('user', 'Hello')
        history.add_message('assistant', 'Hi')
        history.current_agent = 'claude'
        history.workflow = 'thorough'
        history.context = {'files': ['test.py']}

        # Save
        filepath = tmp_path / 'test_session.json'
        history.save(str(filepath))

        assert filepath.exists()

        # Load
        new_history = ConversationHistory()
        new_history.load(str(filepath))

        assert len(new_history.messages) == 2
        assert new_history.current_agent == 'claude'
        assert new_history.workflow == 'thorough'
        assert new_history.context['files'] == ['test.py']


class TestInteractiveShell:
    """Test InteractiveShell functionality."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create a mock orchestrator."""
        orchestrator = Mock()
        orchestrator.get_available_agents.return_value = ['claude', 'codex']
        orchestrator.get_workflows.return_value = ['default', 'quick']
        orchestrator.config = {
            'agents': {
                'claude': {'enabled': True, 'role': 'refinement'},
                'codex': {'enabled': True, 'role': 'implementation'}
            }
        }
        return orchestrator

    @patch('orchestrator.shell.Orchestrator')
    def test_initialization(self, mock_orchestrator_class):
        """Test shell initialization."""
        mock_orchestrator_class.return_value = Mock()

        shell = InteractiveShell()

        assert shell.history is not None
        assert shell.running is True
        assert isinstance(shell.commands, dict)

    @patch('orchestrator.shell.Orchestrator')
    def test_commands_registered(self, mock_orchestrator_class):
        """Test that all commands are registered."""
        mock_orchestrator_class.return_value = Mock()

        shell = InteractiveShell()

        # Check that expected commands are registered
        expected_commands = [
            '/help', '/exit', '/quit', '/clear', '/history',
            '/agents', '/workflows', '/switch', '/workflow',
            '/save', '/load', '/context', '/reset', '/info'
        ]

        for cmd in expected_commands:
            assert cmd in shell.commands

    @patch('orchestrator.shell.Orchestrator')
    def test_cmd_switch_agent(self, mock_orchestrator_class, capsys):
        """Test switching agents."""
        mock_orch = Mock()
        mock_orch.get_available_agents.return_value = ['claude', 'codex']
        mock_orchestrator_class.return_value = mock_orch

        shell = InteractiveShell()

        # Switch to valid agent
        shell.cmd_switch_agent('claude')
        assert shell.history.current_agent == 'claude'

        # Try to switch to invalid agent
        shell.cmd_switch_agent('invalid')
        assert shell.history.current_agent == 'claude'  # Should remain unchanged

    @patch('orchestrator.shell.Orchestrator')
    def test_cmd_set_workflow(self, mock_orchestrator_class):
        """Test setting workflow."""
        mock_orch = Mock()
        mock_orch.get_workflows.return_value = ['default', 'quick', 'thorough']
        mock_orchestrator_class.return_value = mock_orch

        shell = InteractiveShell()

        # Set to valid workflow
        shell.cmd_set_workflow('thorough')
        assert shell.history.workflow == 'thorough'

        # Try to set to invalid workflow
        shell.cmd_set_workflow('invalid')
        assert shell.history.workflow == 'thorough'  # Should remain unchanged

    @patch('orchestrator.shell.Orchestrator')
    def test_cmd_save_load_session(self, mock_orchestrator_class, tmp_path):
        """Test saving and loading sessions."""
        mock_orchestrator_class.return_value = Mock()

        shell = InteractiveShell()
        shell.session_dir = tmp_path

        # Add some history
        shell.history.add_message('user', 'Test message')
        shell.history.current_agent = 'claude'

        # Save session
        shell.cmd_save_session('test_session.json')

        session_file = tmp_path / 'test_session.json'
        assert session_file.exists()

        # Clear history
        shell.history.clear()
        shell.history.current_agent = None

        # Load session
        shell.cmd_load_session('test_session.json')

        assert len(shell.history.messages) == 1
        assert shell.history.current_agent == 'claude'

    @patch('orchestrator.shell.Orchestrator')
    @patch('orchestrator.shell.Confirm.ask', return_value=True)
    def test_cmd_reset(self, mock_confirm, mock_orchestrator_class):
        """Test resetting conversation."""
        mock_orchestrator_class.return_value = Mock()

        shell = InteractiveShell()

        # Add some history
        shell.history.add_message('user', 'Test')
        shell.history.current_agent = 'claude'
        shell.history.workflow = 'thorough'

        # Reset
        shell.cmd_reset('')

        assert len(shell.history.messages) == 0
        assert shell.history.current_agent is None
        assert shell.history.workflow == 'default'

    @patch('orchestrator.shell.Orchestrator')
    def test_handle_command(self, mock_orchestrator_class):
        """Test command handling."""
        mock_orchestrator_class.return_value = Mock()

        shell = InteractiveShell()

        # Create a mock command function
        mock_cmd = Mock()
        shell.commands['/test'] = mock_cmd

        # Handle valid command
        shell._handle_command('/test')
        mock_cmd.assert_called_once_with('')

        # Handle command with arguments
        shell._handle_command('/test arg1 arg2')
        assert mock_cmd.call_count == 2

    @patch('orchestrator.shell.Orchestrator')
    def test_get_prompt(self, mock_orchestrator_class):
        """Test prompt generation."""
        mock_orchestrator_class.return_value = Mock()

        shell = InteractiveShell()

        # Default prompt
        prompt = shell._get_prompt()
        assert 'orchestrator' in prompt.lower()

        # With agent
        shell.history.current_agent = 'claude'
        prompt = shell._get_prompt()
        assert 'claude' in prompt.lower()


class TestShellIntegration:
    """Integration tests for the shell."""

    @patch('orchestrator.shell.Orchestrator')
    @patch('orchestrator.shell.Prompt.ask')
    def test_shell_startup_and_exit(self, mock_prompt, mock_orchestrator_class):
        """Test shell can start and exit cleanly."""
        mock_orch = Mock()
        mock_orch.get_available_agents.return_value = ['claude']
        mock_orch.get_workflows.return_value = ['default']
        mock_orchestrator_class.return_value = mock_orch

        # Simulate user typing /exit
        mock_prompt.side_effect = ['/exit']

        shell = InteractiveShell()

        # This should exit cleanly
        shell.start()

        assert shell.running is False

    @patch('orchestrator.shell.Orchestrator')
    @patch('orchestrator.shell.Prompt.ask')
    def test_shell_handles_empty_input(self, mock_prompt, mock_orchestrator_class):
        """Test shell handles empty input gracefully."""
        mock_orch = Mock()
        mock_orch.get_available_agents.return_value = []
        mock_orchestrator_class.return_value = mock_orch

        # Simulate empty input then exit
        mock_prompt.side_effect = ['', '  ', '/exit']

        shell = InteractiveShell()
        shell.start()

        # Should handle empty input without errors
        assert shell.running is False

    @patch('orchestrator.shell.Orchestrator')
    @patch('orchestrator.shell.Prompt.ask')
    @patch('orchestrator.shell.Confirm.ask', return_value=False)
    def test_shell_exit_without_save(self, mock_confirm, mock_prompt, mock_orchestrator_class):
        """Test exiting shell without saving."""
        mock_orch = Mock()
        mock_orch.get_available_agents.return_value = ['claude']
        mock_orchestrator_class.return_value = mock_orch

        mock_prompt.side_effect = ['/exit']

        shell = InteractiveShell()
        shell.history.add_message('user', 'Test')  # Add message so save prompt appears

        shell.start()

        # Confirm should be called for save prompt
        mock_confirm.assert_called()
