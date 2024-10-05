echo '0 2 * * *' /usr/bin/python3 `pwd`/vCard23cx.py vCard23cx.ini > /etc/cron.d/vCard23cx
chmod a+x /etc/cron.d/vCard23cx
