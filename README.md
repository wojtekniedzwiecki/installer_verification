
## Overview  
Automates testing of `.sh` installers on Linux/macOS. Checks installer integrity, runs silent install or simulates if needed, verifies success, logs actions, and outputs JSON summary for CI.

## Requirements  
- Python 3.x  
- Installer `.sh` file accessible via local path or HTTP URL  
- Permissions to write in target install directory  

## Usage  
```bash
python ./installer_verify.py --build-url <installer_path_or_url> --app-name <AppName> --install-dir <InstallDir> [--dry-run] [--uninstall] [--log-path <LogFile>]
```

### Arguments  
- `--build-url`: Installer file path or HTTP URL  
- `--app-name`: Application label  
- `--install-dir`: Installation target directory  
- `--dry-run`: Simulate install steps only  
- `--uninstall`: Remove previous installation  
- `--log-path`: Custom log file output (optional)  

### Examples  
Install:  
```bash
python ./installer_verify.py --build-url ./installer.sh --app-name MyApp --install-dir /tmp/myapp
```

Uninstall only:  
```bash
python ./installer_verify.py --uninstall --install-dir /tmp/myapp
```

### Examples to Trigger Different Status Codes

- **Success (Exit code 0) with local file:**  
  Run a clean install with a valid local installer and install directory.  
```bash
python ./installer_verify.py --build-url ./installer.sh --app-name MyApp --install-dir /tmp/myapp
```

- **Success (Exit code 0) with HTTP URL:**  
Run a clean install with a valid HTTP URL pointing to the installer.  
```bash
python ./installer_verify.py --build-url http://example.com/installer.sh --app-name MyApp --install-dir /tmp/myapp
```

- **Download Failure (Exit code 2):**  
Provide an invalid or inaccessible build URL to simulate download failure.  
```bash
python ./installer_verify.py --build-url ./nonexistent.sh --app-name MyApp --install-dir /tmp/myapp
```

- **Install Failure (Exit code 3):**  
Use an installer that fails during execution or simulate failure by restricting permissions on install directory.  
```bash
python ./installer_verify.py --build-url ./failing_installer.sh --app-name MyApp --install-dir /root/protected_dir
```

- **Validation Failure (Exit code 4):**  
Force validation to fail by deleting the version.txt or install directory after install step but before validation.  
  - Uncomment sleep in line 102 and then run command and remove version.txt file during the sleep time (and before validation):
```bash
python ./installer_verify.py --build-url ./installer.sh --app-name MyApp --install-dir /tmp/myapp
```

- **Unexpected Exception (Exit code 9):**  
Simulate by passing causing script exceptions intentionally (e.g., invalid Python environment), for testing purpose pass --force-exception flag
```bash
python ./installer_verify.py --build-url "" --app-name MyApp --install-dir /tmp/myapp --force-exception
```


## Expected Behavior  
- Validates installer presence and size  
- Runs installer silently with environment vars; simulates if fails  
- Checks install dir and version file for validation  
- Generates detailed timestamped logs and JSON summary  
- Exit codes indicate success or specific failure types  
- Supports idempotent uninstall/install cycles for CI  

## Outputs  
- Log file named like `install_verification_YYYYMMDDTHHMMSS.log`  
- JSON summary like `<AppName>_summary_YYYYMMDDTHHMMSS.json`  
- Both provide full detail for automation use  

## Notes  
- Installer may require interactive sudo; simulation used if non-interactive fail  
- Retry logic for transient failures on download included  
- JSON summary ready for CI with status and numeric exit code  
'''
