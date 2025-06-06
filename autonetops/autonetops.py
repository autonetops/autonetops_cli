import click
import os
from jinja2 import Template, Environment
from .utils.helpers import (
    load_yaml,
    convert_yaml_to_commands,
    connect_to_device_netmiko
)
from rich import print as rprint

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

@cli.command(name="task", help="Render configuration from task<TASK_NUMBER>.yaml and task<TASK_NUMBER>.j2, display it, and push the configuration to a device.")
@click.argument('task_number')
@click.option(
    "--show",
    is_flag=True,
    help="Show the rendered configuration instead of pushing it to the device",
)
@click.pass_context
def task(ctx, task_number, show):
    """
    Render configuration from task<TASK_NUMBER>.yaml and task<TASK_NUMBER>.j2,
    display it, and push the configuration to a device.
    """
    # Define filenames based on the task number
    wsf = os.getenv("CONTAINERWSF", os.getcwd())
    yaml_file = f"task{task_number}.yaml"

    print(f"Loading YAML file: {wsf}/solutions/{yaml_file}")
    devices = load_yaml(f'{wsf}/solutions/{yaml_file}')

    for device, data in devices.items():
        config = data['config']
        commands = convert_yaml_to_commands(config)
        
        if show:
            rprint(f"[blue]{device}:[/blue]")
            rprint(f"[green]{config}[/green]")
        else:
            try:
                conn = connect_to_device_netmiko(data['conn'])
                conn.enable()
                conn.send_config_set(commands)
                conn.disconnect()
                print(f"Configuration pushed to {device} successfully.")
            except Exception as e:
                print(f"Failed to push configuration to {device}: {e}")
                if ctx.obj["debug"]:
                    rprint(f"[red]Error:[/red] {e}")
    

if __name__ == '__main__':
    cli()
