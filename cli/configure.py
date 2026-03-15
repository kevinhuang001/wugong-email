import argparse
import os
import logging
import base64
import questionary
from rich.console import Console

import config
from mail import MailManager
from crypto_utils import generate_salt, encrypt_data
from schedule import setup_scheduling

logger = logging.getLogger("cli.configure")
console = Console()

def configure_wizard(
    args: argparse.Namespace | None = None,
    console_log_level: str | None = None,
    file_log_level: str | None = None,
    sync_interval: int | None = None,
    non_interactive: bool = False
) -> bool:
    """Allows modifying the sync interval and displays a message about password changes."""
    config_path = config.get_config_path()
    current_config = config.load_config(config_path)
    
    try:
        if non_interactive:
            # === Non-Interactive Flow ===
            if not current_config.get("general", {}).get("salt"):
                return False

            # Logging Setup
            current_console_level = current_config.get("general", {}).get("console_log_level", "WARNING")
            current_file_level = current_config.get("general", {}).get("file_log_level", "DEBUG")
            
            console_log_level = console_log_level or current_console_level
            file_log_level = file_log_level or current_file_level

            # Sync Interval
            current_interval = current_config.get("general", {}).get("sync_interval", 10)
            interval = sync_interval if sync_interval is not None else current_interval

            if interval != current_interval or console_log_level != current_console_level or file_log_level != current_file_level:
                encryption_password = config.get_verified_password(current_config, args)

                setup_scheduling(interval, encryption_password)
                general = current_config.setdefault("general", {})
                general["sync_interval"] = interval
                general["console_log_level"] = console_log_level
                general["file_log_level"] = file_log_level
                config.save_config(current_config, config_path)
            
            return True

        # === Interactive Flow ===
        print("\n=== Wugong Email Configuration ===")

        if not current_config.get("general", {}).get("salt"):
            print("\n❌ Wugong is not initialized yet. Please run 'wugong init' first.")
            return False

        print("\nℹ️  Encryption password cannot be modified.")
        print("⚠️  If you need to change your encryption password, please uninstall and reinstall Wugong.")

        # Logging Setup
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        current_console_level = current_config.get("general", {}).get("console_log_level", "WARNING")
        current_file_level = current_config.get("general", {}).get("file_log_level", "DEBUG")

        if console_log_level is None:
            if (console_log_level := questionary.select(
                f"Select console log level (current: {current_console_level}):",
                choices=log_levels,
                default=current_console_level
            ).ask()) is None:
                raise KeyboardInterrupt

        if file_log_level is None:
            if (file_log_level := questionary.select(
                f"Select file log level (current: {current_file_level}):",
                choices=log_levels,
                default=current_file_level
            ).ask()) is None:
                raise KeyboardInterrupt

        # Sync Interval & Scheduling
        current_interval = current_config.get("general", {}).get("sync_interval", 10)
        if sync_interval is None:
            if (sync_interval_str := questionary.text(
                f"Sync interval in minutes (current: {current_interval}. Enter 0 to disable auto-sync):",
                default=str(current_interval)
            ).ask()) is None:
                raise KeyboardInterrupt
            else:
                interval = int(sync_interval_str) if sync_interval_str.isdigit() else current_interval
        else:
            interval = sync_interval

        if interval != current_interval or console_log_level != current_console_level or file_log_level != current_file_level:
            encryption_password = config.get_verified_password(current_config, args, prompt_text="Enter your encryption password to update the scheduled task:")

            setup_scheduling(interval, encryption_password)
            general = current_config.setdefault("general", {})
            general["sync_interval"] = interval
            general["console_log_level"] = console_log_level
            general["file_log_level"] = file_log_level
            
            config.save_config(current_config, config_path)
            print(f"\n✅ Configuration updated: interval={interval}m, console={console_log_level}, file={file_log_level}.")
        else:
            print("\nNo changes made to configuration.")

        return True
    except KeyboardInterrupt:
        print("\nConfiguration cancelled.")
        return False
    except Exception as e:
        print(f"\n❌ Error during configuration: {e}")
        return False

def init_wizard(
    args: argparse.Namespace | None = None,
    encrypt_creds: bool | None = None,
    encrypt_emails: bool | None = None,
    console_log_level: str | None = None,
    file_log_level: str | None = None,
    sync_interval: int | None = None,
    non_interactive: bool = False
) -> tuple[bool, str | None]:
    """Initializes the configuration, sets up encryption, and schedules periodic sync."""
    config_path = config.get_config_path()
    current_config = config.load_config(config_path)

    try:
        if non_interactive:
            # === Non-Interactive Flow ===
            if current_config.get("general", {}).get("salt"):
                raise ValueError("Wugong is already initialized. Please use 'wugong configure' to modify settings or delete the config file to reset.")

            # 1. Encryption Setup
            encrypt_creds = encrypt_creds if encrypt_creds is not None else True
            encrypt_emails = encrypt_emails if encrypt_emails is not None else True
            encrypt_enabled = encrypt_creds or encrypt_emails

            salt_val = ""
            canary = ""
            encryption_password = None

            if encrypt_enabled:
                encryption_password = config.get_encryption_password(args)
                if not encryption_password:
                    raise ValueError("Encryption password must be provided via --encryption-password or WUGONG_PASSWORD to set up encryption in non-interactive mode.")
                
                salt_raw = generate_salt()
                salt_val = base64.b64encode(salt_raw).decode()
                canary = encrypt_data("wugong", encryption_password, salt_raw)

            # 2. Logging & Interval Defaults
            console_log_level = console_log_level or "WARNING"
            file_log_level = file_log_level or "DEBUG"
            interval = sync_interval if sync_interval is not None else 10

            if interval > 0:
                setup_scheduling(interval, encryption_password)

            # 3. Save initial config
            general = current_config.setdefault("general", {})
            general["encryption_enabled"] = encrypt_creds
            general["encrypt_emails"] = encrypt_emails
            general["salt"] = salt_val
            if canary:
                general["canary"] = canary
            general["sync_interval"] = interval
            general["console_log_level"] = console_log_level
            general["file_log_level"] = file_log_level

            config.save_config(current_config, config_path)
            return True, encryption_password

        # === Interactive Flow ===
        print("\n=== Wugong Email Initialization ===")

        # Check if already initialized
        if current_config.get("general", {}).get("salt"):
            print("\n❌ Wugong is already initialized.")
            print("⚠️  If you need to change your encryption password, please uninstall and reinstall Wugong.")
            print("💡 Use 'wugong configure' to modify settings like the sync interval.")
            return False, None

        # 1. Encryption Setup
        if encrypt_creds is None:
            if (encrypt_creds := questionary.confirm("Enable credential encryption? (Highly Recommended)", default=True).ask()) is None:
                raise KeyboardInterrupt

        if encrypt_emails is None:
            if (encrypt_emails := questionary.confirm("Encrypt locally cached email bodies?", default=True).ask()) is None:
                raise KeyboardInterrupt

        encrypt_enabled = encrypt_creds or encrypt_emails
        salt_val = ""
        canary = ""
        encryption_password = None

        if encrypt_enabled:
            encryption_password = config.get_encryption_password(args, prompt_text="Set your encryption password:")
            if encryption_password is None:
                raise KeyboardInterrupt
            
            if not encryption_password:
                print("❌ Encryption password cannot be empty when encryption is enabled. Initialization aborted.")
                return False, None
            salt_raw = generate_salt()
            salt_val = base64.b64encode(salt_raw).decode()
            canary = encrypt_data("wugong", encryption_password, salt_raw)
        else:
            print("\n[Warning] Encryption is disabled. Your credentials and data will be stored in plain text.")

        # 2. Logging Setup
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if console_log_level is None:
            if (console_log_level := questionary.select(
                "Select default console log level:",
                choices=log_levels,
                default="WARNING"
            ).ask()) is None:
                raise KeyboardInterrupt

        if file_log_level is None:
            if (file_log_level := questionary.select(
                "Select default file log level:",
                choices=log_levels,
                default="DEBUG"
            ).ask()) is None:
                raise KeyboardInterrupt

        # 3. Sync Interval & Scheduling
        if sync_interval is None:
            if (sync_interval_str := questionary.text("Sync interval in minutes (e.g., 5, 10, 60. Enter 0 to disable auto-sync):", default="10").ask()) is None:
                raise KeyboardInterrupt
            else:
                interval = int(sync_interval_str) if sync_interval_str.isdigit() else 10
        else:
            interval = sync_interval

        if interval > 0:
            setup_scheduling(interval, encryption_password)

        # 4. Save initial config
        general = current_config.setdefault("general", {})
        general["encryption_enabled"] = encrypt_creds
        general["encrypt_emails"] = encrypt_emails
        general["salt"] = salt_val
        if canary:
            general["canary"] = canary
        general["sync_interval"] = interval
        general["console_log_level"] = console_log_level
        general["file_log_level"] = file_log_level

        config.save_config(current_config, config_path)

        # 5. Success Message
        print(f"\n✅ Configuration initialized and saved to {config_path}")
        print(f"ℹ️  Sync interval: {interval} minutes.")
        print(f"ℹ️  Console log level: {console_log_level}")
        print(f"ℹ️  File log level: {file_log_level} (logged to ~/.wugong/wugong.log)")

        if not current_config.get("accounts"):
            print("\n💡 Tip: No accounts found. Use 'wugong account add' to add your first email account.")

        return True, encryption_password
    except KeyboardInterrupt:
        print("\nInitialization cancelled.")
        return False, None
    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
        return False, None

def handle_init(args: argparse.Namespace, manager: MailManager) -> None:
    """Handles the 'init' command to setup encryption and sync schedule."""
    if os.name == 'nt':
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            console.print("[yellow]Warning: You are not running as administrator. Scheduling may fail.[/yellow]")
            console.print("[yellow]Please run the terminal as Administrator and try again if schtasks fails.[/yellow]\n")

    init_wizard(
        args=args,
        encrypt_creds=args.encrypt_creds,
        encrypt_emails=args.encrypt_emails,
        console_log_level=args.console_log_level,
        file_log_level=args.file_log_level,
        sync_interval=args.sync_interval,
        non_interactive=getattr(args, "non_interactive", False)
    )

def handle_configure(args: argparse.Namespace, manager: MailManager) -> None:
    """Handles the 'configure' command to modify sync settings."""
    configure_wizard(
        args=args,
        console_log_level=args.console_log_level,
        file_log_level=args.file_log_level,
        sync_interval=args.sync_interval,
        non_interactive=getattr(args, "non_interactive", False)
    )
