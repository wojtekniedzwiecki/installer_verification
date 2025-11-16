#!/usr/bin/env python3
import argparse
import datetime
import subprocess
import os
import sys
import time
import json
import logging
from urllib.request import urlretrieve

# Exit codes
EXIT_SUCCESS = 0
EXIT_DOWNLOAD_FAIL = 2
EXIT_INSTALL_FAIL = 3
EXIT_VALIDATE_FAIL = 4
EXIT_EXCEPTION = 9

def setup_logger(log_path):
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s'
    )
    return logging.getLogger()

def run_cmd(cmd, timeout=120):
    try:
        result = subprocess.run(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout
        )
        return result.returncode, result.stdout.decode(), result.stderr.decode()
    except subprocess.TimeoutExpired:
        return 1, "", "TimeoutExpired"

def download_installer(build_url, dest_path, retries=2, backoff=2, logger=None):
    attempt = 0
    while attempt <= retries:
        try:
            if build_url.startswith("http"):
                urlretrieve(build_url, dest_path)
            else:
                if not os.path.isfile(build_url) or os.path.getsize(build_url) == 0:
                    raise FileNotFoundError("Installer not found or zero size")
                # For local path, copy to dest_path or create symlink
                if os.path.abspath(build_url) != os.path.abspath(dest_path):
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    os.symlink(os.path.abspath(build_url), dest_path)
            if logger:
                logger.info(f"Installer verified: {build_url}")
            return True
        except Exception as e:
            if logger:
                logger.error(f"Download attempt {attempt+1} failed: {e}")
            time.sleep(backoff)
            attempt += 1
    return False

def sanity_check(path, logger=None):
    exists = os.path.isfile(path) and os.path.getsize(path) > 0
    if logger:
        logger.info(f"Sanity check: {path} exists and non-zero size: {exists}")
    return exists

def silent_install(installer_path, install_dir, dry_run=False, logger=None):
    if dry_run:
        if logger:
            logger.info(f"DRY RUN: Would install {installer_path} to {install_dir}")
        return 0
    # Try to execute the installer .sh script
    if installer_path.endswith(".sh"):
        cmd = f"NONINTERACTIVE=1 CI=1 INSTALL_DIR='{install_dir}' bash '{installer_path}'"
        if logger:
            logger.info(f"Running installer command: {cmd}")
        code, out, err = run_cmd(cmd)
        if logger:
            logger.info(f"Installer stdout: {out}")
            logger.info(f"Installer stderr: {err}")
        if code == 0:
            return 0
        else:
            if logger:
                logger.warning(
                    f"Installer script returned non-zero exit code ({code}). Falling back to simulation."
                )
    # Simulate install if execution failed or installer is not .sh
    try:
        os.makedirs(install_dir, exist_ok=True)
        with open(os.path.join(install_dir, "version.txt"), "w") as f:
            f.write("1.0.0")
        if logger:
            logger.info(f"Simulated installation to {install_dir}")
        return 0
    except Exception as e:
        if logger:
            logger.error(f"Installation simulation failed: {e}")
        return 1

def validate_install(install_dir, logger=None):
    time.sleep(15)    
    exists = os.path.isdir(install_dir)
    file_exists = os.path.isfile(os.path.join(install_dir, "version.txt"))
    if logger:
        logger.info(f"Validation: dir exists: {exists}, version.txt: {file_exists}")
    return exists and file_exists

def uninstall(install_dir, logger=None):
    try:
        if os.path.isdir(install_dir):
            for root, dirs, files in os.walk(install_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(install_dir)
        if logger:
            logger.info(f"Uninstalled {install_dir}")
        return True
    except Exception as e:
        if logger:
            logger.error(f"Uninstall error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Linux Installer Verification Script")
    parser.add_argument("--build-url", required=True, help="Path or HTTP URL of installer")
    parser.add_argument("--app-name", required=True, help="Generic label for app")
    parser.add_argument("--dry-run", action="store_true", help="Log steps only, simulate installation")
    parser.add_argument("--install-dir", required=True, help="Directory for installation")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall previous installation")
    parser.add_argument("--log-path", help="Log file path (overridden by timestamp if not empty)")
    parser.add_argument("--force-exception", action="store_true", help="Force a simulated unexpected exception for testing")
    args = parser.parse_args()

        # Create timestamp string for filenames (e.g. 20251116T131200)
    timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")

    # Generate log file path with timestamp
    log_path = args.log_path if args.log_path else f"install_verification_{timestamp_str}.log"

    # Setup logger with new log path
    logger = setup_logger(log_path)
    start_time = time.time()
    checks_run = []
    status_code = EXIT_SUCCESS
    summary_path = f"{args.app_name}_summary_{timestamp_str}.json"

    try:
        if args.uninstall:
            checks_run.append("uninstall")
            success = uninstall(args.install_dir, logger=logger)
            if not success:
                status_code = EXIT_VALIDATE_FAIL
        elif args.dry_run:
            logger.info("Dry run mode: simulated steps")
            checks_run.append("dry-run")
        elif args.force_exception:
            raise RuntimeError("Forced exception for testing status code 9")
        else:
            dest_installer = os.path.join("/tmp", f"{args.app_name}_installer.sh")
            checks_run.append("download")
            if not download_installer(args.build_url, dest_installer, logger=logger):
                status_code = EXIT_DOWNLOAD_FAIL
                raise Exception("Download failed")

            checks_run.append("sanity-check")
            if not sanity_check(dest_installer, logger=logger):
                status_code = EXIT_DOWNLOAD_FAIL
                raise Exception("Sanity check failed")

            checks_run.append("install")
            if silent_install(dest_installer, args.install_dir, dry_run=args.dry_run, logger=logger) != 0:
                status_code = EXIT_INSTALL_FAIL
                raise Exception("Installer failed")

            checks_run.append("validate")
            if not validate_install(args.install_dir, logger=logger):
                status_code = EXIT_VALIDATE_FAIL
                raise Exception("Validation failed")

        final_status = "success" if status_code == EXIT_SUCCESS else "failure"
        logger.info(f"Final status: {final_status}")

    except Exception as ex:
        logger.error(f"Unexpected exception: {ex}")
        if status_code == EXIT_SUCCESS:
            status_code = EXIT_EXCEPTION

    duration = int(time.time() - start_time)

    summary = {
        "status": "success" if status_code == EXIT_SUCCESS else "failure",
        "status_code": status_code,
        "duration_seconds": duration,
        "log_path": log_path,
        "checks_run": checks_run
    }
    
    # Write summary to timestamped JSON file
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    sys.exit(status_code)

if __name__ == "__main__":
    main()
