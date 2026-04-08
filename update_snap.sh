#!/bin/bash
set -eu

/usr/local/esa-snap/bin/snap --nosplash --nogui --modules --update-all 2>&1 | while read -r line; do
    echo "$line"
    # https://senbox.atlassian.net/wiki/spaces/SNAP/pages/30539785/Update+SNAP+from+the+command+line
     if [ "$line" = "updates=0" ]; then
        sleep 2
        if pgrep -f "snap/jre/bin/java" > /dev/null; then
            pkill -TERM -f "snap/jre/bin/java"
        fi
    fi
done