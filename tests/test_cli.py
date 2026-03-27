"""Tests for autonetops.autonetops CLI module."""
import os
import yaml
import click
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from click.testing import CliRunner

from autonetops.autonetops import cli, parse_task_range


class TestParseTaskRange:
    """Tests for parse_task_range helper."""

    def test_single_number(self):
        assert parse_task_range("3") == [3]

    def test_range(self):
        assert parse_task_range("2-5") == [2, 3, 4, 5]

    def test_range_single_span(self):
        assert parse_task_range("4-4") == [4]

    def test_invalid_string(self):
        with pytest.raises(click.BadParameter):
            parse_task_range("abc")

    def test_invalid_range(self):
        with pytest.raises(click.BadParameter):
            parse_task_range("a-b")

    def test_reversed_range(self):
        with pytest.raises(click.BadParameter):
            parse_task_range("5-2")

    def test_all_discovers_tasks(self, tmp_path):
        """Test 'all' discovers and sorts task files."""
        solutions = tmp_path / "solutions"
        solutions.mkdir()
        (solutions / "task3.yaml").write_text("")
        (solutions / "task1.yaml").write_text("")
        (solutions / "task10.yaml").write_text("")
        assert parse_task_range("all", str(solutions)) == [1, 3, 10]

    def test_all_no_tasks_found(self, tmp_path):
        """Test 'all' raises when no task files exist."""
        solutions = tmp_path / "solutions"
        solutions.mkdir()
        with pytest.raises(click.BadParameter, match="No task files found"):
            parse_task_range("all", str(solutions))

    def test_all_without_solutions_dir(self):
        """Test 'all' raises when no solutions dir is provided."""
        with pytest.raises(click.BadParameter):
            parse_task_range("all")


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

    def test_task_range_show(self, tmp_path):
        """Test task command with a range and --show flag."""
        solutions = tmp_path / "solutions"
        solutions.mkdir(parents=True)
        for i in range(2, 5):
            devices = {
                f"router{i}": {
                    "config": f"hostname Router{i}",
                    "conn": {"host": f"10.0.0.{i}", "auth_username": "admin", "auth_password": "pass"},
                }
            }
            (solutions / f"task{i}.yaml").write_text(yaml.dump(devices))

        runner = CliRunner()
        with patch.dict(os.environ, {"CONTAINERWSF": str(tmp_path)}):
            result = runner.invoke(cli, ["task", "2-4", "--show"])
        assert result.exit_code == 0
        assert "router2" in result.output
        assert "router3" in result.output
        assert "router4" in result.output
        assert "Task 2" in result.output
        assert "Task 4" in result.output

    def test_task_range_push(self, tmp_path):
        """Test task command with a range pushes configs for all tasks."""
        solutions = tmp_path / "solutions"
        solutions.mkdir(parents=True)
        for i in range(1, 4):
            devices = {
                f"sw{i}": {
                    "config": f"hostname Switch{i}",
                    "conn": {"host": f"10.0.0.{i}", "auth_username": "admin", "auth_password": "pass"},
                }
            }
            (solutions / f"task{i}.yaml").write_text(yaml.dump(devices))

        runner = CliRunner()
        with patch.dict(os.environ, {"CONTAINERWSF": str(tmp_path)}):
            with patch("autonetops.autonetops.connect_and_send_config", new_callable=AsyncMock):
                result = runner.invoke(cli, ["task", "1-3"])
        assert result.exit_code == 0
        assert "sw1" in result.output
        assert "sw2" in result.output
        assert "sw3" in result.output

    def test_task_all_show(self, tmp_path):
        """Test 'autonetops task all --show' discovers and shows all tasks."""
        solutions = tmp_path / "solutions"
        solutions.mkdir(parents=True)
        for i in [1, 3, 5]:
            devices = {
                f"dev{i}": {
                    "config": f"hostname Dev{i}",
                    "conn": {"host": f"10.0.0.{i}", "auth_username": "admin", "auth_password": "pass"},
                }
            }
            (solutions / f"task{i}.yaml").write_text(yaml.dump(devices))

        runner = CliRunner()
        with patch.dict(os.environ, {"CONTAINERWSF": str(tmp_path)}):
            result = runner.invoke(cli, ["task", "all", "--show"])
        assert result.exit_code == 0
        assert "dev1" in result.output
        assert "dev3" in result.output
        assert "dev5" in result.output
        assert "Task 1" in result.output
        assert "Task 5" in result.output

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
