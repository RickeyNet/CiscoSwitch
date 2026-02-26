# SNMPv3 Configuration Tool

Connects to Cisco Catalyst switches and applies a standardized SNMPv3 configuration from a template file. Shows existing SNMP config before changes and verifies SNMPv3 user creation after.

## Setup

```bash
pip install netmiko
```

## Files

| File                      | Purpose                                           |
|---------------------------|---------------------------------------------------|
| `snmpv3_configurator.py`  | Main script                                       |
| `switches.txt`            | Switch IPs/hostnames, one per line                |
| `snmpv3_template.txt`     | SNMPv3 commands to apply (one per line)           |
| `logs/`                   | Auto-created directory with timestamped log files |

## Usage

1. Edit `switches.txt` with your switch IPs.
2. Edit `snmpv3_template.txt` with your SNMPv3 commands — **update the auth and priv passwords before running**.
3. Run the script:

```bash
python snmpv3_configurator.py
```

4. Enter SSH credentials when prompted.
5. Choose **dry-run** first to preview changes, then re-run in **live mode** to apply.

## How It Works

1. Reads switch IPs from `switches.txt`
2. SSHs into each switch using Netmiko
3. Displays existing SNMP configuration (`show running-config | include snmp-server`)
4. Applies every command from `snmpv3_template.txt` via config mode
5. Verifies the new SNMPv3 user with `show snmp user`
6. Saves the running config to startup config
7. Logs everything to `logs/`

## Example Template

```text
snmp-server group SNMPV3_GROUP v3 priv
snmp-server user SNMPV3_USER SNMPV3_GROUP v3 auth sha AUTH_PASS_HERE priv aes 128 PRIV_PASS_HERE
snmp-server contact NetworkTeam@company.com
snmp-server location DataCenter-Rack01
```

## Safety Features

- **Dry-run mode** — previews changes without touching the switch
- **Confirmation prompt** in live mode before any changes are made
- **Pre-change audit** — shows existing SNMP config before applying anything
- **Post-change verification** — runs `show snmp user` to confirm success
- **Per-switch error handling** — a failed connection skips to the next switch
- **Full logging** to both console and timestamped log files
- **Auto-saves config** after changes on each switch