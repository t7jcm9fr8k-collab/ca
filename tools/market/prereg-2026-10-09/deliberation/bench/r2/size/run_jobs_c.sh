#!/bin/sh
cd "$(dirname "$0")"
date -u +"start-c %H:%M:%S" >> progress.log
xargs -P 4 -L 1 sh -c 'python3 -B size_study.py "$0" "$1" "$2" "$3" "$4" "$5" $6 2>> progress.log' < jobs-c.txt
date -u +"end-c %H:%M:%S" >> progress.log
