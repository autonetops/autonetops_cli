import yaml
import os
from scrapli import AsyncScrapli


def load_yaml(file_path):
    """Load and parse a YAML file, returning its contents."""
    try:
        with open(file_path, 'r', encoding='utf-8') as yf:
            return yaml.safe_load(yf)
    except FileNotFoundError:
        raise
    except yaml.YAMLError:
        raise


def convert_yaml_to_commands(config):
    """Split a YAML configuration string into a list of commands."""
    return [line.lstrip() for line in config.splitlines()]


async def connect_and_send_config(device_conn, commands):
    """
    Connect to a device using scrapli async and send configuration commands.

    Args:
        device_conn (dict): Connection parameters with keys:
            host, auth_username, auth_password, platform, transport (optional)
        commands (list): List of configuration commands to send.

    Returns:
        response: Scrapli MultiResponse from send_configs.
    """
    conn_params = {
        "host": device_conn["host"],
        "auth_username": device_conn["auth_username"],
        "auth_password": device_conn["auth_password"],
        "platform": device_conn.get("platform", "cisco_iosxe"),
        "transport": device_conn.get("transport", "asyncssh"),
        "auth_strict_key": device_conn.get("auth_strict_key", False),
    }

    async with AsyncScrapli(**conn_params) as conn:
        response = await conn.send_configs(commands)
        return response
