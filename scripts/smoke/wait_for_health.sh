#!/usr/bin/env bash

set -euo pipefail

port="${1:?Usage: wait_for_health.sh PORT}"
url="http://127.0.0.1:${port}/_stcore/health"

for attempt in $(seq 1 30); do
    if curl --fail --silent --max-time 3 "$url" > /dev/null; then
        echo "Application is healthy on port ${port}."
        exit 0
    fi

    echo "Waiting for application health (${attempt}/30)..."
    sleep 2
done

echo "Application did not become healthy: ${url}" >&2
exit 1