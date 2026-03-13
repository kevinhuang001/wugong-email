#!/bin/bash

# --- Configuration ---
INSTALL_DIR="$HOME/.wugong"
CONFIG_DIR="$HOME/.config/wugong"
CONFIG_FILE="$CONFIG_DIR/config.toml"
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
    LOCAL_VERSION=""
    if [ -f "$INSTALL_DIR/.version" ]; then
        LOCAL_VERSION=$(cat "$INSTALL_DIR/.version" | xargs)
    fi

    # Get remote head version from .version file
    REMOTE_VERSION=$(curl -sSL "https://raw.githubusercontent.com/kevinhuang001/wugong-email/main/.version" | tr -d '\n\r' | xargs)
    
    if [ "$LOCAL_VERSION" = "$REMOTE_VERSION" ] && [ -n "$LOCAL_VERSION" ]; then
        echo -e "${GREEN}✅ Wugong Email is already up to date (v$LOCAL_VERSION).${NC}"
        [ -d "$TEMP_DIR" ] && rm -rf "$TEMP_DIR"
        exit 0
    fi

    # Clone only if update needed, and hide git output
    git clone --depth 1 "$REPO_URL" "$TEMP_DIR" &>/dev/null || { echo -e "${RED}❌ Error: Failed to clone repository.${NC}"; exit 1; }
    SOURCE_DIR="$TEMP_DIR"
    UPDATE_NEEDED=true
    NEW_VERSION="$REMOTE_VERSION"
else
    echo -e "${BLUE}📡 Fetching remote changes...${NC}"
    cd "$REPO_DIR" || exit
    # Ensure remote URL is correct
    git remote set-url origin "$REPO_URL" 2>/dev/null || git remote add origin "$REPO_URL"
    git fetch origin &>/dev/null

    LOCAL_VERSION=$(cat "$REPO_DIR/.version" 2>/dev/null)
    REMOTE_VERSION=$(git show origin/main:.version | tr -d '\n\r')

    if [ "$LOCAL_VERSION" = "$REMOTE_VERSION" ] && [ -n "$LOCAL_VERSION" ]; then
        echo -e "${GREEN}✅ Wugong Email is already up to date (v$LOCAL_VERSION).${NC}"
        exit 0
    fi
    SOURCE_DIR="$REPO_DIR"
    UPDATE_NEEDED=true
    NEW_VERSION="$REMOTE_VERSION"
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
    
    # Custom sync logic: copy ALL files and directories except hidden ones, venv, pycache, and the update script itself
    # Use rsync if available for cleaner directory syncing, otherwise fallback to cp -R
    if command -v rsync &> /dev/null; then
        # Use --delete but EXCLUDE config, database, and venv/cache
        # Ensure it overwrites by using -a (archive, which includes -r and -p etc)
        rsync -av --delete --ignore-errors --exclude='.git' --exclude='.venv' --exclude='__pycache__' --exclude='update.sh' --exclude='*.db' --exclude='config.toml' "$SOURCE_DIR/" "$INSTALL_DIR/" &>/dev/null
    else
        # Fallback to cp -R, but we need to be careful with exclusions
        echo -e "${BLUE}⚠️  rsync not found, using cp -Rf (files will be forced to overwrite)...${NC}"
        # Manually remove old core files to simulate --delete for critical files
        rm -f "$INSTALL_DIR/read_config.py"
        # Using a simple loop for top-level items to avoid copying excluded dirs
        for item in "$SOURCE_DIR"/*; do
            [ -e "$item" ] || continue
            name=$(basename "$item")
            case "$name" in
                .git|.venv|__pycache__|update.sh|*.db|config.toml) continue ;;
            esac
            # Use -f to force overwrite
            cp -Rf "$item" "$INSTALL_DIR/" &>/dev/null
        done
    fi

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
    
    # Ensure 'wugong' wrapper script is executable
    chmod +x "$INSTALL_DIR/wugong"
    
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
