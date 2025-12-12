#!/usr/bin/env python3
"""
Threaded Cisco IOS-XE Save Config Script

- Connects to multiple switches in parallel
- Runs: write memory
- Logs to a file (optional)

Requirements:
    pip install netmiko


# Single switch
python iosxe_save_config_threaded.py --host 192.168.0.1

# List of switches, 20 concurrent workers
python iosxe_save_config_threaded.py --hosts switches.txt --workers 20 --env-creds

"""

from __future__ import annotations

import argparse
import getpass
import logging
from pathlib import Path
from datetime import datetime
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Save running-config to startup-config on Cisco switches (threaded)"
    )

    # Target switches
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--host", help="Single switch IP or hostname")
    group.add_argument("--hosts", help="Text file with one IP/hostname per line")

    # Auth
    parser.add_argument("-u", "--username", help="SSH username")
    parser.add_argument("-p", "--password", help="SSH password")
    parser.add_argument("--enable", help="Enable password (defaults to password)")
    parser.add_argument(
        "--env-creds",
        action="store_true",
        help="Use SWITCH_USER / SWITCH_PASS / SWITCH_ENABLE environment vars",
    )

    # Connection
    parser.add_argument("--port", type=int, default=22, help="SSH port (default: 22)")
    parser.add_argument("--timeout", type=int, default=30, help="SSH timeout (default: 30)")
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Number of parallel threads (default: 10)",
    )

    # Logging
    parser.add_argument("--log-dir", default="./logs", help="Directory for log files")
    parser.add_argument("--no-log", action="store_true", help="Disable logging to file")

    return parser.parse_args()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_switches(args) -> list[str]:
    """Return list of switches from --host or --hosts (txt file)."""
    if args.host:
        return [args.host]

    path = Path(args.hosts)
    if not path.exists():
        print(f"Error: hosts file not found: {path}")
        sys.exit(1)

    switches: list[str] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        switches.append(line.split(",")[0].strip())

    if not switches:
        print("Error: no switches found in hosts file")
        sys.exit(1)

    return switches


def setup_logging(args) -> Path | None:
    """Set up logging to a file if not disabled."""
    if args.no_log:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        return None

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"save_config_{ts}.log"

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
    )

    return log_file


def get_credentials(args) -> dict[str, str]:
    """Determine username/password/enable."""
    # Env mode
    if args.env_creds:
        user = os.environ.get("SWITCH_USER")
        pw = os.environ.get("SWITCH_PASS")
        en = os.environ.get("SWITCH_ENABLE") or pw
        if not user or not pw:
            print("Error: SWITCH_USER and SWITCH_PASS env vars are required with --env-creds")
            sys.exit(1)
        return {"username": user, "password": pw, "enable": en} # pyright: ignore[reportReturnType]

    # CLI + prompt fallback
    username = args.username or input("Username: ")
    password = args.password or getpass.getpass("Password: ")
    enable = args.enable or password
    return {"username": username, "password": password, "enable": enable}


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------

def save_config_on_switch(
    switch: str,
    creds: dict[str, str],
    port: int,
    timeout: int,
) -> tuple[str, str, str]:
    """
    Connect to switch and run 'write memory'.

    Returns (switch, status, error_message)
    """
    logger = logging.getLogger("save_config")
    logger.info(f"Connecting to {switch}")

    device = {
        "device_type": "cisco_xe",
        "host": switch,
        "username": creds["username"],
        "password": creds["password"],
        "secret": creds.get("enable", creds["password"]),
        "port": port,
        "timeout": timeout,
        "auth_timeout": timeout,
    }

    try:
        conn = ConnectHandler(**device)
        conn.enable()
        logger.info(f"Connected to {switch}")

        output = conn.send_command("write memory", read_timeout=60)
        logger.debug(f"{switch} write memory output:\n{output}")

        if "OK" in output or "copied" in output.lower(): # pyright: ignore[reportAttributeAccessIssue]
            logger.info(f"{switch}: configuration saved successfully")
            status, error = "Success", ""
        else:
            logger.warning(f"{switch}: unexpected output: {output}")
            status, error = "Warning", f"Unexpected output: {output[:100]}" # pyright: ignore[reportArgumentType]

        conn.disconnect()
        return switch, status, error

    except NetmikoAuthenticationException as e:
        logger.error(f"{switch}: authentication failed: {e}")
        return switch, "Auth Failed", str(e)

    except NetmikoTimeoutException as e:
        logger.error(f"{switch}: timeout: {e}")
        return switch, "Timeout", str(e)

    except Exception as e:
        logger.error(f"{switch}: error: {e}")
        return switch, "Error", str(e)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()
    log_file = setup_logging(args)
    logger = logging.getLogger("save_config")

    switches = get_switches(args)
    creds = get_credentials(args)

    print(f"\nSaving configuration on {len(switches)} switch(es)...")
    if log_file:
        print(f"Logging to: {log_file}")
    print(f"Using up to {args.workers} parallel connections.\n")

    logger.info(f"Starting save config for {len(switches)} switches with {args.workers} workers")

    results: list[tuple[str, str, str]] = []

    # Thread pool to run multiple SSH sessions at once
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_switch = {
            executor.submit(
                save_config_on_switch,
                sw,
                creds,
                args.port,
                args.timeout,
            ): sw
            for sw in switches
        }

        total = len(future_to_switch)
        for i, future in enumerate(as_completed(future_to_switch), 1):
            sw = future_to_switch[future]
            try:
                sw_name, status, error = future.result()
            except Exception as e:
                # Catch any unexpected exception from the thread
                sw_name, status, error = sw, "Error", str(e)
                logger.error(f"{sw}: unhandled exception in worker: {e}")

            results.append((sw_name, status, error))

            # Progress line; order is "as completed", not original order
            if status == "Success":
                print(f"  [{i}/{total}] {sw_name}... ✓ Saved")
            else:
                print(f"  [{i}/{total}] {sw_name}... ✗ {status}")

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)

    success = sum(1 for _, s, _ in results if s == "Success")
    failed = len(results) - success

    print(f"\nTotal: {len(results)}  |  Success: {success}  |  Failed: {failed}")

    if failed:
        print("\nFailed switches:")
        for sw, status, error in results:
            if status != "Success":
                print(f"  ✗ {sw}: {status} - {error}")

    if log_file:
        print(f"\nLog saved to: {log_file}")
    logger.info("Save config complete")


if __name__ == "__main__":
    main()
