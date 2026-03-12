#!/bin/bash

# --- Configuration ---
INSTALL_DIR="$HOME/.wugong"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🔄 Checking for updates for Wugong Email...${NC}"

# 1. Check if it's a git repository
if [ ! -d "$REPO_DIR/.git" ]; then
    echo -e "${RED}❌ Error: This script must be run from a git repository.${NC}"
    exit 1
fi

# 2. Fetch remote changes
echo -e "${BLUE}📡 Fetching remote changes...${NC}"
git fetch origin

# 3. Compare local and remote
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u})

if [ "$LOCAL" = "$REMOTE" ]; then
    echo -e "${GREEN}✅ Wugong Email is already up to date.${NC}"
    exit 0
fi

# 4. Ask for confirmation
echo -e "${YELLOW}🔔 A new version of Wugong Email is available!${NC}"
read -p "Do you want to update to the latest version? (y/N) " confirm

if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}❌ Update cancelled.${NC}"
    exit 0
fi

# 5. Perform Update
echo -e "${BLUE}🚀 Updating source code...${NC}"
git pull origin main || git pull origin master

# 6. Update Installation (if exists)
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${BLUE}📦 Updating installed files in $INSTALL_DIR...${NC}"
    cp "$REPO_DIR"/*.py "$INSTALL_DIR/"
    cp "$REPO_DIR"/requirements.txt "$INSTALL_DIR/"

    # Update dependencies
    cd "$INSTALL_DIR" || exit
    if [ -d ".venv" ]; then
        source .venv/bin/activate
        if command -v uv &> /dev/null; then
            echo -e "${GREEN}✨ Using uv to update dependencies...${NC}"
            uv pip install -r requirements.txt
        else
            echo -e "${BLUE}🐍 Using pip to update dependencies...${NC}"
            pip install -r requirements.txt
        fi
    fi
    echo -e "${GREEN}✅ Installation updated.${NC}"
else
    echo -e "${YELLOW}ℹ️  Installation directory $INSTALL_DIR not found, only updated the source code.${NC}"
fi

echo -e "\n${GREEN}🎉 Wugong Email has been updated successfully!${NC}"
echo -e "--------------------------------------------------"
