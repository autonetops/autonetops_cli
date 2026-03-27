"""Tests for autonetops.utils.utils module."""
import click
from unittest.mock import patch, call

from autonetops.utils.utils import debug_msg, debug_result, check_result


class TestDebugMsg:
    """Tests for the debug_msg function."""

    @patch('autonetops.utils.utils.click.secho')
    def test_debug_true_prints_message(self, mock_secho):
        """Test that debug message is printed when debug is True."""
        debug_msg(True, "test message")
        mock_secho.assert_called_once_with("DEBUG: test message", fg="yellow")

    @patch('autonetops.utils.utils.click.secho')
    def test_debug_false_no_print(self, mock_secho):
        """Test that no message is printed when debug is False."""
        debug_msg(False, "test message")
        mock_secho.assert_not_called()


class TestDebugResult:
    """Tests for the debug_result function."""

    @patch('autonetops.utils.utils.debug_msg')
    def test_debug_result_prints_both(self, mock_debug_msg):
        """Test that debug_result prints both success and message."""
        debug_result(True, (True, "success reason"))
        assert mock_debug_msg.call_count == 2
        mock_debug_msg.assert_any_call(True, "Action Successful: True")
        mock_debug_msg.assert_any_call(True, "Message: 'success reason'")

    @patch('autonetops.utils.utils.debug_msg')
    def test_debug_result_false(self, mock_debug_msg):
        """Test that debug_result does nothing when debug is False."""
        debug_result(False, (True, "reason"))
        mock_debug_msg.assert_not_called()


class TestCheckResult:
    """Tests for the check_result function."""

    @patch('autonetops.utils.utils.click.secho')
    def test_check_result_failure(self, mock_secho):
        """Test that failure results print an error message."""
        check_result("Router1", "configure", (False, "connection timeout"))
        mock_secho.assert_called_once_with(
            "ERROR: Action configure on Device Router1 failed with reason 'connection timeout'",
            fg="red",
            err=True,
        )

    @patch('autonetops.utils.utils.click.secho')
    def test_check_result_success(self, mock_secho):
        """Test that success results do not print an error."""
        check_result("Router1", "configure", (True, None))
        mock_secho.assert_not_called()

    @patch('autonetops.utils.utils.debug_result')
    def test_check_result_with_debug(self, mock_debug_result):
        """Test that check_result calls debug_result when debug is True."""
        check_result("Router1", "configure", (True, None), debug=True)
        mock_debug_result.assert_called_once_with(True, (True, None))
