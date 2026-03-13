#!/bin/bash

# --- Configuration ---
INSTALL_DIR="$HOME/.wugong"
REPO_URL="https://github.com/kevinhuang001/wugong-email.git"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🔄 Checking for updates for Wugong Email...${NC}"

# 1. Check if it's a git repository or needs to be cloned
if [ ! -d "$REPO_DIR/.git" ]; then
    echo -e "${YELLOW}ℹ️  Using $REPO_URL as source.${NC}"
    TEMP_DIR=$(mktemp -d)
    
    # Check if we have a local version to compare with
    LOCAL_COMMIT=""
    if [ -f "$INSTALL_DIR/.version" ]; then
        LOCAL_COMMIT=$(cat "$INSTALL_DIR/.version")
    fi

    # Get remote head commit hash without full clone first
    REMOTE_COMMIT=$(git ls-remote "$REPO_URL" HEAD | awk '{print $1}')
    
    if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ] && [ -n "$LOCAL_COMMIT" ]; then
        echo -e "${GREEN}✅ Wugong Email is already up to date.${NC}"
        [ -d "$TEMP_DIR" ] && rm -rf "$TEMP_DIR"
        exit 0
    fi

    # Clone only if update needed, and hide git output
    git clone --depth 1 "$REPO_URL" "$TEMP_DIR" &>/dev/null || { echo -e "${RED}❌ Error: Failed to clone repository.${NC}"; exit 1; }
    SOURCE_DIR="$TEMP_DIR"
    UPDATE_NEEDED=true
    NEW_VERSION="$REMOTE_COMMIT"
else
    echo -e "${BLUE}📡 Fetching remote changes...${NC}"
    cd "$REPO_DIR" || exit
    # Ensure remote URL is correct
    git remote set-url origin "$REPO_URL" 2>/dev/null || git remote add origin "$REPO_URL"
    git fetch origin &>/dev/null

    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse @{u})

    if [ "$LOCAL" = "$REMOTE" ]; then
        echo -e "${GREEN}✅ Wugong Email is already up to date.${NC}"
        exit 0
    fi
    SOURCE_DIR="$REPO_DIR"
    UPDATE_NEEDED=true
    NEW_VERSION="$REMOTE"
fi

# 2. Ask for confirmation
if [ "$UPDATE_NEEDED" = true ]; then
    echo -e "${YELLOW}🔔 A new version of Wugong Email is available!${NC}"
    read -p "Do you want to update to the latest version? (y/N) " confirm

    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}❌ Update cancelled.${NC}"
        [ -n "$TEMP_DIR" ] && rm -rf "$TEMP_DIR"
        exit 0
    fi
fi

# 3. Perform Update
if [ -n "$TEMP_DIR" ]; then
    echo -e "${BLUE}🚀 Using files from cloned repository...${NC}"
else
    echo -e "${BLUE}🚀 Pulling latest changes...${NC}"
    git pull origin main || git pull origin master
fi

# 4. Update Installation
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${BLUE}📦 Updating files...${NC}"
    
    # Custom sync logic: copy ALL files except hidden directories and the update script itself
    # We use find to get all files in the source directory, excluding .git, .venv, and __pycache__
    find "$SOURCE_DIR" -maxdepth 1 -not -path '*/.*' -not -path '*/__pycache__*' -not -name "update.sh" -type f -exec cp {} "$INSTALL_DIR/" \;

    # Update dependencies
    cd "$INSTALL_DIR" || exit
    if [ -d ".venv" ]; then
        source .venv/bin/activate &>/dev/null
        if command -v uv &> /dev/null; then
            uv pip install -r requirements.txt &>/dev/null
        else
            pip install -r requirements.txt &>/dev/null
        fi
    fi
    
    # Finally, update the update script itself
    cp "$SOURCE_DIR/update.sh" "$INSTALL_DIR/update.sh"
    
    # Save the current version if we cloned it
    if [ -n "$NEW_VERSION" ]; then
        echo "$NEW_VERSION" > "$INSTALL_DIR/.version"
    fi
    
    echo -e "${GREEN}✅ Update completed.${NC}"
else
    echo -e "${YELLOW}ℹ️  Installation directory $INSTALL_DIR not found, update only applied to source.${NC}"
fi

# 5. Cleanup
if [ -n "$TEMP_DIR" ]; then
    rm -rf "$TEMP_DIR"
fi

echo -e "\n${GREEN}🎉 Wugong Email has been updated successfully!${NC}"
echo -e "--------------------------------------------------"
