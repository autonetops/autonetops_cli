"""Tests for autonetops.autonetops CLI module."""
import os
import yaml
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from click.testing import CliRunner

from autonetops.autonetops import cli


class TestCliGroup:
    """Tests for the main CLI group."""

    def test_cli_help(self):
        """Test that CLI help runs without error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Utilities for autonetops automation" in result.output

    def test_cli_debug_flag(self):
        """Test that debug flag is accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--debug", "--help"])
        assert result.exit_code == 0


class TestTaskCommand:
    """Tests for the task command."""

    def test_task_show(self, tmp_path):
        """Test task command with --show flag."""
        devices = {
            "router1": {
                "config": "interface Gi0/0\n ip address 10.0.0.1 255.255.255.0",
                "conn": {"host": "192.168.1.1", "auth_username": "admin", "auth_password": "pass"},
            }
        }
        yaml_file = tmp_path / "solutions" / "task1.yaml"
        yaml_file.parent.mkdir(parents=True)
        yaml_file.write_text(yaml.dump(devices))

        runner = CliRunner()
        with patch.dict(os.environ, {"CONTAINERWSF": str(tmp_path)}):
            result = runner.invoke(cli, ["task", "1", "--show"])
        assert result.exit_code == 0
        assert "router1" in result.output

    def test_task_push_config(self, tmp_path):
        """Test task command pushing config to devices in parallel."""
        devices = {
            "router1": {
                "config": "hostname TestRouter",
                "conn": {"host": "192.168.1.1", "auth_username": "admin", "auth_password": "pass"},
            }
        }
        yaml_file = tmp_path / "solutions" / "task1.yaml"
        yaml_file.parent.mkdir(parents=True)
        yaml_file.write_text(yaml.dump(devices))

        runner = CliRunner()
        with patch.dict(os.environ, {"CONTAINERWSF": str(tmp_path)}):
            with patch("autonetops.autonetops.connect_and_send_config", new_callable=AsyncMock):
                result = runner.invoke(cli, ["task", "1"])
        assert result.exit_code == 0
        assert "successfully" in result.output

    def test_task_push_config_failure(self, tmp_path):
        """Test task command handling connection failure."""
        devices = {
            "router1": {
                "config": "hostname TestRouter",
                "conn": {"host": "192.168.1.1", "auth_username": "admin", "auth_password": "pass"},
            }
        }
        yaml_file = tmp_path / "solutions" / "task1.yaml"
        yaml_file.parent.mkdir(parents=True)
        yaml_file.write_text(yaml.dump(devices))

        runner = CliRunner()
        with patch.dict(os.environ, {"CONTAINERWSF": str(tmp_path)}):
            with patch(
                "autonetops.autonetops.connect_and_send_config",
                new_callable=AsyncMock,
                side_effect=Exception("Connection failed"),
            ):
                result = runner.invoke(cli, ["task", "1"])
        assert result.exit_code == 0
        assert "Failed to push configuration" in result.output


class TestRestartCommand:
    """Tests for the restart command."""

    def test_restart_lab_file_not_found(self, tmp_path):
        """Test restart when lab file does not exist."""
        runner = CliRunner()
        with patch.dict(os.environ, {"CONTAINERWSF": str(tmp_path)}):
            result = runner.invoke(cli, ["restart"])
        assert result.exit_code == 0
        assert "does not exist" in result.output

    @patch("autonetops.autonetops.subprocess.run")
    def test_restart_with_lab_file(self, mock_run, tmp_path):
        """Test restart when lab file exists."""
        lab_dir = tmp_path / "clab"
        lab_dir.mkdir()
        (lab_dir / "lab.clab.yaml").write_text("topology: {}")

        runner = CliRunner()
        with patch.dict(os.environ, {"CONTAINERWSF": str(tmp_path)}):
            result = runner.invoke(cli, ["restart"])
        assert result.exit_code == 0
        assert mock_run.called


class TestWiresharkCommand:
    """Tests for the wireshark command."""

    @patch("autonetops.autonetops.subprocess.run")
    def test_wireshark(self, mock_run):
        """Test wireshark command pulls docker images."""
        runner = CliRunner()
        result = runner.invoke(cli, ["wireshark"])
        assert result.exit_code == 0
        assert mock_run.call_count == 2
