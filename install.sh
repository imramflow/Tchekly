#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}[*] TCHEKLY Email Validator Installation${NC}"
echo -e "${BLUE}[*] Created by ramflow${NC}\n"

# Check if running on Termux
if [ -d "/data/data/com.termux" ]; then
    echo -e "${BLUE}[*] Detected Termux environment${NC}"
    pkg update -y
    pkg install -y python git
else
    echo -e "${BLUE}[*] Detected standard Linux environment${NC}"
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y python3 python3-pip git
    elif command -v yum &> /dev/null; then
        sudo yum install -y python3 python3-pip git
    elif command -v pacman &> /dev/null; then
        sudo pacman -Sy python python-pip git
    fi
fi

# Create virtual environment
echo -e "\n${BLUE}[*] Creating virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

# Install requirements
echo -e "\n${BLUE}[*] Installing required packages...${NC}"
pip install -r requirements.txt

# Create necessary directories
echo -e "\n${BLUE}[*] Creating necessary directories...${NC}"
mkdir -p logs results/good_emails

# Make main script executable
chmod +x src/main.py

echo -e "\n${GREEN}[✓] Installation completed successfully!${NC}"
echo -e "${BLUE}[*] To run TCHEKLY:${NC}"
echo -e "1. Activate virtual environment: ${GREEN}source venv/bin/activate${NC}"
echo -e "2. Run the script: ${GREEN}python src/main.py${NC}\n"
