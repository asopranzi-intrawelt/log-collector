#!/usr/bin/env bash
# Keep the Seeweb command and environment contract while sharing the retention engine.
set -euo pipefail
export ADS_TECH_ROOT=${ADS_SEEWEB_TECH_ROOT:-/var/log/ads-seeweb-technical}
export ADS_TECH_LABEL=ads-seeweb-technical-retain
export ADS_TECH_EMPTY_OK=0
exec /usr/bin/bash "$(dirname -- "${BASH_SOURCE[0]}")/ads-technical-retain.sh" "$@"
