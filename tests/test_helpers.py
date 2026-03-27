"""Tests for autonetops.utils.helpers module."""
import os
import pytest
import yaml
from unittest.mock import patch, mock_open, MagicMock

from autonetops.utils.helpers import load_yaml, convert_yaml_to_commands, connect_to_device_netmiko


class TestLoadYaml:
    """Tests for the load_yaml function."""

    def test_load_yaml_valid_file(self, tmp_path):
        """Test loading a valid YAML file."""
        yaml_content = {"router1": {"config": "interface Gi0/0\n ip address 10.0.0.1 255.255.255.0"}}
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        result = load_yaml(str(yaml_file))
        assert result == yaml_content

    def test_load_yaml_file_not_found(self):
        """Test loading a non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_yaml("/nonexistent/path/file.yaml")

    def test_load_yaml_invalid_yaml(self, tmp_path):
        """Test loading an invalid YAML file raises YAMLError."""
        yaml_file = tmp_path / "bad.yaml"
        yaml_file.write_text("{{invalid: yaml: content::")
        with pytest.raises(yaml.YAMLError):
            load_yaml(str(yaml_file))

    def test_load_yaml_empty_file(self, tmp_path):
        """Test loading an empty YAML file returns None."""
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")
        result = load_yaml(str(yaml_file))
        assert result is None


class TestConvertYamlToCommands:
    """Tests for the convert_yaml_to_commands function."""

    def test_basic_config(self):
        """Test converting a basic configuration string."""
        config = "interface Gi0/0\n ip address 10.0.0.1 255.255.255.0\n no shutdown"
        result = convert_yaml_to_commands(config)
        assert result == ["interface Gi0/0", "ip address 10.0.0.1 255.255.255.0", "no shutdown"]

    def test_empty_config(self):
        """Test converting an empty configuration string."""
        result = convert_yaml_to_commands("")
        assert result == []

    def test_single_command(self):
        """Test converting a single command."""
        result = convert_yaml_to_commands("hostname Router1")
        assert result == ["hostname Router1"]

    def test_strips_leading_whitespace(self):
        """Test that leading whitespace is stripped from commands."""
        config = "  interface Gi0/0\n    ip address 10.0.0.1 255.255.255.0"
        result = convert_yaml_to_commands(config)
        assert result == ["interface Gi0/0", "ip address 10.0.0.1 255.255.255.0"]


class TestConnectToDeviceNetmiko:
    """Tests for the connect_to_device_netmiko function."""

    @patch('autonetops.utils.helpers.ConnectHandler')
    def test_connect_to_device(self, mock_connect):
        """Test connecting to a device via Netmiko."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        device = {
            "device_type": "cisco_ios",
            "host": "192.168.1.1",
            "username": "admin",
            "password": "password",
        }
        result = connect_to_device_netmiko(device)

        mock_connect.assert_called_once_with(**device)
        assert result == mock_conn
