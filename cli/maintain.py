import argparse
import os
import sys
import subprocess
import shutil
import logging
import tempfile
from pathlib import Path
import urllib.request
from rich.console import Console
from rich.markdown import Markdown

from typing import Any, Optional

logger = logging.getLogger("cli.maintainer")
console = Console()

def get_install_dir() -> Path:
    """Returns the installation directory where the code resides."""
    # Usually code is in ~/.wugong
    dir_path = Path.home() / ".wugong"
    if not dir_path.exists():
        # Fallback to check if it's in ~/.config/wugong (though usually that's for config)
        config_dir = Path.home() / ".config" / "wugong"
        if (config_dir / ".version").exists():
            return config_dir
    return dir_path

def handle_upgrade(args: Optional[argparse.Namespace] = None, manager: Any = None) -> None:
    """Handles the 'upgrade' command to update Wugong Email code directly in Python."""
    import questionary
    install_dir = get_install_dir()
    version_file = install_dir / ".version"
    raw_url_base = "https://raw.githubusercontent.com/kevinhuang001/wugong-email/main"
    repo_url = "https://github.com/kevinhuang001/wugong-email.git"
    
    if not install_dir.exists():
        console.print(f"[red]❌ Installation directory {install_dir} not found. Upgrade aborted.[/red]")
        return

    current_version = version_file.read_text().strip() if version_file.exists() else "Unknown"
    console.print(f"[blue]🔄 Checking for updates... (Current version: {current_version})[/blue]")
    
    try:
        # Check remote version
        with urllib.request.urlopen(f"{raw_url_base}/.version") as response:
            remote_version = response.read().decode().strip()
            
        if remote_version == current_version and not getattr(args, "force", False):
            console.print(f"[green]✅ Wugong Email is already up to date ({current_version}).[/green]")
            return
            
        console.print(f"[yellow]🔔 A new version of Wugong Email is available! (v{current_version} -> v{remote_version})[/yellow]")
        
        # Show changelog
        try:
            with urllib.request.urlopen(f"{raw_url_base}/CHANGELOG.md") as response:
                changelog_text = response.read().decode()
                lines = changelog_text.splitlines()
                relevant_lines = []
                found_latest = False
                for line in lines:
                    if line.startswith("## ["):
                        if current_version != "Unknown" and f"[{current_version}]" in line:
                            break
                        if not found_latest:
                            found_latest = True
                        elif current_version == "Unknown":
                            break
                    if found_latest:
                        relevant_lines.append(line)
                if relevant_lines:
                    console.print("\n[blue]📄 What's new:[/blue]")
                    console.print(Markdown("\n".join(relevant_lines)))
                    console.print("-" * 40 + "\n")
        except Exception:
            pass

        if not getattr(args, "yes", False):
            if not questionary.confirm("Do you want to upgrade to the latest version?").ask():
                console.print("[blue]❌ Upgrade cancelled.[/blue]")
                return

        console.print("[yellow]🚀 Upgrading...[/yellow]")
        
        # Check if git is available
        if shutil.which("git") is None:
            console.print("[red]❌ Error: 'git' is not installed. Upgrade requires git.[/red]")
            return

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Clone repo
            console.print("[blue]📡 Fetching latest source code...[/blue]")
            subprocess.run(["git", "clone", "--depth", "1", repo_url, str(temp_path)], check=True, capture_output=True)
            
            # Sync files
            console.print("[blue]📦 Syncing files...[/blue]")
            
            def ignore_files(dir_path, contents):
                ignored = []
                for item in contents:
                    if item == ".git" or item == ".venv" or item == "__pycache__":
                        ignored.append(item)
                    elif item.endswith(".db"):
                        ignored.append(item)
                    elif item == "config.toml" and (Path(dir_path) / item).parent == temp_path:
                        # Only ignore top-level config.toml to avoid overwriting user config
                        ignored.append(item)
                    elif item.startswith("upgrade.") or item.startswith("uninstall."):
                        # Ignore the old scripts as we are moving logic to Python
                        ignored.append(item)
                return ignored

            # Copy files from temp_path to install_dir
            for item in os.listdir(temp_path):
                s = temp_path / item
                d = install_dir / item
                
                if item in [".git", ".venv", "__pycache__", "config.toml"] or item.endswith(".db"):
                    continue
                if item.startswith("upgrade.") or item.startswith("uninstall."):
                    continue
                
                if s.is_dir():
                    if d.exists():
                        shutil.rmtree(d)
                    shutil.copytree(s, d, ignore=ignore_files)
                else:
                    shutil.copy2(s, d)
            
            # Update .version
            (install_dir / ".version").write_text(remote_version)
            
            # Update dependencies
            venv_python = install_dir / ".venv" / "bin" / "python"
            if os.name == 'nt':
                venv_python = install_dir / ".venv" / "Scripts" / "python.exe"
            
            if venv_python.exists():
                console.print("[blue]🐍 Updating dependencies...[/blue]")
                try:
                    # Try uv if present
                    subprocess.run([str(venv_python), "-m", "uv", "pip", "install", "-r", str(install_dir / "requirements.txt")], check=True, capture_output=True)
                except Exception:
                    # Fallback to pip
                    subprocess.run([str(venv_python), "-m", "pip", "install", "-r", str(install_dir / "requirements.txt")], check=True, capture_output=True)

        console.print(f"[green]✨ Successfully upgraded to version {remote_version}![/green]")
        
    except Exception as e:
        console.print(f"[red]❌ Upgrade failed: {e}[/red]")
        logger.error(f"Upgrade error: {e}")

def handle_uninstall(args: Optional[argparse.Namespace] = None, manager: Any = None) -> None:
    """Handles the 'uninstall' command directly in Python."""
    import questionary
    non_interactive = getattr(args, 'non_interactive', False)
    keep_data_arg = getattr(args, 'keep_data', False)

    if not non_interactive:
        if not questionary.confirm("Are you sure you want to uninstall Wugong Email? This will remove all code and configuration.").ask():
            return
        keep_data = questionary.confirm("Keep local email cache and database?").ask()
    else:
        keep_data = keep_data_arg
    
    install_dir = get_install_dir()
    config_dir = Path.home() / ".config" / "wugong"
    
    try:
        # 1. Remove Crontab entries
        console.print("[blue]⏰ Removing scheduled sync tasks from Crontab...[/blue]")
        if os.name != 'nt':
            try:
                result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
                if result.returncode == 0:
                    lines = result.stdout.splitlines()
                    new_lines = [l for l in lines if "wugong sync all" not in l]
                    if len(lines) != len(new_lines):
                        new_cron = "\n".join(new_lines) + "\n"
                        subprocess.run(["crontab", "-"], input=new_cron, text=True)
                        console.print("[green]✅ Crontab entries removed.[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠️  Could not update crontab: {e}[/yellow]")

        # 2. Remove Installation Directory
        if install_dir.exists():
            console.print(f"[blue]📁 Removing installation directory: {install_dir}...[/blue]")
            shutil.rmtree(install_dir)
            console.print("[green]✅ Installation directory removed.[/green]")
        
        # 3. Remove Configuration Directory
        if not keep_data and config_dir.exists():
            console.print(f"[blue]📁 Removing configuration directory: {config_dir}...[/blue]")
            shutil.rmtree(config_dir)
            console.print("[green]✅ Configuration directory removed.[/green]")
            
        console.print("[green]👋 Wugong Email has been uninstalled.[/green]")
        console.print(f"Note: If you added {install_dir} to your PATH, please remove it manually.")
        
    except Exception as e:
        console.print(f"[red]❌ Uninstall failed: {e}[/red]")
