#!/usr/bin/env bash
set -euo pipefail

project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
script=${ADS_HEARTBEAT_TEST_SCRIPT:-$project/bin/ads-heartbeat-rejected-retain.sh}
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
root=$scratch/rejected
ads=$scratch/ads/2026-07-10.log
seeweb=$scratch/seeweb/192.0.2.20/2026-07-10.log
mkdir -p -- "$root/192.0.2.10" "$scratch/ads" "${seeweb%/*}"
old=$root/192.0.2.10/2026-07-10.log
boundary=$root/192.0.2.10/2026-07-11.log
today=$root/192.0.2.10/2026-10-08.log
printf 'old\n' > "$old"
printf 'boundary\n' > "$boundary"
printf 'today\n' > "$today"
printf 'AdS\n' > "$ads"
printf 'Seeweb\n' > "$seeweb"

set +e
out=$(ADS_HEARTBEAT_REJECTED_ROOT="$scratch/missing" ADS_TODAY=2026-10-08 bash "$script" --inspect 2>&1)
code=$?
set -e
[[ $code -eq 2 && $out == *"ads-heartbeat-rejected-retain status=warning result=no-root"* ]] || { printf 'missing root not reported\n' >&2; exit 1; }

set +e
out=$(ADS_HEARTBEAT_REJECTED_ROOT="$root" ADS_TODAY=2026-10-08 bash "$script" --inspect 2>&1)
code=$?
set -e
[[ $code -eq 0 && $out == *"ads-heartbeat-rejected-retain status=ok mode=inspect sources=1 files=3 bytes=19"* ]] || { printf 'wrong archive measured (exit %s): %s\n' "$code" "$out" >&2; exit 1; }

if ADS_HEARTBEAT_REJECTED_ROOT="$root" ADS_TODAY=2026-10-08 bash "$script" --apply >/dev/null 2>&1; then
    printf 'apply without retention days accepted\n' >&2; exit 1
fi
out=$(ADS_HEARTBEAT_REJECTED_ROOT="$root" ADS_TODAY=2026-10-08 bash "$script" --dry-run --days 90 2>&1)
[[ $out == *"cutoff=2026-07-11 expired=1 expired_bytes=4"* && $out == *"would-delete=$old"* ]] || { printf 'dry run wrong: %s\n' "$out" >&2; exit 1; }
[[ -f $old && -f $boundary && -f $today && -f $ads && -f $seeweb ]]

out=$(ADS_HEARTBEAT_REJECTED_ROOT="$root" ADS_TODAY=2026-10-08 bash "$script" --apply --days 90 2>&1)
[[ $out == *"deleted=$old"* && $out == *"mode=apply sources=1 files=2 bytes=15"* ]] || { printf 'apply wrong: %s\n' "$out" >&2; exit 1; }
[[ ! -e $old && -f $boundary && -f $today && -f $ads && -f $seeweb ]] || { printf 'archive isolation failed\n' >&2; exit 1; }

ln -s "$ads" "$root/192.0.2.10/2026-07-09.log"
if ADS_HEARTBEAT_REJECTED_ROOT="$root" ADS_TODAY=2026-10-08 bash "$script" --apply --days 90 >/dev/null 2>&1; then
    printf 'symbolic log accepted\n' >&2; exit 1
fi
[[ -f $ads ]] || { printf 'AdS original changed\n' >&2; exit 1; }
rm -- "$root/192.0.2.10/2026-07-09.log"
ln -- "$ads" "$root/192.0.2.10/2026-07-08.log"
if ADS_HEARTBEAT_REJECTED_ROOT="$root" ADS_TODAY=2026-10-08 bash "$script" --apply --days 90 >/dev/null 2>&1; then
    printf 'hard-linked log accepted\n' >&2; exit 1
fi
[[ -f $ads ]] || { printf 'AdS original changed through hard link\n' >&2; exit 1; }
printf 'test_heartbeat_rejected_retain: OK\n'
