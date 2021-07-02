#!/bin/zsh

/usr/bin/find . -type d -iname __pycache__ -exec rm -r {} \; 2>/dev/null

# /usr/local/bin/python3 -m zipapp src --compress --output appleloops --python="/usr/local/bin/python3"
/usr/local/bin/python3 -m zipapp src --output appleloops --python="/usr/local/bin/python3"
