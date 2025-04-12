import click
import os
from jinja2 import Template, Environment
import ipdb

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
@click.pass_context
def task(ctx, task_number):
    """
    Render configuration from task<TASK_NUMBER>.yaml and task<TASK_NUMBER>.j2,
    display it, and push the configuration to a device.
    """
    # Define filenames based on the task number
    folder = ''
    yaml_file = folder + f"task{task_number}.yaml"

    print(f"Loading YAML file: {yaml_file}")
    

if __name__ == '__main__':
    cli()
