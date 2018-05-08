printenv | grep -E "^PULSE" | cat - /etc/crontab > /tmp/crontab && mv /tmp/crontab /etc/crontab 
cron -f
