# IOS-XE Upgrade Script - Enhancement Backlog

Potential improvements identified during code review. Items are grouped by category and roughly prioritized within each section.

---

## Reliability & Robustness

### [x] ~~Retry Logic for Transient Failures~~
~~If an SCP transfer fails mid-stream or SSH drops unexpectedly, the script currently reconnects to verify but does not retry the failed operation itself. Adding configurable retry attempts (e.g., `--retries 2`) with exponential backoff would handle flaky connections gracefully.~~

**Implemented:** Added `--retries N` flag (default: 0). SCP transfers retry with exponential backoff (30s, 60s, 120s... capped at 300s). SSH connections also retry on transient failures (timeouts, socket errors, connection refused).

### [x] ~~Delay/Throttle Between Switches~~
~~Processing all switches back-to-back with no configurable delay could overwhelm shared infrastructure (RADIUS servers, SCP source disk I/O, network bandwidth). A `--delay` flag (e.g., `--delay 30` for 30 seconds between switches) would prevent resource contention.~~

**Implemented:** Added `--delay N` flag (default: 0). Inserts a wait between each switch in sequential mode and between sequential activate phases in parallel mode.

### [x] ~~Flash Space Cleanup Intelligence~~
~~`install remove inactive` is run during prestage, but there's no check afterward on whether the cleanup actually freed enough space for the new image. If flash is still full after cleanup, the transfer will fail. The script should re-check free space after cleanup and warn early.~~

**Implemented:** After `install remove inactive`, prestage re-checks flash free space against the image size (when `--image` is provided) and warns if cleanup didn't free enough space.

---

## Operational Improvements

### [x] ~~Parallel Execution for Prestage/Transfer~~ 
~~The main script (`iosxe_upgrade.py`) processes switches sequentially. For large deployments, parallel prestage and transfer using `ThreadPoolExecutor` (like the API variant already does for prestage) would save significant time. Activate should remain sequential for safety.~~

**Implemented:** Added `--parallel N` flag (default: 1). When `N > 1`, prestage and transfer run across switches concurrently using `ThreadPoolExecutor`. Activate always runs sequentially for safety. Requires `--no-confirm` in parallel mode.

### [x] ~~Config File Support~~
~~Everything is via CLI arguments currently. A YAML or JSON config file for common settings (timeouts, image paths, credential file paths, parallel workers, default flags) would reduce long command lines and support repeatable deployments.~~

**Implemented:** Added `--config FILE` flag that loads settings from a YAML (`.yml`/`.yaml`, requires PyYAML) or JSON (`.json`) config file. All CLI arguments can be specified as config keys (using underscores). CLI arguments always override config file values. Unknown keys are rejected with an error. Example:
```yaml
# upgrade_config.yml
hosts: switches.txt
image: cat9k_iosxe.17.15.05.SPA.bin
full: true
timeout: 900
parallel: 10
no_confirm: true
retries: 2
verify_upgrade: true
auto_rollback: true
output: results.json
```

### [x] ~~Structured Result Output~~
~~The script only prints results to console and log files. Outputting final results as JSON or CSV (`--output results.json`) would enable integration with monitoring, ticketing systems (ServiceNow), or dashboards.~~

**Implemented:** Added `--output FILE` flag. Auto-detects format by extension (`.json` or `.csv`). Each record includes switch hostname, overall success, per-phase results (health_check, prestage, transfer, activate, verify), image name, and timestamp.

### [ ] Backup Format Options
Config backups are raw text files. Adding a structured format option (JSON via RESTCONF, or at least consistent naming with version info in the filename) would make automated comparison and diff easier.

### [ ] Version Comparison / Skip Already Upgraded
Pre-check that compares the running version vs target image version and skips switches already on the target version. This makes re-runs idempotent and safe to schedule without worrying about unnecessary reloads.

### [ ] Dry-Run Mode
A `--dry-run` flag that connects to each switch, checks versions, validates flash space, runs health checks, and reports what *would* happen without making any changes. Useful for upgrade planning and change management documentation.

---

## Code Quality

### [ ] Shared Module for Common Logic
`iosxe_upgrade.py` and `ios_upgrade_api.py` share significant overlapping code (credential management, SCP transfer, install activation, logging setup). Extracting shared logic into a common module (e.g., `upgrade_common.py`) would reduce duplication and maintenance burden.

### [ ] More Specific Exception Handling
Several `except Exception` blocks catch everything generically. More targeted exceptions (e.g., `NetmikoAuthenticationException`, `ConnectionRefusedError`, `FileNotFoundError`) would prevent silently swallowing unexpected errors and make debugging easier.

### [ ] Configurable Timeouts
Values like the 600s command timeout and 900s install timeout are embedded in the code or only partially exposed via `--timeout`. Making all timeouts individually configurable (transfer timeout, install timeout, MD5 verification timeout) via CLI args or a config file would help for different switch models and network conditions.

---

## Advanced Features

### [ ] ISSU / Rolling Upgrade Support
For stacked switches or StackWise Virtual pairs on supported platforms, In-Service Software Upgrade (ISSU) allows zero-downtime upgrades. This would require detecting whether the platform/version supports ISSU and using `install add file <image> activate issu commit` instead.

### [ ] Notification/Webhook Integration
Send notifications on upgrade completion or failure to Slack, Teams, email, or a generic webhook. Useful for maintenance windows where multiple people need status updates.

### [ ] Pre/Post Upgrade Script Hooks
Allow users to specify custom scripts or commands to run before and after each phase. For example, disabling monitoring alerts before activate, or running custom validation after reboot.
