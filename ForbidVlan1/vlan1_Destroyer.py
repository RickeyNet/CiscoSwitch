#!/usr/bin/env python3
"""
VLAN 1 Remediation Script
--------------------------
Connects to Cisco Catalyst switches listed in switches.txt,
inventories all interfaces, identifies access ports assigned to VLAN 1,
and applies a replacement interface configuration from interface_template.txt.

Requirements:
    pip install netmiko

Files needed:
    switches.txt             - One switch IP per line
    interface_template.txt   - Interface config commands (one per line, no "interface" line)
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
TEMPLATE_FILE = "interface_template.txt"
LOG_DIR = "logs"

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
os.makedirs(LOG_DIR, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(LOG_DIR, f"vlan1_remediation_{timestamp}.log")

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
    """Read the interface template config commands from a text file."""
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


def get_vlan1_access_ports(connection) -> list[str]:
    """
    Parse 'show interfaces switchport' to find access ports on VLAN 1.
    Returns a list of interface names that match.
    """
    output = connection.send_command("show interfaces switchport", delay_factor=2)

    vlan1_ports = []
    current_interface = None
    is_access = False
    access_vlan = None

    for line in output.splitlines():
        # Detect interface header: "Name: Gi1/0/1"
        if line.startswith("Name:"):
            # Save previous interface if it matched
            if current_interface and is_access and access_vlan == "1":
                vlan1_ports.append(current_interface)

            current_interface = line.split("Name:")[-1].strip()
            is_access = False
            access_vlan = None

        # Detect operational mode
        elif "Administrative Mode:" in line:
            mode = line.split("Administrative Mode:")[-1].strip().lower()
            is_access = mode == "static access"

        # Detect access VLAN
        elif "Access Mode VLAN:" in line:
            # Format: "Access Mode VLAN: 1 (default)"
            vlan_part = line.split("Access Mode VLAN:")[-1].strip()
            access_vlan = vlan_part.split()[0] if vlan_part else None

    # Don't forget the last interface
    if current_interface and is_access and access_vlan == "1":
        vlan1_ports.append(current_interface)

    return vlan1_ports


def apply_template_to_ports(
    connection, ports: list[str], template_commands: list[str], dry_run: bool = False
) -> dict:
    """
    Apply the template configuration to each port.
    Returns a dict of {interface: output}.
    """
    results = {}
    for port in ports:
        config_set = [f"interface {port}"] + template_commands

        if dry_run:
            logger.info(f"  [DRY-RUN] Would apply to {port}:")
            for cmd in config_set:
                logger.info(f"    {cmd}")
            results[port] = "DRY-RUN"
        else:
            logger.info(f"  Applying template to {port} ...")
            output = connection.send_config_set(config_set)
            results[port] = output
            logger.debug(output)

    return results


def process_switch(
    ip: str,
    username: str,
    password: str,
    secret: str,
    template_commands: list[str],
    dry_run: bool = False,
):
    """Connect to a single switch, find VLAN 1 access ports, and remediate."""
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

        # --- Inventory ---
        logger.info("  Gathering interface inventory ...")
        vlan1_ports = get_vlan1_access_ports(conn)

        if not vlan1_ports:
            logger.info("  No access ports on VLAN 1 found. Nothing to do.")
            return

        logger.info(
            f"  Found {len(vlan1_ports)} access port(s) on VLAN 1: "
            f"{', '.join(vlan1_ports)}"
        )

        # --- Remediate ---
        results = apply_template_to_ports(
            conn, vlan1_ports, template_commands, dry_run=dry_run
        )

        # Save running config (unless dry run)
        if not dry_run and results:
            logger.info("  Saving running config to startup ...")
            conn.save_config()

        logger.info(f"  Finished processing {hostname} ({ip}).")

    finally:
        conn.disconnect()


def main():
    print(
        """
╔══════════════════════════════════════════════════╗
║        VLAN 1 Access Port Remediation Tool       ║
╚══════════════════════════════════════════════════╝
"""
    )

    # --- Load files ---
    switches = load_switches(SWITCHES_FILE)
    template_commands = load_template(TEMPLATE_FILE)

    print("\nTemplate commands that will be applied to each VLAN 1 access port:")
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