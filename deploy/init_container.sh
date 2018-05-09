printenv | grep -e "^PULSE" -e "^PATH" | cat - /etc/crontab > /tmp/crontab && mv /tmp/crontab /etc/crontab 
cron -f
