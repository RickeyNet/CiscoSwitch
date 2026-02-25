# VLAN 1 Access Port Remediation Tool

Connects to Cisco Catalyst switches, finds all access ports still on VLAN 1, and applies a standardized interface configuration from a template file.

## Setup

```bash
pip install netmiko
```

## Files

| File                     | Purpose                                                  |
|--------------------------|----------------------------------------------------------|
| `vlan1_remediation.py`   | Main script                                              |
| `switches.txt`           | Switch IPs/hostnames, one per line                       |
| `interface_template.txt` | Interface commands to apply (no `interface` line needed) |
| `logs/`                  | Auto-created directory with timestamped log files        |

## Usage

1. Edit `switches.txt` with your switch IPs.
2. Edit `interface_template.txt` with the desired port config.
3. Run the script:

```bash
python vlan1_Destroyer.py
```

4. Enter SSH credentials when prompted.
5. Choose **dry-run** first to preview changes, then re-run in **live mode** to apply.

## How It Works

1. Reads switch IPs from `switches.txt`
2. SSHs into each switch using Netmiko
3. Runs `show interfaces switchport` to inventory all ports
4. Filters for ports that are **access mode** AND **VLAN 1**
5. Applies every command from `interface_template.txt` under each matching interface
6. Saves the running config to startup config
7. Logs everything to `logs/`

## Safety Features

- **Dry-run mode** — previews changes without touching the switch
- **Confirmation prompt** in live mode before any changes are made
- **Per-switch error handling** — a failed connection skips to the next switch
- **Full logging** to both console and timestamped log files
- **Auto-saves config** after changes on each switch