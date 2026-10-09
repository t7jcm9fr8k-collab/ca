#!/bin/sh
cd "$(dirname "$0")"
date -u +"start %H:%M:%S" > progress.log
xargs -P 4 -L 1 sh -c 'python3 -B size_study.py "$0" "$1" "$2" "$3" "$4" "$5" 2>> progress.log' < jobs.txt
date -u +"end %H:%M:%S" >> progress.log
