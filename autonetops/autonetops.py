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
    """Parse a task range string like '3', '2-5', or 'all' into a list of ints."""
    if value == "all":
        if solutions_dir is None:
            raise click.BadParameter("Cannot use 'all' without a solutions directory.")
        numbers = discover_task_numbers(solutions_dir)
        if not numbers:
            raise click.BadParameter(f"No task files found in {solutions_dir}.")
        return numbers
    if "-" in value:
        parts = value.split("-", 1)
        try:
            start, end = int(parts[0]), int(parts[1])
        except ValueError:
            raise click.BadParameter(f"Invalid range '{value}'. Use a number, range (2-5), or 'all'.")
        if start > end:
            raise click.BadParameter(f"Start ({start}) must be <= end ({end}).")
        return list(range(start, end + 1))
    try:
        return [int(value)]
    except ValueError:
        raise click.BadParameter(f"Invalid task '{value}'. Use a number, range (2-5), or 'all'.")


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
        devices = load_yaml(yaml_path)

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
