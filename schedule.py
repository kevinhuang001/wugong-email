import os
import platform
import subprocess
from pathlib import Path

def setup_scheduling(interval_minutes: int, encryption_password: str | None = None) -> bool:
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
                        print("✅ Auto-sync disabled (Task Scheduler entry removed).")
                    except subprocess.CalledProcessError:
                        pass
                    return True

                env_prefix = f'set WUGONG_PASSWORD={encryption_password} && ' if encryption_password else ""
                task_command = f'cmd /c "{env_prefix}{wugong_bat} sync all >> \"{log_file}\" 2>&1"'

                cmd = ["schtasks", "/create", "/sc", "minute", "/mo", str(interval_minutes), "/tn", "WugongSync", "/tr", task_command, "/f"]
                subprocess.run(cmd, check=True, capture_output=True)
                print(f"✅ Scheduled sync every {interval_minutes} minutes via Task Scheduler.")
                if encryption_password:
                    print("ℹ️  WUGONG_PASSWORD environment variable included in the scheduled task.")
                print(f"ℹ️  Logs will be saved to: {log_file}")

            case _:
                # Unix-like (macOS/Linux) Cron
                try:
                    current_cron = subprocess.check_output(["crontab", "-l"], stderr=subprocess.STDOUT).decode()
                except subprocess.CalledProcessError:
                    current_cron = ""

                lines = [line for line in current_cron.splitlines() if "wugong sync all" not in line]

                if interval_minutes > 0:
                    env_prefix = f"WUGONG_PASSWORD={encryption_password} " if encryption_password else ""
                    cron_job = f"*/{interval_minutes} * * * * {env_prefix}{wugong_exe} sync all >> {log_file} 2>&1"
                    lines.append(cron_job)
                    print(f"✅ Scheduled sync every {interval_minutes} minutes via Crontab.")
                    if encryption_password:
                        print("ℹ️  WUGONG_PASSWORD environment variable included in the crontab job.")
                    print(f"ℹ️  Logs will be saved to: {log_file}")
                else:
                    print("✅ Auto-sync disabled (Crontab entry removed).")

                new_cron = "\n".join(lines) + "\n"
                process = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                _, stderr = process.communicate(input=new_cron.encode())

                if process.returncode != 0:
                    print(f"❌ Error setting up crontab: {stderr.decode()}")
                    return False
        return True
    except Exception as e:
        print(f"❌ Failed to setup scheduling: {e}")
        return False
