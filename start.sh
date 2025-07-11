#!/bin/bash
# Startet SSH, Cron und den Flask-Webserver

/usr/sbin/sshd &
cron &
exec python3 /scripts/webhook.py
