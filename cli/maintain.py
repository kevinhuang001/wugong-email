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

from cli.render import CLIRenderer

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
    json_out = getattr(args, "json", False)
    non_interactive = getattr(args, "non_interactive", False)
    install_dir = get_install_dir()
    version_file = install_dir / ".version"
    raw_url_base = "https://raw.githubusercontent.com/kevinhuang001/wugong-email/main"
    repo_url = "https://github.com/kevinhuang001/wugong-email.git"
    
    if not install_dir.exists():
        CLIRenderer.render_message(f"Installation directory {install_dir} not found. Upgrade aborted.", type="error", json_output=json_out)
        return

    current_version = version_file.read_text().strip() if version_file.exists() else "Unknown"
    if not json_out:
        console.print(f"[blue]🔄 Checking for updates... (Current version: {current_version})[/blue]")
    
    try:
        # Check remote version
        with urllib.request.urlopen(f"{raw_url_base}/.version") as response:
            remote_version = response.read().decode().strip()
            
        if remote_version == current_version and not getattr(args, "force", False):
            CLIRenderer.render_message(f"Wugong Email is already up to date ({current_version}).", type="success", json_output=json_out, data={"current_version": current_version})
            return
            
        if not json_out:
            console.print(f"[yellow]🔔 A new version of Wugong Email is available! (v{current_version} -> v{remote_version})[/yellow]")
        
        # Show changelog
        if not json_out:
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

        if not getattr(args, "yes", False) and not non_interactive:
            if not json_out:
                console.print("\n[bold cyan]=== Wugong Upgrade ===[/bold cyan]")
            if not questionary.confirm("Do you want to upgrade to the latest version?").ask():
                if not json_out:
                    console.print("[yellow]Upgrade aborted by user.[/yellow]")
                return

        if not json_out:
            console.print("[yellow]🚀 Upgrading...[/yellow]")
        
        # Check if git is available
        if shutil.which("git") is None:
            CLIRenderer.render_message("'git' is not installed. Upgrade requires git.", type="error", json_output=json_out)
            return

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Clone repo
            if not json_out:
                console.print("[blue]📡 Fetching latest source code...[/blue]")
            subprocess.run(["git", "clone", "--depth", "1", repo_url, str(temp_path)], check=True, capture_output=True)
            
            # Sync files
            if not json_out:
                console.print("[blue]📦 Syncing files...[/blue]")
            
            def cleanup_obsolete(src_dir: Path, dst_dir: Path, root_dst: Path):
                """Recursively remove files in dst_dir that are not in src_dir, except protected ones."""
                if not dst_dir.exists():
                    return
                
                for item in os.listdir(dst_dir):
                    d_item = dst_dir / item
                    s_item = src_dir / item
                    
                    # 1. Protected items (global)
                    if item in [".git", ".venv", "__pycache__"] or item.endswith(".db"):
                        continue
                        
                    # 2. Protected items (root level only)
                    if item == "config.toml" and dst_dir == root_dst:
                        continue
                        
                    # 3. If it doesn't exist in source, delete it
                    if not s_item.exists():
                        try:
                            if d_item.is_dir():
                                shutil.rmtree(d_item)
                            else:
                                os.remove(d_item)
                        except Exception as e:
                            logger.warning(f"Could not remove obsolete {d_item}: {e}")
                    
                    # 4. If it's a directory and exists in both, recurse
                    elif d_item.is_dir() and s_item.is_dir():
                        cleanup_obsolete(s_item, d_item, root_dst)

            def ignore_files(dir_path, contents):
                ignored = []
                # dir_path is absolute, temp_path is Path object
                rel_path = Path(dir_path).relative_to(temp_path)
                
                for item in contents:
                    # Global ignores
                    if item in [".git", ".venv", "__pycache__"] or item.endswith(".db"):
                        ignored.append(item)
                        continue
                    
                    # Do not overwrite config.toml in the root directory
                    if item == "config.toml" and rel_path == Path("."):
                        ignored.append(item)
                return ignored

            try:
                # 1. Cleanup obsolete files first
                cleanup_obsolete(temp_path, install_dir, install_dir)
                
                # 2. Directly copy with overwrite (dirs_exist_ok=True)
                # This works on Windows because Python doesn't lock .py files after reading
                shutil.copytree(temp_path, install_dir, ignore=ignore_files, dirs_exist_ok=True)
                if not json_out:
                    console.print("[green]✅ Files synchronized successfully.[/green]")
            except Exception as e:
                logger.warning(f"Sync failed: {e}")
                raise e
            
            # Update .version
            (install_dir / ".version").write_text(remote_version)
            
            # Update dependencies
            venv_python = install_dir / ".venv" / "bin" / "python"
            if os.name == 'nt':
                venv_python = install_dir / ".venv" / "Scripts" / "python.exe"
            
            if venv_python.exists():
                if not json_out:
                    console.print("[blue]🐍 Updating dependencies...[/blue]")
                
                # Try to use uv if available in PATH (more reliable than python -m uv)
                uv_path = shutil.which("uv")
                try:
                    if uv_path:
                        if not json_out:
                            console.print("[blue]✨ Using uv for dependency update...[/blue]")
                        subprocess.run([uv_path, "pip", "install", "--python", str(venv_python), "-r", str(install_dir / "requirements.txt")], check=True, capture_output=True)
                    else:
                        # No fallback to pip as requested
                        error_msg = "uv not found in PATH. uv is required for dependency management."
                        if not json_out:
                            console.print(f"[red]❌ {error_msg}[/red]")
                            console.print("[yellow]Please install uv: https://github.com/astral-sh/uv[/yellow]")
                        raise Exception(error_msg)
                except subprocess.CalledProcessError as e:
                    error_msg = e.stderr.decode() if e.stderr else str(e)
                    logger.error(f"Dependency update failed: {error_msg}")
                    # If uv failed, we don't blindly fallback to pip here because the user
                    # wants to know why uv failed or stay consistent.
                    raise Exception(f"Dependency update failed: {error_msg}")

        # Upgrade success
        CLIRenderer.render_message(f"Successfully upgraded to v{remote_version}.", type="success", json_output=json_out, data={"new_version": remote_version})
        
    except Exception as e:
        CLIRenderer.render_message(f"Error during upgrade: {e}", type="error", json_output=json_out)

def handle_uninstall(args: Optional[argparse.Namespace] = None, manager: Any = None) -> None:
    """Handles the 'uninstall' command directly in Python."""
    import questionary
    json_out = getattr(args, "json", False)
    non_interactive = getattr(args, 'non_interactive', False)
    keep_data_arg = getattr(args, 'keep_data', False)

    if not getattr(args, "yes", False) and not non_interactive and not json_out:
        if not questionary.confirm("Are you sure you want to uninstall Wugong Email? This will remove all code and configuration.").ask():
            return
        keep_data = questionary.confirm("Keep local email cache and database?").ask()
    else:
        keep_data = keep_data_arg
    
    install_dir = get_install_dir()
    config_dir = Path.home() / ".config" / "wugong"
    
    try:
        # 1. Remove Crontab entries
        if not json_out:
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
                        if not json_out:
                            console.print("[green]✅ Crontab entries removed.[/green]")
            except Exception as e:
                if not json_out:
                    console.print(f"[yellow]⚠️  Could not update crontab: {e}[/yellow]")

        # 2. Remove Installation Directory
        if install_dir.exists():
            if not json_out:
                console.print(f"[blue]📁 Removing installation directory: {install_dir}...[/blue]")
            try:
                shutil.rmtree(install_dir)
                if not json_out:
                    console.print("[green]✅ Installation directory removed.[/green]")
            except Exception as e:
                if os.name == 'nt':
                    if not json_out:
                        console.print(f"[yellow]⚠️  Could not remove some files in {install_dir} (likely because they are in use).[/yellow]")
                        console.print(f"[yellow]Please remove the directory manually after the program exits.[/yellow]")
                else:
                    raise e
        
        # 3. Remove Configuration Directory
        if not keep_data and config_dir.exists():
            if not json_out:
                console.print(f"[blue]📁 Removing configuration directory: {config_dir}...[/blue]")
            shutil.rmtree(config_dir)
            if not json_out:
                console.print("[green]✅ Configuration directory removed.[/green]")
            
        CLIRenderer.render_message("Wugong Email has been uninstalled.", type="success", json_output=json_out)
        if not json_out:
            console.print(f"Note: If you added {install_dir} to your PATH, please remove it manually.")
        
    except Exception as e:
        CLIRenderer.render_message(f"Uninstall failed: {e}", type="error", json_output=json_out)

