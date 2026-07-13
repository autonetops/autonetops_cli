import asyncio
import os
import re
import subprocess

import click
from rich import print as rprint

from .utils.helpers import (
    load_yaml,
    convert_yaml_to_commands,
    connect_and_send_config,
)


@click.group(help="Utilities for autonetops automation.")
@click.option("--debug", is_flag=True, help="Print debug messages during processing")
@click.option("--cli-verbose", is_flag=True, help="Stream CLI connection info to screen")
@click.option(
    "-i",
    "--inventory",
    default="task1.yaml",
    help="The network inventory file to operate on",
)
@click.pass_context
def cli(ctx, inventory, debug, cli_verbose):
    """Autonetops CLI tool for network automation."""
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    ctx.obj["cli_verbose"] = cli_verbose
    ctx.obj["inventory"] = inventory
    ctx.obj["task_number"] = set()


async def _push_device_config(device_name, data, debug):
    """Push configuration to a single device asynchronously."""
    commands = convert_yaml_to_commands(data["config"])
    try:
        await connect_and_send_config(data["conn"], commands)
        rprint(f"[green]Configuration pushed to {device_name} successfully.[/green]")
    except Exception as e:
        rprint(f"Failed to push configuration to {device_name}: {e}")
        if debug:
            rprint(f"[red]Error:[/red] {e}")


async def _push_all_configs(devices, debug):
    """Push configuration to all devices in parallel."""
    tasks = [
        _push_device_config(name, data, debug)
        for name, data in devices.items()
    ]
    await asyncio.gather(*tasks)


@cli.command(name="wireshark", help="Instala as imagens para capturar pacotes")
@click.pass_context
def wireshark(ctx):
    subprocess.run(["docker", "pull", "ghcr.io/siemens/ghostwire:latest"], check=True)
    subprocess.run(["docker", "pull", "ghcr.io/siemens/packetflix:latest"], check=True)
    rprint("[green]Imagens Instaladas. Comece as capturas...[/green]")


VPN_PID_FILE = "/run/openconnect.pid"


def _find_openconnect_pid():
    """Return the running openconnect PID from the pid file or pgrep, or None."""
    try:
        with open(VPN_PID_FILE) as f:
            pid = f.read().strip()
    except OSError:
        pid = ""

    if pid:
        try:
            with open(f"/proc/{pid}/comm") as f:
                if f.read().strip() == "openconnect":
                    return pid
        except OSError:
            pass

    result = subprocess.run(
        ["pgrep", "-x", "openconnect"], capture_output=True, text=True, check=False
    )
    pids = result.stdout.split()
    return pids[0] if pids else None


@cli.group(name="vpn", help="Install and manage the Cisco Sandbox OpenConnect VPN.")
@click.pass_context
def vpn(ctx):
    """Manage the Cisco Sandbox VPN (OpenConnect client)."""


@vpn.command(name="setup", help="Install dependencies and the OpenConnect VPN client.")
@click.pass_context
def vpn_setup(ctx):
    """Update the system and install everything needed for the VPN."""
    steps = [
        ["sudo", "apt", "update"],
        ["sudo", "apt", "upgrade", "-y"],
        [
            "sudo", "apt", "install", "-y",
            "wget", "curl", "nano", "software-properties-common", "dirmngr",
            "apt-transport-https", "gnupg2", "ca-certificates", "lsb-release", "unzip",
        ],
        ["sudo", "apt", "install", "ufw", "-y"],
        ["sudo", "ufw", "allow", "22/tcp"],
        ["sudo", "apt", "install", "git", "-y"],
        ["sudo", "apt", "install", "openconnect", "-y"],
    ]
    for step in steps:
        subprocess.run(step, check=True)
    subprocess.run(["sudo", "ufw", "enable"], input="y\n", text=True, check=True)

    rprint("[green]==> Setup complete.[/green]")
    rprint("==> Connect to VPN:")
    rprint("  autonetops vpn connect --domain <host> --port <port> --user <user>")
    rprint("==> Check status:")
    rprint("  autonetops vpn status")
    rprint("==> Disconnect:")
    rprint("  autonetops vpn disconnect")


@vpn.command(name="connect", help="Connect to the Cisco Sandbox VPN.")
@click.option("--domain", required=True, help="VPN server hostname or IP")
@click.option("--port", required=True, help="VPN server TCP port")
@click.option("--user", "vpn_user", required=True, help="VPN username")
@click.pass_context
def vpn_connect(ctx, domain, port, vpn_user):
    """Start openconnect in the background against the sandbox VPN."""
    subprocess.run(
        [
            "sudo", "openconnect", "-b",
            f"--pid-file={VPN_PID_FILE}",
            f"{domain}:{port}",
            "-u", vpn_user,
        ],
        check=True,
    )


@vpn.command(name="status", help="Show whether the VPN tunnel is up.")
@click.pass_context
def vpn_status(ctx):
    """Exit 0 when the tunnel is up, 1 when it is down."""
    pid = _find_openconnect_pid()
    if not pid:
        rprint("[red]==> VPN is DOWN (no openconnect process)[/red]")
        ctx.exit(1)

    rprint(f"[green]==> VPN is UP (openconnect pid {pid})[/green]")
    result = subprocess.run(
        ["ip", "-br", "addr", "show", "type", "tun"],
        capture_output=True, text=True, check=False,
    )
    for line in result.stdout.splitlines():
        rprint(f"    {line}")

    link = subprocess.run(
        ["ip", "-br", "link", "show", "type", "tun"],
        capture_output=True, text=True, check=False,
    )
    tun_dev = link.stdout.split()[0] if link.stdout.split() else None
    if tun_dev:
        routes = subprocess.run(
            ["ip", "route", "show", "dev", tun_dev],
            capture_output=True, text=True, check=False,
        )
        for line in routes.stdout.splitlines():
            rprint(f"    route: {line}")


@vpn.command(name="disconnect", help="Log off and disconnect the VPN.")
@click.pass_context
def vpn_disconnect(ctx):
    """Send SIGINT to openconnect for a clean logoff, escalating to SIGKILL."""
    import time

    pid = _find_openconnect_pid()
    if not pid:
        rprint("==> No openconnect process found")
        subprocess.run(["sudo", "rm", "-f", VPN_PID_FILE], check=False)
        return

    rprint(f"==> Logging off session and disconnecting (pid {pid})...")
    subprocess.run(["sudo", "kill", "-INT", pid], check=False)
    for _ in range(10):
        if not os.path.isdir(f"/proc/{pid}"):
            break
        time.sleep(1)
    if os.path.isdir(f"/proc/{pid}"):
        rprint(
            "[yellow]==> Clean shutdown timed out after 10s, forcing SIGKILL "
            "(routes may need manual cleanup)[/yellow]"
        )
        subprocess.run(["sudo", "kill", "-9", pid], check=False)
        time.sleep(1)
    subprocess.run(["sudo", "rm", "-f", VPN_PID_FILE], check=False)
    rprint("[green]==> VPN disconnected[/green]")

def discover_task_numbers(solutions_dir):
    """Find all task<N>.yaml files in the solutions directory and return sorted task numbers."""
    import glob
    pattern = os.path.join(solutions_dir, "task*.yaml")
    numbers = []
    for path in glob.glob(pattern):
        basename = os.path.basename(path)
        # Extract number from "task<N>.yaml"
        num_str = basename.removeprefix("task").removesuffix(".yaml")
        try:
            numbers.append(int(num_str))
        except ValueError:
            continue
    return sorted(numbers)


def parse_task_range(value, solutions_dir=None):
    """Parse a task range string like '3', '2-5', or 'all' into a list of ints.

    For ranges like '1-9', discovers all task files whose leading digit falls
    within the range (e.g. task61.yaml is included when range covers 6).
    """
    if solutions_dir is None:
        raise click.BadParameter("Cannot resolve tasks without a solutions directory.")
    all_numbers = discover_task_numbers(solutions_dir)
    if value == "all":
        if not all_numbers:
            raise click.BadParameter(f"No task files found in {solutions_dir}.")
        return all_numbers
    if "-" in value:
        parts = value.split("-", 1)
        try:
            start, end = int(parts[0]), int(parts[1])
        except ValueError:
            raise click.BadParameter(f"Invalid range '{value}'. Use a number, range (2-5), or 'all'.")
        if start > end:
            raise click.BadParameter(f"Start ({start}) must be <= end ({end}).")
        matched = [n for n in all_numbers if start <= int(str(n)[0]) <= end]
        if not matched:
            return list(range(start, end + 1))
        return matched
    try:
        single = int(value)
    except ValueError:
        raise click.BadParameter(f"Invalid task '{value}'. Use a number, range (2-5), or 'all'.")
    matched = [n for n in all_numbers if str(n).startswith(value)]
    return matched if matched else [single]


@cli.command(name="task", help="Render and push configuration from task(s). Accepts a number (3), range (2-5), or 'all'.")
@click.argument("task_range", type=str)
@click.option(
    "--show",
    is_flag=True,
    help="Show the rendered configuration instead of pushing it to the device",
)
@click.pass_context
def task(ctx, task_range, show):
    """
    Render configuration from task YAML files and push to devices.

    TASK_RANGE can be a single number (3), a range (2-5), or 'all' to
    run every task file found in the solutions directory in order.
    """
    wsf = os.getenv("CONTAINERWSF", os.getcwd())
    solutions_dir = f"{wsf}/solutions"
    task_numbers = parse_task_range(task_range, solutions_dir)

    for task_number in task_numbers:
        yaml_file = f"task{task_number}.yaml"
        yaml_path = f"{wsf}/solutions/{yaml_file}"
        rprint(f"[bold blue]--- Task {task_number} ---[/bold blue]")
        if not os.path.exists(yaml_path):
            rprint(f"[yellow]Skipping task {task_number}: {yaml_file} not found.[/yellow]")
            continue
        devices = load_yaml(yaml_path)

        for device, data in devices.items():
            if show:
                rprint(f"[blue]{device}:[/blue]")
                rprint(f"[green]{data['config']}[/green]")

        if not show:
            asyncio.run(_push_all_configs(devices, ctx.obj["debug"]))


@cli.command(name="tshoot", help="Deploy a troubleshooting scenario and display the challenge.")
@click.argument("scenario_number", type=int)
@click.option(
    "--show",
    is_flag=True,
    help="Show the scenario description without pushing the broken config",
)
@click.pass_context
def tshoot(ctx, scenario_number, show):
    """
    Load a troubleshooting scenario from tshoot<N>.yaml, push the
    broken configuration to devices, and display the scenario challenge.
    """
    wsf = os.getenv("CONTAINERWSF", os.getcwd())
    yaml_path = f"{wsf}/solutions/tshoot{scenario_number}.yaml"

    if not os.path.exists(yaml_path):
        rprint(f"[red]This lab has no troubleshooting scenario {scenario_number}.[/red]")
        return

    data = load_yaml(yaml_path)
    scenario = data.get("scenario", "No scenario description provided.")
    devices = data.get("devices", {})

    rprint(f"[bold blue]--- Troubleshooting Scenario {scenario_number} ---[/bold blue]")
    rprint(f"[yellow]{scenario}[/yellow]")

    if not devices:
        rprint("[red]No device configurations found in this scenario.[/red]")
        return

    if show:
        for device, device_data in devices.items():
            rprint(f"[blue]{device}:[/blue]")
            rprint(f"[green]{device_data['config']}[/green]")
    else:
        asyncio.run(_push_all_configs(devices, ctx.obj["debug"]))
        rprint("[bold green]Troubleshooting scenario deployed. Good luck![/bold green]")


@cli.command(name="restart", help="Restart the lab with the specified lab name.")
@click.option("--lab")
@click.pass_context
def restart(ctx, lab):
    """Restart the lab with the specified lab name."""
    wsf = f"/{lab}" if lab else os.getenv("CONTAINERWSF", os.getcwd())
    lab_file = f"{wsf}/clab/lab.clab.yaml"

    if not os.path.exists(lab_file):
        rprint(f"[red]Lab file {lab_file} does not exist.[/red]")
        return

    rprint("[blue]Restarting lab[/blue]")
    subprocess.run(["containerlab", "redeploy", "-c", "-t", lab_file], check=False)
    for i in range(6):
        subprocess.run(
            ["ssh-keygen", "-f", "/home/vscode/.ssh/known_hosts", "-R", f"172.20.20.1{i}"],
            check=False,
        )


if __name__ == "__main__":
    cli()
