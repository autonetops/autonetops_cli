import yaml
from netmiko import ConnectHandler
def load_yaml(file_path):
    """
    Load a YAML file and return its content.
    """
    try:
        with open(file_path, 'r') as yf:
            data = yaml.safe_load(yf)
    except FileNotFoundError:
        return (f"YAML file {file_path} not found!")
        

def convert_yaml_to_commands(config):
    """Convert YAML config to list of commands"""
    commands = []
    for line in config.split('\n'):
        line = line.strip()
        commands.append(line.lstrip())
    return commands

def connect_to_device_netmiko(device):
    """
    Connect to a device using Netmiko and return the connection object.
    """
    return ConnectHandler(**device)
