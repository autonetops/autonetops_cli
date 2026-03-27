"""Tests for autonetops.utils.helpers module."""
import os
import pytest
import yaml
from unittest.mock import patch, AsyncMock, MagicMock

from autonetops.utils.helpers import load_yaml, convert_yaml_to_commands, connect_and_send_config


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


class TestConnectAndSendConfig:
    """Tests for the connect_and_send_config function."""

    @pytest.mark.asyncio
    async def test_connect_and_send_config(self):
        """Test connecting to a device and sending config via scrapli async."""
        mock_conn = AsyncMock()
        mock_response = MagicMock()
        mock_conn.send_configs = AsyncMock(return_value=mock_response)

        device_conn = {
            "host": "192.168.1.1",
            "auth_username": "admin",
            "auth_password": "password",
            "platform": "cisco_iosxe",
        }
        commands = ["interface Gi0/0", "ip address 10.0.0.1 255.255.255.0"]

        with patch("autonetops.utils.helpers.AsyncScrapli") as mock_scrapli_cls:
            mock_scrapli_cls.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_scrapli_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await connect_and_send_config(device_conn, commands)

        mock_conn.send_configs.assert_awaited_once_with(commands)
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_connect_uses_defaults(self):
        """Test that default platform and transport are applied."""
        mock_conn = AsyncMock()
        mock_conn.send_configs = AsyncMock(return_value=MagicMock())

        device_conn = {
            "host": "10.0.0.1",
            "auth_username": "admin",
            "auth_password": "secret",
        }

        with patch("autonetops.utils.helpers.AsyncScrapli") as mock_scrapli_cls:
            mock_scrapli_cls.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_scrapli_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            await connect_and_send_config(device_conn, ["hostname R1"])

        call_kwargs = mock_scrapli_cls.call_args[1]
        assert call_kwargs["platform"] == "cisco_iosxe"
        assert call_kwargs["transport"] == "asyncssh"
        assert call_kwargs["auth_strict_key"] is False
