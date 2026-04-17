#!/bin/bash
# Run after filling in .env
PROJ_DIR="$HOME/tech-alert-agent"
PYTHON="$PROJ_DIR/venv/bin/python3"
LOG="$PROJ_DIR/logs/cron.log"

(crontab -l 2>/dev/null; cat <<EOF
# Tech Alert Agent — Full briefing (8 AM & 8 PM MYT = 0:00 & 12:00 UTC)
0  0  * * *  $PYTHON $PROJ_DIR/main.py --mode full >> $LOG 2>&1
0  12 * * *  $PYTHON $PROJ_DIR/main.py --mode full >> $LOG 2>&1
# Hourly HIGH ALERT scan
0  *  * * *  $PYTHON $PROJ_DIR/main.py --mode alert >> $LOG 2>&1
EOF
) | crontab -

echo "Crontab installed:"
crontab -l
