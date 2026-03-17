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

# 2. Check if running via local file or piped (remote)
 if [ -f "$0" ]; then
     # Script is being executed as a local file (e.g., ./install.sh or bash install.sh)
     SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
     if [ -f "$SCRIPT_DIR/main.py" ] && [ -f "$SCRIPT_DIR/cli/configure.py" ]; then
         echo -e "${BLUE}📂 Local source files found at $SCRIPT_DIR. Using local version.${NC}"
         SOURCE_DIR="$SCRIPT_DIR"
     else
         echo -e "${BLUE}📡 Local script found but source files missing at $SCRIPT_DIR. Cloning from GitHub...${NC}"
         TEMP_DIR=$(mktemp -d)
         git clone --quiet --depth 1 "$REPO_URL" "$TEMP_DIR" || { echo -e "${RED}❌ Error: Failed to clone repository.${NC}"; exit 1; }
         SOURCE_DIR="$TEMP_DIR"
     fi
 else
     # Script is likely being piped (e.g., curl ... | bash)
     echo -e "${BLUE}📡 Remote execution detected. Checking for existing installation...${NC}"
     
     # Check for existing installation - only for remote/piped execution
     if [ -d "$INSTALL_DIR" ] && [ -f "$INSTALL_DIR/main.py" ] && [ -f "$INSTALL_DIR/.venv/bin/python3" ]; then
         echo -e "${BLUE}💡 Wugong Email is already installed at $INSTALL_DIR.${NC}"
         echo -e "${BLUE}🔄 Switching to upgrade mode...${NC}"
         # Run the existing installation's upgrade command
         "$INSTALL_DIR/.venv/bin/python3" "$INSTALL_DIR/main.py" upgrade "$@"
         exit 0
     fi

     echo -e "${BLUE}📡 Cloning from GitHub...${NC}"
     TEMP_DIR=$(mktemp -d)
     git clone --quiet --depth 1 "$REPO_URL" "$TEMP_DIR" || { echo -e "${RED}❌ Error: Failed to clone repository.${NC}"; exit 1; }
     SOURCE_DIR="$TEMP_DIR"
 fi

# 4. Create Directories
echo -e "${BLUE}📁 Creating directories...${NC}"
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"

# 5. Copy Files
echo -e "${BLUE}📦 Copying files...${NC}"
if command -v rsync &> /dev/null; then
    # Use --delete but EXCLUDE config, database, and venv/cache
    rsync -av --delete --exclude='.git' --exclude='.venv' --exclude='__pycache__' --exclude='*.db' --exclude='config.toml' "$SOURCE_DIR/" "$INSTALL_DIR/" &>/dev/null
else
    # Fallback to cp -R
    echo -e "${BLUE}⚠️  rsync not found, using cp -R (files will be overwritten)...${NC}"
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

# 6. Setup Virtual Environment and Install Dependencies
cd "$INSTALL_DIR" || exit
if command -v uv &> /dev/null; then
    echo -e "${GREEN}✨ uv found! Using uv for installation...${NC}"
    uv venv &> /dev/null
    source .venv/bin/activate
    # Use uv pip install -e . to install dependencies from pyproject.toml
    uv pip install --quiet -e .
else
    echo -e "${RED}❌ Error: uv not found. uv is required for installation.${NC}"
    echo -e "${BLUE}💡 Please install uv first: https://github.com/astral-sh/uv${NC}"
    exit 1
fi

# 7. Create Wrapper Scripts
echo -e "${BLUE}🔨 Setting up executable wrappers...${NC}"

# Ensure 'wugong' CLI wrapper is executable
chmod +x "$INSTALL_DIR/wugong"

# 8. Cleanup temp dir if created
if [ -n "$TEMP_DIR" ]; then
    rm -rf "$TEMP_DIR"
fi

# 9. Final Instructions
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
echo -e "2. ${BLUE}wugong configure${NC}   - Modify sync interval or settings"
echo -e "3. ${BLUE}wugong account add${NC} - Setup your email accounts"
echo -e "4. ${BLUE}wugong account list${NC}- List all configured accounts"
echo -e "5. ${BLUE}wugong sync${NC}        - Manually sync emails"
echo -e "6. ${BLUE}wugong list${NC}        - View your emails (search with -k)"
echo -e "7. ${BLUE}wugong read -i <ID>${NC}- Read an email in terminal"
echo -e "8. ${BLUE}wugong send${NC}        - Send an email"
echo -e "9. ${BLUE}wugong delete -i <ID>${NC}- Delete an email"
echo -e "10. ${BLUE}wugong folder list${NC} - List all mailbox folders"
echo -e "11. ${BLUE}wugong upgrade${NC}     - Update to the latest version"
echo -e "12. ${BLUE}wugong uninstall${NC}   - Uninstall Wugong Email"
echo -e "--------------------------------------------------"
