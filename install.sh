#!/bin/bash

# --- Configuration ---
INSTALL_DIR="$HOME/.wugong"
CONFIG_DIR="$HOME/.config/wugong"
CONFIG_FILE="$CONFIG_DIR/config.toml"
MIN_PYTHON_VERSION="3.8"

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

# 2. Create Directories
echo -e "${BLUE}📁 Creating directories...${NC}"
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"

# 3. Copy Files
echo -e "${BLUE}📦 Copying source files...${NC}"
cp *.py "$INSTALL_DIR/"
cp requirements.txt "$INSTALL_DIR/"
cp uninstall.sh "$INSTALL_DIR/"
cp update.sh "$INSTALL_DIR/"

# 4. Setup Virtual Environment and Install Dependencies
cd "$INSTALL_DIR" || exit
if command -v uv &> /dev/null; then
    echo -e "${GREEN}✨ uv found! Using uv for faster installation...${NC}"
    uv venv &> /dev/null
    source .venv/bin/activate
    uv pip install -r requirements.txt
else
    echo -e "${BLUE}🐍 uv not found, using standard venv and pip...${NC}"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# 5. Create Wrapper Scripts
echo -e "${BLUE}🔨 Creating executable wrappers...${NC}"

# Main 'wugong' CLI wrapper
cat > wugong <<EOF
#!/bin/bash
source "$INSTALL_DIR/.venv/bin/activate"
export WUGONG_CONFIG="$CONFIG_FILE"
python3 "$INSTALL_DIR/cli.py" "\$@"
EOF

# 'wugong-wizard' wrapper
cat > wugong-wizard <<EOF
#!/bin/bash
source "$INSTALL_DIR/.venv/bin/activate"
export WUGONG_CONFIG="$CONFIG_FILE"
python3 "$INSTALL_DIR/wizard.py" "\$@"
EOF

chmod +x wugong wugong-wizard

# 6. Final Instructions
echo -e "\n${GREEN}🎉 Installation Complete!${NC}"
echo -e "--------------------------------------------------"
echo -e "Location: $INSTALL_DIR"
echo -e "Config:   $CONFIG_FILE"
echo -e "\n${BLUE}To use 'wugong' from anywhere, add this to your .zshrc or .bashrc:${NC}"
echo -e "${GREEN}export PATH=\"\$PATH:$INSTALL_DIR\"${NC}"
echo -e "--------------------------------------------------"
echo -e "Run ${GREEN}wugong-wizard${NC} to configure your first account."
echo -e "Run ${GREEN}wugong list${NC} to view your emails."
echo -e "Run ${GREEN}./update.sh${NC} in the installation directory to update."
echo -e "Run ${GREEN}./uninstall.sh${NC} in the installation directory to uninstall."
