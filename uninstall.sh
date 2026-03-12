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

# 2. Remove Installation Directory
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${BLUE}📁 Removing installation directory: $INSTALL_DIR...${NC}"
    rm -rf "$INSTALL_DIR"
    echo -e "${GREEN}✅ Installation directory removed.${NC}"
else
    echo -e "${YELLOW}ℹ️  Installation directory $INSTALL_DIR not found, skipping.${NC}"
fi

# 3. Remove Configuration Directory
if [ -d "$CONFIG_DIR" ]; then
    echo -e "${BLUE}📁 Removing configuration directory: $CONFIG_DIR...${NC}"
    rm -rf "$CONFIG_DIR"
    echo -e "${GREEN}✅ Configuration directory removed.${NC}"
else
    echo -e "${YELLOW}ℹ️  Configuration directory $CONFIG_DIR not found, skipping.${NC}"
fi

# 4. Final message
echo -e "\n${GREEN}🎉 Wugong Email has been successfully uninstalled.${NC}"
echo -e "Note: If you added $INSTALL_DIR to your PATH in .zshrc or .bashrc, please remove it manually."
echo -e "--------------------------------------------------"
