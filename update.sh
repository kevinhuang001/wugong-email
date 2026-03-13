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
    echo -e "${YELLOW}ℹ️  Not running from a git repository. Using $REPO_URL as source.${NC}"
    TEMP_DIR=$(mktemp -d)
    git clone --depth 1 "$REPO_URL" "$TEMP_DIR" || { echo -e "${RED}❌ Error: Failed to clone repository.${NC}"; exit 1; }
    SOURCE_DIR="$TEMP_DIR"
    UPDATE_NEEDED=true
else
    echo -e "${BLUE}📡 Fetching remote changes from $REPO_URL...${NC}"
    cd "$REPO_DIR" || exit
    # Ensure remote URL is correct
    git remote set-url origin "$REPO_URL" 2>/dev/null || git remote add origin "$REPO_URL"
    git fetch origin

    LOCAL=$(git rev-parse @)
    REMOTE=$(git rev-parse @{u})

    if [ "$LOCAL" = "$REMOTE" ]; then
        echo -e "${GREEN}✅ Wugong Email is already up to date.${NC}"
        exit 0
    fi
    SOURCE_DIR="$REPO_DIR"
    UPDATE_NEEDED=true
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
    
    # Custom sync logic: copy files individually to avoid rsync dependency and be cleaner
    # We copy all .py files, scripts, and requirements
    for file in "$SOURCE_DIR"/*.py "$SOURCE_DIR"/*.sh "$SOURCE_DIR"/requirements.txt "$SOURCE_DIR"/README.md "$SOURCE_DIR"/.gitignore; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            # Skip updating itself while running to avoid shell confusion, update at the end
            if [ "$filename" != "update.sh" ]; then
                cp "$file" "$INSTALL_DIR/$filename"
            fi
        fi
    done

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
