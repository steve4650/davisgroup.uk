#!/bin/bash
sudo -u deploy bash -c "cd /home/deploy/git/davisgroup.uk && bun upgrade && uv self update && git pull origin main && uv run make.py build"
rsync -rv --delete /home/deploy/git/davisgroup.uk/dist/ /var/www/html/
rsync -rv --delete /var/www/secret-predeploy/ /var/www/secret/
chown -Rv root:root /var/www/html/
find /var/www/html -mindepth 1 -exec restorecon -v {} \;