import os
import platform
import subprocess
from pathlib import Path
from logger import setup_logger

logger = setup_logger("schedule")

def setup_scheduling(interval_minutes: int, encryption_password: str | None = None, json_output: bool = False) -> bool:
    """Sets up a periodic sync task using Cron (Unix) or Task Scheduler (Windows)."""
    home = Path.home()
    wugong_dir = home / ".wugong"
    wugong_dir.mkdir(parents=True, exist_ok=True)
    
    # Locate the executable
    wugong_exe = next((p for p in [wugong_dir / "wugong", Path.cwd() / "wugong"] if p.exists()), Path("wugong"))
    log_file = wugong_dir / "sync.log"

    try:
        match platform.system():
            case "Windows":
                # Windows Task Scheduler
                wugong_bat = next((p for p in [wugong_exe.with_suffix(".bat"), Path("wugong.bat")] if p.exists()), Path("wugong.bat"))

                if interval_minutes <= 0:
                    try:
                        subprocess.run(["schtasks", "/delete", "/tn", "WugongSync", "/f"], check=True, capture_output=True)
                        logger.info("Auto-sync disabled (Task Scheduler entry removed).")
                    except subprocess.CalledProcessError:
                        pass
                    return True

                env_prefix = f'set WUGONG_PASSWORD={encryption_password} && ' if encryption_password else ""
                # Windows command: echo current date and time, then sync
                task_command = f'cmd /c "{env_prefix}echo [%date% %time%] Syncing... >> \"{log_file}\" 2>&1 && {wugong_bat} sync -a all >> \"{log_file}\" 2>&1"'

                cmd = ["schtasks", "/create", "/sc", "minute", "/mo", str(interval_minutes), "/tn", "WugongSync", "/tr", task_command, "/f"]
                subprocess.run(cmd, check=True, capture_output=True)
                logger.info(f"Scheduled sync every {interval_minutes} minutes via Task Scheduler.")
                if encryption_password:
                    logger.info("WUGONG_PASSWORD environment variable included in the scheduled task.")
                logger.info(f"Logs will be saved to: {log_file}")

            case _:
                # Unix-like (macOS/Linux) Cron
                try:
                    current_cron = subprocess.check_output(["crontab", "-l"], stderr=subprocess.STDOUT).decode()
                except subprocess.CalledProcessError:
                    current_cron = ""

                lines = [line for line in current_cron.splitlines() if "wugong sync" not in line]

                if interval_minutes > 0:
                    env_prefix = f"WUGONG_PASSWORD={encryption_password} " if encryption_password else ""
                    # Unix command: echo current date, then sync
                    cron_job = f"*/{interval_minutes} * * * * {env_prefix}echo \"[`date`] Syncing...\" >> {log_file} 2>&1 && {wugong_exe} sync -a all >> {log_file} 2>&1"
                    lines.append(cron_job)
                    logger.info(f"Scheduled sync every {interval_minutes} minutes via Crontab.")
                    if encryption_password:
                        logger.info("WUGONG_PASSWORD environment variable included in the crontab job.")
                    logger.info(f"Logs will be saved to: {log_file}")
                else:
                    logger.info("Auto-sync disabled (Crontab entry removed).")

                new_cron = "\n".join(lines) + "\n"
                process = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                _, stderr = process.communicate(input=new_cron.encode())

                if process.returncode != 0:
                    logger.error(f"Error setting up crontab: {stderr.decode()}")
                    return False
        return True
    except Exception as e:
        logger.error(f"Failed to setup scheduling: {e}")
        return False
