# Cisco IOS-XE Switch Software Upgrade Script

A Python automation tool for upgrading Cisco Catalyst switches running IOS-XE using **install mode** (not bundle mode).

## Features

- **Staged workflow** — Run phases separately or all at once
- **Pre-stage tasks** — Backup config, write mem, remove inactive packages
- **SCP file transfer** — Secure image transfer without reload
- **Install mode activation** — Proper `install add/activate/commit` workflow
- **Batch operations** — Upgrade multiple switches from a list
- **Interactive confirmations** — Safety prompts before destructive operations
- **Pre-flight health checks** — CPU, memory, and stack health validation before upgrade
- **MD5 image verification** — Hash check before and after transfer to catch corruption
- **Post-upgrade verification** — Waits for switch reboot and confirms new version
- **Automatic rollback** — Reverts to previous version if post-upgrade check fails

## Workflow Phases

The script supports three phases that can be run independently or together:

```
┌─────────────────────────────────────────────────────────────────────┐
│                          UPGRADE WORKFLOW                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  PRE-FLIGHT HEALTH CHECK (automatic, --skip-health-check to skip)   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  1. CPU utilization (fail if >80%, warn if >60%)             │   │
│  │  2. Memory utilization (fail if >90%, warn if >80%)          │   │
│  │  3. Stack member health (fail if any member not "Ready")     │   │
│  │                                                              │   │
│  │  If critical issue found → abort upgrade for this switch     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              ↓                                      │
│  PHASE 1: PRE-STAGE (--prestage)                                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  1. Backup running-config to local file                      │   │
│  │  2. write memory (save config to startup)                    │   │
│  │  3. install remove inactive (free up flash space)            │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              ↓                                      │
│  PHASE 2: TRANSFER (--transfer)                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  1. Compute local MD5 hash of image file                     │   │
│  │  2. Check flash space                                        │   │
│  │  3. Transfer image via SCP                                   │   │
│  │  4. Verify MD5 on switch matches local hash                  │   │
│  │                                                              │   │
│  │  !!!NO RELOAD - switch continues running current version     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              ↓                                      │
│  PHASE 3: ACTIVATE (--activate)                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  1. Verify image exists on flash                             │   │
│  │  2. Run: install add file flash:<image> activate commit      │   │
│  │  3. Respond 'y' to reload prompt                             │   │
│  │                                                              │   │
│  │  !!!TRIGGERS RELOAD - switch reboots with new version        │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              ↓                                      │
│  POST-UPGRADE VERIFICATION (--verify-upgrade)                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  1. Wait for switch to come back online (polls every 30s)    │   │
│  │  2. Reconnect via SSH                                        │   │
│  │  3. Run "show version" and compare to expected version       │   │
│  │  4. If mismatch + --auto-rollback → install rollback         │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Requirements

!!Use a virtual enviroment when running scripts to aviod python version conflicts

Create the virtual enviroment
```bash
py -3.14 -m venv venv
```
install packages inside venv
```bash
.\venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
```

### Python Packages

```bash
pip install netmiko
```

### Switch Configuration

Ensure your IOS-XE switches have SCP enabled:

```bash
ip ssh version 2
ip scp server enable
aaa authorization exec default local
```

The user account needs privilege level 15 access.

## Installation

```bash
# Download the script
curl -O https://example.com/iosxe_upgrade.py
chmod +x iosxe_upgrade.py

# Install dependencies
.\venv\Scripts\python.exe -m pip install netmiko

# Optional: For encrypted credentials file support
.\venv\Scripts\python.exe -m pip install cryptography

# Optional: For Excel file support
.\venv\Scripts\python.exe -m pip install openpyxl
```

## Usage

### Command Line Options

```bash
Required (one of):
  --host HOST           Single switch IP or hostname
  --hosts FILE          File containing list of switches

Actions (at least one required):
  --prestage            Backup config, write mem, remove inactive packages
  --transfer            Transfer image via SCP (no reload)
  --activate            Run install add/activate/commit (triggers reload)
  --full                Run all phases: prestage → transfer → activate

Image (required for --transfer and --activate):
  --image FILE          Path to IOS-XE image file

Authentication:
  -u, --username        SSH username
  -p, --password        SSH password (prompts if not provided)
  --enable              Enable password (if different)

Options:
  --port PORT           SSH port (default: 22)
  --dest-path PATH      Destination filesystem (default: flash:)
  --timeout SECONDS     Command timeout (default: 600)
  --skip-backup         Skip config backup during prestage
  --backup-dir DIR      Backup directory (default: ./backups)
  --no-confirm          Skip confirmation prompts

Verification & Safety:
  --skip-md5            Skip MD5 hash verification during transfer
  --skip-health-check   Skip pre-flight health checks (CPU, memory, stack)
  --verify-upgrade      Wait for switch reboot and verify new version after activate
  --auto-rollback       Auto rollback if version check fails (requires --verify-upgrade)
  --verify-wait SECS    Max seconds to wait for reboot (default: 1200)
```
==============================================================================================================================================================

# Logging
The script automatically generates detailed log files capturing all Netmiko SSH session activity and script operations.
Log File Location
By default, logs are saved to ./logs/iosxe_upgrade_YYYYMMDD_HHMMSS.log
```bash
# Custom log directory
python iosxe_upgrade.py --hosts switches.txt --image ios.bin --transfer --log-dir /var/log/upgrades

# Disable logging
python iosxe_upgrade.py --hosts switches.txt --prestage --no-log

What's Logged
- All SSH commands sent to switches
- All command output received
- Connection events (connect, disconnect, errors)
- File transfer progress
- Phase completion status (success/failure)
- Timestamps for all events

Example Log Output
2025-01-15 14:30:22 - INFO - iosxe_upgrade - IOS-XE Upgrade Script Started
2025-01-15 14:30:22 - INFO - iosxe_upgrade - Target switches: 2
2025-01-15 14:30:22 - INFO - iosxe_upgrade - Processing switch: 192.168.1.10
2025-01-15 14:30:23 - INFO - iosxe_upgrade - Connecting to 192.168.1.10 on port 22
2025-01-15 14:30:25 - INFO - iosxe_upgrade - Successfully connected to 192.168.1.10
2025-01-15 14:30:25 - DEBUG - netmiko - write_channel: show version | include Software
2025-01-15 14:30:26 - DEBUG - netmiko - read_channel: Cisco IOS XE Software, Version 17.09.04a
2025-01-15 14:30:26 - INFO - iosxe_upgrade - Starting transfer phase on 192.168.1.10
2025-01-15 14:30:26 - INFO - iosxe_upgrade - Starting SCP transfer: cat9k_iosxe.17.13.01.SPA.bin -> flash:
2025-01-15 14:45:30 - INFO - iosxe_upgrade - SCP transfer completed in 15.1 minutes
2025-01-15 14:45:31 - INFO - iosxe_upgrade - Image verified on flash: flash:cat9k_iosxe.17.13.01.SPA.bin
2025-01-15 14:45:31 - INFO - iosxe_upgrade - Transfer phase on 192.168.1.10: SUCCESS

# Using Logs for Troubleshooting
# View recent errors
```bash
grep "ERROR" logs/iosxe_upgrade_*.log
```
# Check specific switch
```bash
grep "192.168.1.10" logs/iosxe_upgrade_20250115_*.log
```
# See all commands sent
```bash
grep "write_channel" logs/iosxe_upgrade_*.log
```
=========================================================================================================================================================

# Secure Credential Options
# For scheduled/unattended runs, you have three secure options:
# Option 1: Encrypted Credentials File (Recommended)

# Step 1: Create the encrypted credentials file
```bash
python iosxe_upgrade.py --create-creds ~/.switch_creds.enc

# You'll be prompted for:
#   - Switch username
#   - Switch password  
#   - Enable password
#   - Master password (to encrypt the file)
```
# Step 2: Use the credentials file
```bash
python iosxe_upgrade.py --hosts switches.txt --image ios.bin --creds-file ~/.switch_creds.enc --activate

# For fully unattended runs, set the master password in environment:
export CREDS_MASTER_PASS='your_master_password'
python iosxe_upgrade.py --hosts switches.txt --image ios.bin --creds-file ~/.switch_creds.enc --activate --no-confirm
```
# Option 2: Environment Variables

# Linux/Mac
```bash
export SWITCH_USER='admin'
export SWITCH_PASS='switchpassword'
export SWITCH_ENABLE='enablepassword'  # Optional, defaults to SWITCH_PASS

python iosxe_upgrade.py --hosts switches.txt --image ios.bin --env-creds --activate --no-confirm
```
# Windows (PowerShell)
```bash
$env:SWITCH_USER='admin'
$env:SWITCH_PASS='switchpassword'
python iosxe_upgrade.py --hosts switches.txt --image ios.bin --env-creds --activate --no-confirm
```
# Option 3: Command Line Arguments (Least Secure)
```bash
# Only use in secure environments - password visible in process list
python iosxe_upgrade.py --hosts switches.txt --image ios.bin -u admin -p password --activate
```
# Scheduling Upgrades
# Linux (cron)
```bash
# Edit crontab
crontab -e

# Run at 2:00 AM on Saturday using encrypted credentials
0 2 * * 6 CREDS_MASTER_PASS='masterpass' /usr/bin/python3 /home/user/iosxe_upgrade.py \
    --hosts /home/user/switches.txt \
    --image /home/user/images/ios.bin \
    --creds-file /home/user/.switch_creds.enc \
    --activate --no-confirm >> /var/log/switch_upgrade.log 2>&1
```
# Windows (Task Scheduler)

1. Create a batch file upgrade.bat:

```bash
batch
   @echo off
   set CREDS_MASTER_PASS=masterpass
   python C:\scripts\iosxe_upgrade.py --hosts C:\scripts\switches.txt --image C:\images\ios.bin --creds-file C:\scripts\.switch_creds.enc --activate --no-confirm >> C:\logs\upgrade.log 2>&1
```
2. Open Task Scheduler → Create Basic Task
3. Set trigger (e.g., Saturday 2:00 AM)
4. Action: Start upgrade.bat

====================================================================================================================================================================================================================

### Common Workflows

#### Full Upgrade (All Phases)
9200 lite image:
```bash
.\venv\scripts\python.exe iosxe_upgrade.py --hosts switches.txt --image ciscosoftware\cat9k_lite_iosxe.17.15.04.SPA.bin --full --no-confirm
```
9300 image:
```bash
.\venv\scripts\python.exe iosxe_upgrade.py --hosts switches.txt --image ciscosoftware\cat9k_iosxe.17.15.04.SPA.bin --full
```

#### Pre-Stage Only (No Downtime)
Prepare switches without any impact:
```bash
python iosxe_upgrade.py --hosts switches.txt --prestage
```

#### Transfer Only (Stage Image)
Push the image during business hours, reload later:

9200 lite image:
```bash
python iosxe_upgrade.py --hosts switches.txt --image ciscosoftware\cat9k_lite_iosxe.17.15.05.SPA.bin --transfer
```
9300 image:
```bash
python iosxe_upgrade.py --hosts switches.txt --image ciscosoftware\cat9k_iosxe.17.15.05.SPA.bin --transfer
```

#### Activate Only (Maintenance Window)
Trigger the upgrade when ready: Use --no-confirm on the end if you don't want babysit the reboot for each device.

9200 lite image:
```bash
python iosxe_upgrade.py --hosts switches.txt --image ciscosoftware\cat9k_lite_iosxe.17.15.04.SPA.bin --activate
```
9300 image:
```bash
python iosxe_upgrade.py --hosts switches.txt --image ciscosoftware\cat9k_iosxe.17.15.04b.SPA.bin --activate
```

#### Transfer + Activate (Back to Back)

9200 lite image:
```bash
python iosxe_upgrade.py --hosts switches.txt --image ciscosoftware\cat9k_lite_iosxe.17.15.04.SPA.bin --transfer --activate
```
9300 image:
```bash
python iosxe_upgrade.py --hosts switches.txt --image ciscosoftware\cat9k_iosxe.17.15.04.SPA.bin --transfer --activate
```

#### Full Upgrade with Verification and Auto-Rollback
Runs all phases, waits for switch to reboot, verifies the new version, and rolls back automatically if the version doesn't match:
```bash
python iosxe_upgrade.py --hosts switches.txt --image ciscosoftware\cat9k_iosxe.17.15.05.SPA.bin --full --verify-upgrade --auto-rollback
```

#### Activate with Post-Upgrade Verification Only
Trigger the upgrade and verify it worked (no auto-rollback, just reporting):
```bash
python iosxe_upgrade.py --hosts switches.txt --image ciscosoftware\cat9k_iosxe.17.15.05.SPA.bin --activate --verify-upgrade
```

#### Transfer with MD5 Verification (default)
MD5 hash is computed locally before transfer and verified on the switch after:
```bash
python iosxe_upgrade.py --hosts switches.txt --image ciscosoftware\cat9k_iosxe.17.15.05.SPA.bin --transfer
```

#### Transfer without MD5 (faster, less safe)
Skip MD5 if you're in a hurry and trust the network:
```bash
python iosxe_upgrade.py --hosts switches.txt --image ciscosoftware\cat9k_iosxe.17.15.05.SPA.bin --transfer --skip-md5
```

#### Skip Pre-Flight Health Checks
If you've already validated the switches and want to skip CPU/memory/stack checks:
```bash
python iosxe_upgrade.py --hosts switches.txt --image ciscosoftware\cat9k_iosxe.17.15.05.SPA.bin --full --skip-health-check
```

### Hosts File Format

The scripts support multiple file formats:

**Text file (.txt)** - One switch per line:
```
# switches.txt
# Core switches - upgrade first
192.168.1.10
192.168.1.11

# Access switches
10.0.0.50
switch-access-01.example.com
```

**Excel file (.xlsx)** - First column contains IPs/hostnames:
| IP Address    | Location   | Model     |
|---------------|------------|-----------|
| 192.168.1.10  | Building A | C9300-24P |
| 192.168.1.11  | Building B | C9300-48P |
| 10.0.0.50     | Floor 1    | C9200L    |

The script automatically:
- Reads from the first column only
- Skips the header row if detected (looks for words like "ip", "host", "switch", "address")
- Ignores empty cells
```bash
# Use Excel file
python iosxe_upgrade.py --hosts switches.xlsx --image ios.bin --transfer

# Use text file
python iosxe_upgrade.py --hosts switches.txt --image ios.bin --transfer
```

## Output Example

```
============================================================
IOS-XE UPGRADE PLAN
============================================================
  Target switches: 2
  Actions:
    • Pre-flight health check (CPU, memory, stack)
    • Pre-stage (backup, write mem, remove inactive)
    • Transfer image: cat9k_lite_iosxe.17.15.05.SPA.bin
    • MD5 verification (pre and post transfer)
    • Activate & reload (install add/activate/commit)
    • Post-upgrade verification (wait for reboot, check version)
    • Auto-rollback (if version check fails)

  ⚠ WARNING: --activate will reload switches!

Proceed with upgrade? (yes/no): yes

############################################################
# SWITCH: 192.168.1.10
############################################################

  Connecting to 192.168.1.10...
  ✓ Connected and in enable mode

  Current Version Info:
    Cisco IOS XE Software, Version 17.09.04a
    Switch uptime is 45 days, 3 hours

  --- Pre-Flight Health Check ---
  ✓ CPU utilization: 7% (5-min avg)
  ✓ Memory utilization: 42%
  ✓ Stack member 1: Ready
  ✓ Stack member 2: Ready

  ✓ All pre-flight checks passed

==================================================
PRE-STAGE TASKS
==================================================

  --- Backing Up Configuration ---
  Retrieving running-config...
  ✓ Config saved to: backups/backup_192.168.1.10_20250115_143022.txt

  --- Saving Configuration ---
  Running 'write memory'...
  ✓ Configuration saved successfully

  --- Removing Inactive Packages ---
  Running 'install remove inactive'...
  (This may take several minutes)
  ✓ Inactive packages removed (or none to remove)

==================================================
IMAGE TRANSFER
==================================================

  --- Computing Local MD5 Hash ---
  Hashing local file: 100%
  Local MD5: a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4

  --- Checking Prerequisites ---
  Image size: 485.3 MB
  Flash free: 2048.0 MB
  ✓ Sufficient space available

  --- Transferring Image ---
  Starting SCP transfer of cat9k_lite_iosxe.17.15.05.SPA.bin...
  (This may take 10-30 minutes for large images)
  Transfer completed in 12.3 minutes
  ✓ Image verified on flash

  --- Post-Transfer MD5 Verification ---
  Verifying MD5 on switch (this may take several minutes)...
  ✓ MD5 verified: a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4
  ✓ Image integrity confirmed after transfer

==================================================
ACTIVATE & RELOAD
==================================================

  --- Verifying Image ---
  ✓ Image found: flash:cat9k_lite_iosxe.17.15.05.SPA.bin

  WARNING: This will reload the switch!
  Proceed with install and reload? (yes/no): yes

  --- Running Install Add/Activate/Commit ---
  Command: install add file flash:cat9k_lite_iosxe.17.15.05.SPA.bin activate commit
  This will trigger a reload. Please wait...
  (This process can take 5-15 minutes)
  Install initiated, confirming reload...

  ✓ Install activate commit initiated
  ✓ Reload confirmed - switch is now rebooting

  Waiting for 192.168.1.10 to reboot and come back online...
  (Will check every 30s for up to 20 minutes)
  Waiting 60s for switch to begin reload...
  Connection attempt 1 (90s elapsed)...
  Connection attempt 2 (120s elapsed)...
  Connection attempt 5 (210s elapsed)...
  ✓ Switch 192.168.1.10 is back online! (210s total)

  --- Post-Upgrade Version Verification ---
  ✓ Running version: 17.15.05 (matches expected 17.15.05)

============================================================
FINAL SUMMARY
============================================================

  Successful (1):
    ✓ 192.168.1.10

  Full log saved to: logs/iosxe_upgrade_20250115_143022.log
```

## Safety Features

### Pre-Flight Health Checks (automatic)

Before any upgrade operations begin, the script checks the switch's operational health. This runs automatically every time and does not require any flags.

| Check | Warning Threshold | Critical Threshold (aborts upgrade) |
|-------|-------------------|-------------------------------------|
| CPU utilization (5-min avg) | > 60% | > 80% |
| Memory utilization | > 80% | > 90% |
| Stack member state | — | Any member not in "Ready" state |

If a critical issue is found, the upgrade is aborted for that switch (with an override prompt unless `--no-confirm` is set). Other switches in the batch continue normally.

To skip: `--skip-health-check`

### MD5 Image Verification (automatic during transfer)

During `--transfer`, the script automatically:
1. Computes the MD5 hash of the local image file before transfer
2. After SCP completes, runs `verify /md5 flash:<image>` on the switch
3. Compares both hashes — if they don't match, the transfer is marked as failed

This catches corrupt images, truncated transfers, and bit-rot before you activate a bad image.

If the image already exists on flash, the script verifies its MD5 against the local file. If the hashes match, the transfer is skipped entirely (saving time on re-runs).

To skip: `--skip-md5`

### Post-Upgrade Verification (opt-in)

When `--verify-upgrade` is used with `--activate`, the script will:
1. Wait for the switch to finish rebooting (polls SSH every 30 seconds)
2. Reconnect and run `show version`
3. Compare the running version against the version extracted from the image filename
4. Report success or failure

The maximum wait time defaults to 20 minutes and can be changed with `--verify-wait`.

```bash
# Activate and verify
python iosxe_upgrade.py --hosts switches.txt --image cat9k_iosxe.17.15.05.SPA.bin --activate --verify-upgrade

# Activate and verify with 30-minute wait
python iosxe_upgrade.py --hosts switches.txt --image cat9k_iosxe.17.15.05.SPA.bin --activate --verify-upgrade --verify-wait 1800
```

### Automatic Rollback (opt-in)

When `--auto-rollback` is used with `--verify-upgrade`, the script will automatically run `install rollback to committed` if the post-upgrade version check fails. This reverts the switch to whatever version was committed before the activation.

The switch will reload again during rollback.

```bash
# Full upgrade with safety net
python iosxe_upgrade.py --hosts switches.txt --image cat9k_iosxe.17.15.05.SPA.bin --full --verify-upgrade --auto-rollback
```

**When rollback triggers:**
- Version mismatch detected after reboot
- Switch comes back on wrong version (e.g., fell back to old image)
- `install rollback to committed` is executed automatically

**When rollback does NOT trigger:**
- Switch doesn't come back online (manual intervention needed)
- Version check succeeds
- `--auto-rollback` is not specified

## How the Install Mode Works

IOS-XE uses **install mode** for software upgrades (recommended over bundle mode):

### The Command
```
install add file flash:cat9k_lite_iosxe.17.13.01.SPA.bin activate commit
```

This single command performs three operations:
1. **add** — Extracts and adds packages to the repository
2. **activate** — Stages packages for the next boot
3. **commit** — Makes the change persistent

### The Reload Prompt

After running this command, the switch prompts:
```
This operation may require a reload of the system. Do you want to proceed? [y/n]
```

**CRITICAL**: You must respond `y` within the timeout or the entire operation is cancelled. This script handles this automatically.

### Verification After Upgrade

After the switch reboots:
```
show version
show install summary
show install log
```

## Troubleshooting

### Common Issues

**"SCP transfer failed"**
- Verify `ip scp server enable` is configured
- Check that SSH credentials have privilege 15
- Ensure AAA authorization allows file transfers

**"install remove inactive" hangs**
- This is normal for large package removals
- Increase timeout with `--timeout 900`
- Can skip with `--prestage` without running separately

**"Install command cancelled"**
- The script failed to respond 'y' to the reload prompt
- May indicate network latency - try with `--timeout 900`
- Run `--activate` separately if needed

**"Insufficient space"**
- Run `--prestage` first to remove inactive packages
- Manually delete old images: `delete flash:old_image.bin`

**Connection timeout during activate**
- This is often normal - the switch is rebooting
- Check switch status after 10-15 minutes
- Verify with `show version` once accessible

### Manual Recovery

If the script fails mid-upgrade:

```cisco
! Check current install state
show install summary
show install log

! If packages are in "U" (uncommitted) state
install commit

! If you need to rollback
install rollback to committed

! Remove a specific package
install remove file flash:<filename>
```

## Supported Platforms

Tested with:
- Cisco Catalyst 9200/9200L
- Cisco Catalyst 9300/9300L
- Cisco Catalyst 9400
- Cisco Catalyst 9500

Should work with any IOS-XE platform that supports install mode.

## Safety Considerations

- **Always test in a lab first**
- **Run `--prestage` during business hours** — no impact
- **Run `--transfer` during business hours** — no reload
- **Schedule `--activate` for maintenance windows** — triggers reload
- **Keep console access available** — in case of boot issues
- **Verify image compatibility** with your hardware model

