#!/usr/bin/env bash
# Rejected heartbeat markers are technical logs, not AdS originals or valid D6 signals.
set -euo pipefail
export ADS_TECH_ROOT=${ADS_HEARTBEAT_REJECTED_ROOT:-/var/log/ads-heartbeat-rejected}
export ADS_TECH_LABEL=ads-heartbeat-rejected-retain
exec /usr/bin/bash "$(dirname -- "${BASH_SOURCE[0]}")/ads-technical-retain.sh" "$@"
