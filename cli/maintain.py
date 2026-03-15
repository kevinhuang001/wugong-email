import argparse
import os
import sys
import subprocess
import shutil
import logging
from pathlib import Path
import urllib.request
from rich.console import Console

from typing import Any, Optional

logger = logging.getLogger("cli.maintainer")
console = Console()

def get_install_dir() -> Path:
    """Returns the installation directory, checking for ~/.config/wugong first."""
    new_dir = Path.home() / ".config" / "wugong"
    legacy_dir = Path.home() / ".wugong"
    if not new_dir.exists() and legacy_dir.exists():
        return legacy_dir
    return new_dir

def handle_upgrade(args: Optional[argparse.Namespace] = None, manager: Any = None) -> None:
    """Handles the 'upgrade' command to update Wugong Email code."""
    install_dir = get_install_dir()
    version_file = install_dir / ".version"
    raw_url_base = "https://raw.githubusercontent.com/kevinhuang001/wugong-email/main"
    
    current_version = version_file.read_text().strip() if version_file.exists() else "Unknown"
    console.print(f"[blue]🔄 Checking for updates... (Current version: {current_version})[/blue]")
    
    try:
        # Check remote version
        with urllib.request.urlopen(f"{raw_url_base}/.version") as response:
            remote_version = response.read().decode().strip()
            
        if remote_version == current_version and not getattr(args, "force", False):
            console.print(f"[green]✅ Wugong Email is already up to date ({current_version}).[/green]")
            return
            
        console.print(f"[yellow]🚀 Upgrading to version {remote_version}...[/yellow]")
        
        # Download upgrade script
        script_ext = "sh" if os.name != 'nt' else "ps1"
        upgrade_script_url = f"{raw_url_base}/upgrade.{script_ext}"
        upgrade_script_path = install_dir / f"upgrade_temp.{script_ext}"
        
        with urllib.request.urlopen(upgrade_script_url) as response, open(upgrade_script_path, "wb") as out_file:
            out_file.write(response.read())
            
        # Run upgrade script
        if os.name != 'nt':
            os.chmod(upgrade_script_path, 0o755)
            subprocess.run(["bash", str(upgrade_script_path)], check=True)
        else:
            subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(upgrade_script_path)], check=True)
            
        console.print(f"[green]✨ Successfully upgraded to version {remote_version}![/green]")
        
    except Exception as e:
        console.print(f"[red]❌ Upgrade failed: {e}[/red]")
        logger.error(f"Upgrade error: {e}")

def handle_uninstall(args: Optional[argparse.Namespace] = None, manager: Any = None) -> None:
    """Handles the 'uninstall' command."""
    import questionary
    non_interactive = getattr(args, 'non_interactive', False)
    keep_data_arg = getattr(args, 'keep_data', False)

    if not non_interactive:
        if not questionary.confirm("Are you sure you want to uninstall Wugong Email? This will remove all code and configuration (but keep the data folder if you choose).").ask():
            return
            
        keep_data = questionary.confirm("Keep local email cache and database?").ask()
    else:
        keep_data = keep_data_arg
    
    install_dir = get_install_dir()
    script_ext = "sh" if os.name != 'nt' else "ps1"
    uninstall_script = install_dir / f"uninstall.{script_ext}"
    
    if not uninstall_script.exists():
        console.print(f"[red]❌ Uninstall script not found. Please remove {install_dir} manually.[/red]")
        return
        
    try:
        cmd = ["bash", str(uninstall_script)] if os.name != 'nt' else ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(uninstall_script)]
        if keep_data:
            cmd.append("--keep-data")
            
        subprocess.run(cmd, check=True)
        console.print("[green]👋 Wugong Email has been uninstalled.[/green]")
    except Exception as e:
        console.print(f"[red]❌ Uninstall failed: {e}[/red]")
