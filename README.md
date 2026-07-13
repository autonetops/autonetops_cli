# autonetops

CLI for autonetops labs and exercises.

## Install

Dependencies are declared in `pyproject.toml`, so installing the package pulls them in.

```
pip install -e .          # editable install for development
pip install -e ".[dev]"   # also installs pytest to run the test suite
```

## Usage

```
autonetops task 3                # render and push a single task
autonetops task 2-5              # a range of tasks
autonetops task all              # every task in solutions/
autonetops task 3 --show         # print the config instead of pushing it

autonetops tshoot 1              # deploy a troubleshooting scenario
autonetops restart --lab <name>  # redeploy the containerlab topology
autonetops wireshark             # pull the packet-capture images
```

### VPN

Install and manage the Cisco sandbox VPN (OpenConnect). `setup` installs system
packages and needs sudo.

```
autonetops vpn setup
autonetops vpn connect --domain <host> --port <port> --user <user>
autonetops vpn status
autonetops vpn disconnect
```

`vpn status` exits 0 when the tunnel is up and 1 when it is down, so it can gate
other commands.

## Tests

```
pytest
```
