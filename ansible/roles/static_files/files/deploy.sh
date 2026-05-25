#!/bin/bash
rsync --info=NAME -r --delete /var/www/html-predeploy/ /var/www/html/
rsync --info=NAME -r --delete /var/www/secret-predeploy/ /var/www/secret/
chown -Rv root:root /var/www/html/
find /var/www/html -mindepth 1 -exec restorecon -v {} \;