#!/bin/bash
set -xe

bash build.sh

script_dir="$(cd "$(dirname "$0")"; pwd)"
GZ_LOG_DIR="$script_dir/../logs"

source "${script_dir}"/active_env.sh

if command -v lsof >/dev/null 2>&1; then
    old_pid=$(lsof -ti:8000 || true)
elif command -v netstat >/dev/null 2>&1; then
    old_pid=$(netstat -nlp 2>/dev/null | grep ':8000' | awk '{print $7}' | cut -d'/' -f1 || true)
else
    old_pid=""
fi

if [ -n "$old_pid" ]; then
    echo "Killing old process on port 8000: $old_pid"
    kill -9 $old_pid || true
else
    echo "No old process found on port 8000"
fi

if [ -n "$ENABLE_IPV6" ]; then
    host_addr='::'
else
    host_addr='0.0.0.0'
fi

mkdir -p "$GZ_LOG_DIR"

# start jupyter proxy
GZ_LOG_DIR=$GZ_LOG_DIR python -m uvicorn app.main:app --host $host_addr --port 8000 >> "$GZ_LOG_DIR"/gz-backend-server.log 2>&1 &
echo "Server started. Logs: $GZ_LOG_DIR/gz-backend-server.log"