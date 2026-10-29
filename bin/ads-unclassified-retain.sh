#!/usr/bin/env bash
# Il deposito dei mittenti sconosciuti puo' essere vuoto senza essere guasto.
set -euo pipefail
export ADS_TECH_ROOT=${ADS_UNCLASSIFIED_ROOT:-/var/log/ads-unclassified}
export ADS_TECH_LABEL=ads-unclassified-retain
export ADS_TECH_EMPTY_OK=1
exec /usr/bin/bash "$(dirname -- "${BASH_SOURCE[0]}")/ads-technical-retain.sh" "$@"
