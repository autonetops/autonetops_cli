import asyncio
import yaml
import os
from scrapli import AsyncScrapli


# conn.platform values that mean "run this entry on the local host" instead of
# SSHing to a network device. Lets host tasks live in the same solution files.
LOCAL_PLATFORMS = {"local", "localhost", "host", "shell", "linux", "bash"}


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


def is_local_target(device_conn):
    """Return True if an entry should run on the local host, not a network device.

    A host entry is flagged by its connection block, e.g. ``platform: local``
    or ``host: localhost``. This keeps host tasks in the same solution file
    structure as device tasks (name -> {conn, config}).
    """
    conn = device_conn or {}
    platform = str(conn.get("platform", "")).lower()
    host = str(conn.get("host", "")).lower()
    return platform in LOCAL_PLATFORMS or host in {"local", "localhost"}


async def run_local_config(config, cli_verbose=False):
    """Run a ``config`` block as a shell script on the local host.

    The whole block is handed to ``bash`` (with ``set -e`` prepended) so that
    multi-line constructs, pipes, loops, and ``cd`` between lines behave the way
    they would in a terminal, and any failing command fails the task. Commands
    must be non-interactive (e.g. ``apt install -y``, passwordless/``sudo -n``);
    stdin is closed.

    Args:
        config (str): Shell commands, one per line, from the entry's ``config``.
        cli_verbose (bool): Stream command output to the screen as it runs.

    Returns:
        str: Combined stdout/stderr produced by the script.

    Raises:
        RuntimeError: If the script exits with a non-zero status.
    """
    script = "set -e\n" + (config or "")
    proc = await asyncio.create_subprocess_exec(
        "bash", "-c", script,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    output = stdout.decode(errors="replace")
    if cli_verbose and output:
        print(output, end="" if output.endswith("\n") else "\n")
    if proc.returncode != 0:
        raise RuntimeError(
            f"host commands exited with status {proc.returncode}\n{output}".rstrip()
        )
    return output


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
