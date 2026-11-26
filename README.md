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
```

File names are read as `task<task><subtask>.yaml`: the first digit is the task,
any following digits a subtask, so `task 6` runs `task61.yaml` and `task62.yaml`
and they run before `task7.yaml`. Task numbers above 9 are not supported.

A failed push or host command stops the run and exits 1.

```

autonetops tshoot 1              # deploy a troubleshooting scenario
autonetops restart --lab <name>  # redeploy the containerlab topology
autonetops wireshark             # pull the packet-capture images
```

### Host tasks

Task files normally map a device name to a `conn`/`config` block that is pushed
over SSH. To run commands **on the host that runs the CLI** instead (install
packages, copy files, `curl`, …), give the entry a local `platform` — no other
change to the file structure. Host and device entries can live in the same
`task<N>.yaml` and run under the same `autonetops task N`:

```yaml
r11:                       # pushed to the device over SSH (unchanged)
  conn:
    host: r11
    platform: cisco_iosxe
    auth_username: admin
    auth_password: autonetops
  config: |
    ip route 192.168.100.0 255.255.255.0 121.121.121.21

setup:                     # runs on the host
  conn:
    platform: local        # also: host, shell, linux, bash, localhost
  config: |
    sudo apt install -y curl
    curl -sO http://198.51.100.10/lab.cfg
    cp lab.cfg /etc/lab/
```

The `config` block runs as a single `bash` script (with `set -e`, so a failing
command fails the task, and `cd`/variables carry across lines). Commands must be
non-interactive — use `apt install -y`, passwordless/`sudo -n`, etc.; stdin is
closed. Add `--cli-verbose` to stream output as it runs (for device entries it
prints the device's reply after the push). Host entries work in
`tshoot` scenarios too.

Device entries are pushed in parallel, but host entries run **one at a time in
file order** (they share the host's dpkg lock, working files, and current
directory), so you can rely on an earlier host entry finishing before the next
one starts. If one fails, the host entries after it are skipped.

### VPN

Install and manage the Cisco sandbox VPN (OpenConnect). `setup` installs the
`openconnect` package with apt and needs sudo.

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
