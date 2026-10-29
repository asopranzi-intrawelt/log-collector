#!/usr/bin/env bash
set -euo pipefail

script=${ADS_SEEWEB_TEST_SCRIPT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/bin/ads-seeweb-technical-retain.sh}
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
root=$scratch/seeweb
mkdir -p -- "$root/192.0.2.9" "$scratch/ads" "$scratch/fakebin"
old=$root/192.0.2.9/2026-07-10.log
boundary=$root/192.0.2.9/2026-07-11.log
new=$root/192.0.2.9/2026-10-08.log
zero=$root/192.0.2.9/2026-10-07.log
ads=$scratch/ads/2026-07-10.log
printf 'old\n' >"$old"
printf 'boundary\n' >"$boundary"
printf 'new\n' >"$new"
: >"$zero"
printf 'ads\n' >"$ads"

set +e
out=$(ADS_SEEWEB_TECH_ROOT="$scratch/missing" ADS_TODAY=2026-10-08 bash "$script" --inspect 2>&1)
code=$?
set -e
[[ $code -eq 2 && $out == *"status=warning result=no-root"* ]]

mkdir -p -- "$scratch/empty/192.0.2.9"
set +e
out=$(ADS_SEEWEB_TECH_ROOT="$scratch/empty" ADS_TODAY=2026-10-08 bash "$script" --inspect 2>&1)
code=$?
set -e
[[ $code -eq 2 && $out == *"status=warning mode=inspect sources=1 files=0"* ]]
set +e
out=$(ADS_TECH_EMPTY_OK=1 ADS_SEEWEB_TECH_ROOT="$scratch/empty" ADS_TODAY=2026-10-08 bash "$script" --inspect 2>&1)
code=$?
set -e
[[ $code -eq 2 && $out == *"status=warning mode=inspect sources=1 files=0"* ]] || { printf 'Seeweb accepted ambient empty-ok setting\n' >&2; exit 1; }

out=$(ADS_SEEWEB_TECH_ROOT="$root" ADS_TODAY=2026-10-08 bash "$script" --inspect 2>&1)
[[ $out == *"mode=inspect sources=1 files=4 bytes=17"* && $out == *"oldest=2026-07-10 newest=2026-10-08"* ]]
[[ -f $old && -f $boundary && -f $new && -f $zero && -f $ads ]]

if ADS_SEEWEB_TECH_ROOT="$root" ADS_TODAY=2026-10-08 bash "$script" --apply >/dev/null 2>&1; then
    printf 'apply without a policy accepted\n' >&2; exit 1
fi
out=$(ADS_SEEWEB_TECH_ROOT="$root" ADS_TODAY=2026-10-08 bash "$script" --dry-run --days 90 2>&1)
[[ $out == *"cutoff=2026-07-11 expired=1 expired_bytes=4"* && $out == *"would-delete=$old"* ]]
[[ -f $old && -f $ads ]]

out=$(ADS_SEEWEB_TECH_ROOT="$root" ADS_TODAY=2026-10-08 bash "$script" --apply --days 90 2>&1)
[[ $out == *"deleted=$old"* && $out == *"mode=apply sources=1 files=3 bytes=13"* && $out == *"expired=1"* ]]
[[ ! -e $old && -f $boundary && -f $new && -f $zero && -f $ads ]]

mkdir -p -- "$scratch/all-old/192.0.2.10"
only_old=$scratch/all-old/192.0.2.10/2026-07-10.log
: >"$only_old"
set +e
out=$(ADS_SEEWEB_TECH_ROOT="$scratch/all-old" ADS_TODAY=2026-10-08 bash "$script" --apply --days 90 2>&1)
code=$?
set -e
[[ $code -eq 2 && $out == *"deleted=$only_old"* && $out == *"status=warning mode=apply sources=1 files=0 bytes=0 oldest=none newest=none"* ]]
[[ ! -e $only_old ]]

ln -s "$ads" "$root/192.0.2.9/2026-07-09.log"
[[ -L $root/192.0.2.9/2026-07-09.log ]] || { printf 'real symbolic links unavailable in this environment\n' >&2; exit 77; }
if ADS_SEEWEB_TECH_ROOT="$root" ADS_TODAY=2026-10-08 bash "$script" --apply --days 90 >/dev/null 2>&1; then
    printf 'symbolic log accepted\n' >&2; exit 1
fi
[[ -f $ads ]]
rm -- "$root/192.0.2.9/2026-07-09.log"

cat >"$scratch/fakebin/df" <<'EOF'
#!/usr/bin/env bash
printf 'Filesystem 1024-blocks Used Available Capacity Mounted on\n'
printf 'fake       1000        800  200       80%%      /fake\n'
EOF
chmod +x "$scratch/fakebin/df"
set +e
out=$(PATH="$scratch/fakebin:$PATH" ADS_SEEWEB_TECH_ROOT="$root" ADS_TODAY=2026-10-08 bash "$script" --inspect 2>&1)
code=$?
set -e
[[ $code -eq 2 && $out == *"status=warning"* && $out == *"filesystem_used_pct=80"* ]]

printf 'test_seeweb_technical_retain: OK\n'
