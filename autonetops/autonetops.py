import asyncio
import os
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


@cli.command(name="task", help="Render configuration from task <TASK_NUMBER>")
@click.argument("task_number", type=int)
@click.option(
    "--show",
    is_flag=True,
    help="Show the rendered configuration instead of pushing it to the device",
)
@click.pass_context
def task(ctx, task_number, show):
    """
    Render configuration from task<TASK_NUMBER>.yaml,
    display it, and push the configuration to devices.
    """
    wsf = os.getenv("CONTAINERWSF", os.getcwd())
    yaml_file = f"task{task_number}.yaml"
    devices = load_yaml(f"{wsf}/solutions/{yaml_file}")

    for device, data in devices.items():
        if show:
            rprint(f"[blue]{device}:[/blue]")
            rprint(f"[green]{data['config']}[/green]")

    if not show:
        asyncio.run(_push_all_configs(devices, ctx.obj["debug"]))


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
