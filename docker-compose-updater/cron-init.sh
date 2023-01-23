#!/bin/sh

# Initialize cron
/usr/bin/crontab /crontab
# start cron
/usr/sbin/cron -f
