#!/usr/bin/env python3
"""
SNMPv3 Configuration Script
-----------------------------
Connects to Cisco Catalyst switches listed in switches.txt
and applies SNMPv3 configuration commands from snmpv3_template.txt.

Requirements:
    pip install netmiko

Files needed:
    switches.txt          - One switch IP per line
    snmpv3_template.txt   - SNMPv3 config commands (one per line)
"""

import sys
import os
import getpass
import logging
from datetime import datetime
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SWITCHES_FILE = "switches.txt"
TEMPLATE_FILE = "snmpv3_template.txt"
LOG_DIR = "logs"

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
os.makedirs(LOG_DIR, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(LOG_DIR, f"snmpv3_config_{timestamp}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def load_switches(filepath: str) -> list[str]:
    """Read switch IPs/hostnames from a text file (one per line)."""
    if not os.path.isfile(filepath):
        logger.error(f"Switches file not found: {filepath}")
        sys.exit(1)
    with open(filepath) as f:
        switches = [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]
    logger.info(f"Loaded {len(switches)} switch(es) from {filepath}")
    return switches


def load_template(filepath: str) -> list[str]:
    """Read the SNMPv3 config commands from a text file."""
    if not os.path.isfile(filepath):
        logger.error(f"Template file not found: {filepath}")
        sys.exit(1)
    with open(filepath) as f:
        commands = [
            line.rstrip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]
    logger.info(f"Loaded {len(commands)} template command(s) from {filepath}")
    return commands


def get_existing_snmpv3_config(connection) -> str:
    """Pull current SNMPv3-related lines from the running config."""
    output = connection.send_command("show running-config | include snmp-server")
    return output


def apply_snmpv3_config(
    connection, template_commands: list[str], dry_run: bool = False
) -> str:
    """
    Apply the SNMPv3 template commands to the switch.
    Returns the command output or 'DRY-RUN'.
    """
    if dry_run:
        logger.info("  [DRY-RUN] Would apply the following commands:")
        for cmd in template_commands:
            logger.info(f"    {cmd}")
        return "DRY-RUN"
    else:
        logger.info("  Applying SNMPv3 configuration ...")
        output = connection.send_config_set(template_commands)
        logger.debug(output)
        return output


def verify_snmpv3_config(connection) -> str:
    """Run verification commands after applying the config."""
    logger.info("  Verifying SNMPv3 configuration ...")
    output = connection.send_command("show snmp user")
    return output


def process_switch(
    ip: str,
    username: str,
    password: str,
    secret: str,
    template_commands: list[str],
    dry_run: bool = False,
):
    """Connect to a single switch and apply SNMPv3 configuration."""
    logger.info(f"{'='*60}")
    logger.info(f"Connecting to {ip} ...")

    device = {
        "device_type": "cisco_ios",
        "host": ip,
        "username": username,
        "password": password,
        "secret": secret,
        "timeout": 30,
        "banner_timeout": 30,
    }

    try:
        conn = ConnectHandler(**device)
    except NetmikoTimeoutException:
        logger.error(f"  TIMEOUT connecting to {ip} — skipping.")
        return
    except NetmikoAuthenticationException:
        logger.error(f"  AUTH FAILED for {ip} — skipping.")
        return
    except Exception as e:
        logger.error(f"  Connection error for {ip}: {e} — skipping.")
        return

    try:
        # Enter enable mode if needed
        if not conn.check_enable_mode():
            conn.enable()

        hostname = conn.find_prompt().replace("#", "").replace(">", "").strip()
        logger.info(f"  Connected to {hostname} ({ip})")

        # --- Show existing SNMP config ---
        logger.info("  Checking existing SNMP configuration ...")
        existing_snmp = get_existing_snmpv3_config(conn)
        if existing_snmp.strip():
            logger.info(f"  Current SNMP config:\n{existing_snmp}")
        else:
            logger.info("  No existing SNMP configuration found.")

        # --- Apply SNMPv3 template ---
        result = apply_snmpv3_config(conn, template_commands, dry_run=dry_run)

        # --- Verify and save (unless dry run) ---
        if not dry_run and result != "DRY-RUN":
            verification = verify_snmpv3_config(conn)
            logger.info(f"  SNMPv3 user verification:\n{verification}")

            logger.info("  Saving running config to startup ...")
            conn.save_config()

        logger.info(f"  Finished processing {hostname} ({ip}).")

    finally:
        conn.disconnect()


def main():
    print(
        """
╔══════════════════════════════════════════════════╗
║         SNMPv3 Configuration Tool                ║
╚══════════════════════════════════════════════════╝
"""
    )

    # --- Load files ---
    switches = load_switches(SWITCHES_FILE)
    template_commands = load_template(TEMPLATE_FILE)

    print("\nSNMPv3 commands that will be applied to each switch:")
    for cmd in template_commands:
        print(f"  {cmd}")
    print()

    # --- Credentials ---
    username = input("SSH Username: ").strip()
    password = getpass.getpass("SSH Password: ")
    secret = getpass.getpass("Enable Secret (press Enter if same as password): ")
    if not secret:
        secret = password

    # --- Dry run? ---
    dry_run_input = (
        input("\nPerform a DRY RUN first? (y/n) [y]: ").strip().lower() or "y"
    )
    dry_run = dry_run_input == "y"

    if dry_run:
        logger.info("*** DRY-RUN MODE — no changes will be made ***\n")
    else:
        confirm = input(
            "⚠️  LIVE MODE — changes WILL be written to switches. Continue? (yes/no): "
        )
        if confirm.strip().lower() != "yes":
            logger.info("Aborted by user.")
            sys.exit(0)

    # --- Process each switch ---
    for ip in switches:
        process_switch(ip, username, password, secret, template_commands, dry_run=dry_run)

    logger.info(f"\n{'='*60}")
    logger.info("All switches processed.")
    logger.info(f"Log saved to: {log_file}")


if __name__ == "__main__":
    main()