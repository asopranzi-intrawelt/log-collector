#!/usr/bin/env bash
set -euo pipefail

script=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/bin/ads-ilo-other-retain.sh
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
root=$scratch/ilo
mkdir -p -- "$root/192.0.2.9" "$scratch/ads"
old=$root/192.0.2.9/2026-07-10.log
boundary=$root/192.0.2.9/2026-07-11.log
new=$root/192.0.2.9/2026-10-08.log
ads=$scratch/ads/2026-07-10.log
printf 'old\n' >"$old"
printf 'boundary\n' >"$boundary"
printf 'new\n' >"$new"
printf 'ads\n' >"$ads"

out=$(ADS_ILO_OTHER_ROOT="$root" ADS_TODAY=2026-10-08 bash "$script" --dry-run 2>&1)
[[ $out == *"expired=1"* && $out == *"would-delete=$old"* ]]
[[ -f $old && -f $boundary && -f $new && -f $ads ]]

out=$(ADS_ILO_OTHER_ROOT="$root" ADS_TODAY=2026-10-08 bash "$script" --apply 2>&1)
[[ $out == *"deleted=1"* ]]
[[ ! -e $old && -f $boundary && -f $new && -f $ads ]]

ln -s "$ads" "$root/192.0.2.9/2026-07-09.log"
if ADS_ILO_OTHER_ROOT="$root" ADS_TODAY=2026-10-08 bash "$script" --apply >/dev/null 2>&1; then
    printf 'symlink log accepted\n' >&2
    exit 1
fi
[[ -f $ads ]]

printf 'test_ilo_other_retain: OK\n'
