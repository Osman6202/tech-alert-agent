#!/bin/bash
# Run as ubuntu user on Oracle Cloud ARM VM (Ubuntu 22.04)
set -e

echo "=== Tech Alert Agent Setup ==="

# System dependencies
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip git

# Clone project
cd ~
git clone https://github.com/Osman6202/tech-alert-agent.git
cd tech-alert-agent

# Python environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
playwright install-deps chromium

# Secrets
cp .env.example .env
echo ">>> Edit .env with your API keys before continuing <<<"
echo "    nano .env"
echo ""
echo "After editing .env, run:"
echo "    bash deploy/install_cron.sh"
