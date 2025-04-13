import yaml
from netmiko import ConnectHandler
import os

def load_yaml(file_path):
    print(f"Attempting to load: {file_path}")
    print(f"File exists: {os.path.exists(file_path)}")
    try:
        with open(file_path, 'r', encoding='utf-8') as yf:
            data = yaml.safe_load(yf)
        print("File loaded successfully")
        return data
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        raise
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file {file_path}: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise
        

def convert_yaml_to_commands(config):
    """split a YAML configuration string into a list of commands."""
    commands = []
    for line in config.splitlines():
        commands.append(line.lstrip())
    return commands

def connect_to_device_netmiko(device):
    """
    Connect to a device using Netmiko and return the connection object.
    """
    return ConnectHandler(**device)
