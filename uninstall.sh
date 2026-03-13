#!/bin/bash

# --- Configuration ---
INSTALL_DIR="$HOME/.wugong"
CONFIG_DIR="$HOME/.config/wugong"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🗑️  Starting Wugong Email Uninstallation...${NC}"

# 1. Ask for confirmation
echo -e "${YELLOW}⚠️  Warning: This will remove all Wugong Email files and your configuration.${NC}"
read -p "Are you sure you want to uninstall Wugong Email? (y/N) " confirm

if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}❌ Uninstallation cancelled.${NC}"
    exit 0
fi

# 2. Remove Scheduled Tasks (Crontab)
echo -e "${BLUE}⏰ Removing scheduled sync tasks from Crontab...${NC}"
if command -v crontab &> /dev/null; then
    # Read current crontab, remove lines containing 'wugong sync all', and write back
    current_cron=$(crontab -l 2>/dev/null)
    if [ -n "$current_cron" ]; then
        new_cron=$(echo "$current_cron" | grep -v "wugong sync all")
        if [ "$current_cron" != "$new_cron" ]; then
            echo "$new_cron" | crontab -
            echo -e "${GREEN}✅ Crontab entries removed.${NC}"
        else
            echo -e "${YELLOW}ℹ️  No Wugong crontab entries found.${NC}"
        fi
    else
        echo -e "${YELLOW}ℹ️  Crontab is empty, skipping.${NC}"
    fi
fi

# 3. Remove Installation Directory
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${BLUE}📁 Removing installation directory: $INSTALL_DIR...${NC}"
    rm -rf "$INSTALL_DIR"
    echo -e "${GREEN}✅ Installation directory removed.${NC}"
else
    echo -e "${YELLOW}ℹ️  Installation directory $INSTALL_DIR not found, skipping.${NC}"
fi

# 4. Remove Configuration Directory
if [ -d "$CONFIG_DIR" ]; then
    read -p "Do you want to remove your configuration and email accounts? (y/N) " remove_config
    if [[ "$remove_config" =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}📁 Removing configuration directory: $CONFIG_DIR...${NC}"
        rm -rf "$CONFIG_DIR"
        echo -e "${GREEN}✅ Configuration directory removed.${NC}"
    else
        echo -e "${GREEN}📁 Configuration directory $CONFIG_DIR kept.${NC}"
    fi
else
    echo -e "${YELLOW}ℹ️  Configuration directory $CONFIG_DIR not found, skipping.${NC}"
fi

# 5. Final message
echo -e "\n${GREEN}🎉 Wugong Email has been successfully uninstalled.${NC}"
echo -e "Note: If you added $INSTALL_DIR to your PATH in .zshrc or .bashrc, please remove it manually."
echo -e "--------------------------------------------------"
