#!/bin/bash

# --- Configuration ---
INSTALL_DIR="$HOME/.wugong"
CONFIG_DIR="$HOME/.config/wugong"
CONFIG_FILE="$CONFIG_DIR/config.toml"
MIN_PYTHON_VERSION="3.8"
REPO_URL="https://github.com/kevinhuang001/wugong-email.git"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Starting Wugong Email Installation...${NC}"

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: python3 is not installed. Please install Python >= $MIN_PYTHON_VERSION first.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if [[ $(echo -e "$PYTHON_VERSION\n$MIN_PYTHON_VERSION" | sort -V | head -n1) != "$MIN_PYTHON_VERSION" ]]; then
    echo -e "${RED}❌ Error: Python version $PYTHON_VERSION is too low. Required: >= $MIN_PYTHON_VERSION${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python $PYTHON_VERSION found.${NC}"

# 2. Check if running via curl or local
if [ -f "cli.py" ] && [ -f "wizard.py" ]; then
    echo -e "${BLUE}📂 Local source files found. Using current directory.${NC}"
    SOURCE_DIR=$(pwd)
else
    echo -e "${BLUE}📡 Source files not found locally. Cloning from GitHub...${NC}"
    TEMP_DIR=$(mktemp -d)
    git clone --quiet --depth 1 "$REPO_URL" "$TEMP_DIR" || { echo -e "${RED}❌ Error: Failed to clone repository.${NC}"; exit 1; }
    SOURCE_DIR="$TEMP_DIR"
fi

# 3. Create Directories
echo -e "${BLUE}📁 Creating directories...${NC}"
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"

# 4. Copy Files
echo -e "${BLUE}📦 Copying files...${NC}"
if command -v rsync &> /dev/null; then
    # Use --delete but EXCLUDE config, database, and venv/cache
    rsync -av --delete --exclude='.git' --exclude='.venv' --exclude='__pycache__' --exclude='*.db' --exclude='config.toml' "$SOURCE_DIR/" "$INSTALL_DIR/" &>/dev/null
else
    # Fallback to cp -R
    echo -e "${BLUE}⚠️  rsync not found, using cp -R (files will be overwritten)...${NC}"
    # Manually remove old core files to simulate --delete for critical files
    rm -f "$INSTALL_DIR/read_config.py"
    # Using a loop to avoid copying excluded dirs/files
    for item in "$SOURCE_DIR"/*; do
        [ -e "$item" ] || continue
        name=$(basename "$item")
        case "$name" in
            .git|.venv|__pycache__|*.db|config.toml) continue ;;
        esac
        cp -R "$item" "$INSTALL_DIR/" &>/dev/null
    done
fi

# 5. Setup Virtual Environment and Install Dependencies
cd "$INSTALL_DIR" || exit
if command -v uv &> /dev/null; then
    echo -e "${GREEN}✨ uv found! Using uv for faster installation...${NC}"
    uv venv &> /dev/null
    source .venv/bin/activate
    uv pip install --quiet -r requirements.txt
else
    echo -e "${BLUE}🐍 uv not found, using standard venv and pip...${NC}"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt
fi

# 6. Create Wrapper Scripts
echo -e "${BLUE}🔨 Setting up executable wrappers...${NC}"

# Ensure 'wugong' CLI wrapper is executable
chmod +x "$INSTALL_DIR/wugong"

# 7. Cleanup temp dir if created
if [ -n "$TEMP_DIR" ]; then
    rm -rf "$TEMP_DIR"
fi

# 8. Final Instructions
echo -e "\n${GREEN}🎉 Installation Complete!${NC}"
echo -e "--------------------------------------------------"
echo -e "Location: $INSTALL_DIR"
echo -e "Config:   $CONFIG_FILE"
echo -e "\n${BLUE}To use 'wugong' from anywhere, add this to your .zshrc or .bashrc:${NC}"
echo -e "${GREEN}export PATH=\"\$PATH:$INSTALL_DIR\"${NC}"
echo -e "Then run: ${BLUE}source ~/.zshrc${NC} (or your shell's config file)"
echo -e "--------------------------------------------------"
echo -e "Quick Start Guide:"
echo -e "1. ${BLUE}wugong init${NC}        - Setup master password & sync schedule"
echo -e "2. ${BLUE}wugong configure${NC}   - Modify sync interval"
echo -e "3. ${BLUE}wugong account add${NC} - Setup your email accounts"
echo -e "4. ${BLUE}wugong sync${NC}        - Manually sync emails"
echo -e "5. ${BLUE}wugong list${NC}        - View your emails"
echo -e "6. ${BLUE}wugong send${NC}        - Send an email"
echo -e "7. ${BLUE}wugong upgrade${NC}     - Update to the latest version"
echo -e "8. ${BLUE}wugong uninstall${NC}   - Uninstall Wugong Email"
echo -e "--------------------------------------------------"
