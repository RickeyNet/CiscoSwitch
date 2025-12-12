# Cisco Nexus NX-OS Upgrade Scripts

Python automation tools for upgrading Cisco Nexus switches running NX-OS.

## Scripts Included

| Script | Purpose |
|--------|---------|
| `nxos_upgrade.py` | Full upgrade workflow (prestage, transfer, activate) |
| `nxos_version_check.py` | Check current NX-OS versions |
| `nxos_save_config.py` | Save running-config to startup-config |

## Minimum Version Requirement

These scripts are designed for **NX-OS 10.2.1.M or greater** (nxos64-cs.10.2.1.M.bin).

The version check script can flag switches below this minimum with `--check-minimum`.

## Requirements

```bash
# Required
pip install netmiko

# Optional
pip install openpyxl      # Excel file support
pip install cryptography  # Encrypted credentials
```

## NX-OS Upgrade Process

NX-OS uses the `install all` command (different from IOS-XE):

```
install all nxos bootflash:<image>
```

This command:
1. Validates the image
2. Checks compatibility
3. Performs the upgrade
4. Reloads the switch

## Workflow Phases

```
┌────────────────────────────────────────────────────────────────┐
│                      NX-OS UPGRADE WORKFLOW                    │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  PHASE 1: PRE-STAGE (--prestage)                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. Check current version                               │   │
│  │  2. Backup running-config                               │   │
│  │  3. Verify bootflash space                              │   │
│  │  4. Save configuration                                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                 │
│  PHASE 2: TRANSFER (--transfer)                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. Check bootflash space                               │   │
│  │  2. Transfer image via SCP                              │   │
│  │  3. Verify image on bootflash                           │   │
│  │  4. Save configuration                                  │   │
│  │                                                         │   │
│  │  !! NO RELOAD - switch continues running                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                 │
│  PHASE 3: ACTIVATE (--activate)                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. Verify image exists                                 │   │
│  │  2. Run compatibility check                             │   │
│  │  3. Execute: install all nxos bootflash:<image>         │   │
│  │  4. Confirm upgrade prompt                              │   │
│  │                                                         │   │
│  │  !! TRIGGERS RELOAD - switch reboots                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## Usage Examples

### Full Upgrade

```bash
python nxos_upgrade.py --hosts switches.txt --image nxos64-cs.10.4.1.F.bin --full
```

### Staged Upgrade

```bash
# Step 1: Pre-stage (during business hours)
python nxos_upgrade.py --hosts switches.txt --prestage

# Step 2: Transfer image (during low-usage period)
python nxos_upgrade.py --hosts switches.txt --image nxos64-cs.10.4.1.F.bin --transfer

# Step 3: Activate (maintenance window)
python nxos_upgrade.py --hosts switches.txt --image nxos64-cs.10.4.1.F.bin --activate
```

### Version Check

```bash
# Basic check
python nxos_version_check.py --hosts switches.txt

# Check with minimum version flagging
python nxos_version_check.py --hosts switches.txt --check-minimum

# Export to CSV
python nxos_version_check.py --hosts switches.txt --csv versions.csv -v
```

### Save Configuration

```bash
python nxos_save_config.py --hosts switches.txt
```

## Command Line Options

### nxos_upgrade.py

```
Target:
  --host HOST           Single switch
  --hosts FILE          File with switch list (.txt or .xlsx)

Actions:
  --prestage            Backup, version check, space check
  --transfer            Copy image via SCP
  --activate            Run install all (triggers reload)
  --full                All phases

Image:
  --image FILE          Path to NX-OS image file

Authentication:
  -u, --username        SSH username
  -p, --password        SSH password
  --creds-file FILE     Encrypted credentials file
  --create-creds FILE   Create encrypted credentials
  --env-creds           Use SWITCH_USER/SWITCH_PASS env vars

Options:
  --port PORT           SSH port (default: 22)
  --timeout SECONDS     Command timeout (default: 600)
  --dest-path PATH      Destination (default: bootflash:)
  --non-disruptive      Attempt ISSU if supported
  --force               Force upgrade past warnings
  --skip-version-check  Skip minimum version check
  --skip-backup         Skip config backup
  --backup-dir DIR      Backup directory (default: ./backups)
  --no-confirm          Skip confirmation prompts

Logging:
  --log-dir DIR         Log directory (default: ./logs)
  --log-level LEVEL     DEBUG, INFO, WARNING, ERROR
  --no-log              Disable logging
```

## Hosts File Format

**Text file (.txt)**
```
# Nexus switches
192.168.1.10
192.168.1.11
nexus-core-01.example.com
```

**Excel file (.xlsx)** - First column contains IPs:
| IP Address | Location | Model |
|------------|----------|-------|
| 192.168.1.10 | DC1 | N9K-C93180YC |
| 192.168.1.11 | DC2 | N9K-C9336C |

## Credential Options

### Interactive (default)
```bash
python nxos_upgrade.py --hosts switches.txt --prestage
# Prompts for username/password
```

### Command line
```bash
python nxos_upgrade.py --hosts switches.txt -u admin -p password --prestage
```

### Environment variables
```bash
export SWITCH_USER='admin'
export SWITCH_PASS='password'
python nxos_upgrade.py --hosts switches.txt --env-creds --prestage
```

### Encrypted file (recommended for automation)
```bash
# Create encrypted credentials (one-time)
python nxos_upgrade.py --create-creds ~/.nxos_creds.enc

# Use encrypted credentials
python nxos_upgrade.py --hosts switches.txt --creds-file ~/.nxos_creds.enc --prestage

# For fully unattended runs
export CREDS_MASTER_PASS='masterpassword'
python nxos_upgrade.py --hosts switches.txt --creds-file ~/.nxos_creds.enc --full --no-confirm
```

## Non-Disruptive Upgrade (ISSU)

Some Nexus platforms support In-Service Software Upgrade (ISSU):

```bash
python nxos_upgrade.py --hosts switches.txt --image nxos.bin --activate --non-disruptive
```

**Note:** ISSU support depends on:
- Platform (not all Nexus models support it)
- Source and target versions
- Current switch configuration
- Feature compatibility

If non-disruptive isn't possible, the switch will perform a standard reload.

## Example Output

```
============================================================
NX-OS UPGRADE PLAN
============================================================
  Target switches: 2
  Actions:
    • Pre-stage (backup, version check, space check)
    • Transfer image: nxos64-cs.10.4.1.F.bin
    • Activate (standard - install all)

  ⚠ WARNING: --activate will reload switches!

Proceed? (yes/no): yes

############################################################
# SWITCH: 192.168.1.10
############################################################

  Connecting to 192.168.1.10...
  ✓ Connected

  Current: 10.2(1)M (Nexus 9300)

==================================================
PRE-STAGE TASKS
==================================================

  --- Checking Current Version ---
  Hostname: NEXUS-CORE-01
  Model: Nexus 9300
  Version: 10.2(1)M
  Serial: FDO12345678

  --- Backing Up Configuration ---
  Retrieving running-config...
  ✓ Config saved to: backups/backup_192.168.1.10_20250115_143022.txt

  --- Checking Bootflash Space ---
  Image size: 1847.3 MB
  Bootflash free: 12048.0 MB
  ✓ Sufficient space available

  --- Saving Configuration ---
  Running 'copy running-config startup-config'...
  ✓ Configuration saved

==================================================
IMAGE TRANSFER
==================================================

  --- Checking Prerequisites ---
  Image size: 1847.3 MB
  Bootflash free: 12048.0 MB
  ✓ Sufficient space available

  --- Transferring Image ---
  Starting SCP transfer of nxos64-cs.10.4.1.F.bin...
  (This may take 15-45 minutes for large images)
  Transfer completed in 18.3 minutes
  ✓ Image verified on bootflash

  --- Saving Configuration ---
  Running 'copy running-config startup-config'...
  ✓ Configuration saved

==================================================
ACTIVATE & RELOAD
==================================================

  --- Verifying Image ---
  ✓ Image found: bootflash:nxos64-cs.10.4.1.F.bin

  --- Checking Image Compatibility ---
  Running compatibility check...
  (This may take a few minutes)
  ✓ Compatibility check passed

  WARNING: This will reload the switch!
  Proceed? (yes/no): yes

  --- Running Install All ---
  Command: install all nxos bootflash:nxos64-cs.10.4.1.F.bin
  This will trigger a reload. Please wait...
  Install initiated, confirming...

  ✓ Install all initiated
  ✓ Switch is now upgrading and will reload

  The switch will be unavailable for 10-30 minutes.
  After reboot, verify with: show version

============================================================
FINAL SUMMARY
============================================================

  Successful (1):
    ✓ 192.168.1.10

  Note: Activated switches are now rebooting.
  Verify upgrade with: show version

  Full log: logs/nxos_upgrade_20250115_143022.log
```

## Troubleshooting

### Common Issues

**"Authentication failed"**
- Verify username/password
- Check if SSH is enabled on the switch
- Verify user has admin privileges

**"Connection timeout"**
- Check network connectivity
- Verify SSH is reachable (port 22)
- Increase timeout with `--timeout 60`

**"Insufficient bootflash space"**
- Delete old images: `delete bootflash:old_image.bin`
- Check space: `dir bootflash:`

**"Compatibility check failed"**
- Verify image is correct for your platform
- Check release notes for known issues
- Use `--force` to proceed anyway (with caution)

**"Transfer failed"**
- Ensure `feature scp-server` is enabled
- Check bootflash space
- Verify SCP connectivity

### Manual Recovery

If upgrade fails mid-process:

```
! Check current boot image
show boot

! Check installed packages
show install all status

! If switch is stuck, boot from loader:
loader> boot bootflash:nxos64-cs.10.2.1.M.bin
```

## Supported Platforms

Tested with:
- Nexus 9300 series
- Nexus 9500 series
- Nexus 3000 series

Should work with any NX-OS platform that supports:
- `install all nxos` command
- SCP file transfer
- SSH management access

## Differences from IOS-XE Scripts

| Feature | IOS-XE | NX-OS |
|---------|--------|-------|
| Upgrade command | `install add file ... activate commit` | `install all nxos` |
| Destination | `flash:` | `bootflash:` |
| ISSU option | Not in script | `--non-disruptive` |
| Compatibility check | `show install all impact` | `show install all impact nxos` |
| Save config | `write memory` | `copy running-config startup-config` |

## License

MIT License - Use at your own risk.