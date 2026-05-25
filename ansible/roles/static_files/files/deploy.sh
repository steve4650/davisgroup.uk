#!/bin/bash
rsync --info=NAME -r --delete /var/www/html-predeploy/ /var/www/html/
rsync --info=NAME -r --delete /var/www/secret-predeploy/ /var/www/secret/
chown -Rv root:root /var/www/html/
find /var/www/html -mindepth 1 -exec restorecon -v {} \;
find /var/www/html /var/www/html-predeploy /var/www/secret /var/www/secret-predeploy -type f -mtime +30 -delete
find /var/www/html /var/www/html-predeploy /var/www/secret /var/www/secret-predeploy -type d -empty -delete