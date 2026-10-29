#!/usr/bin/env bash
set -euo pipefail

project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
script=${ADS_UNCLASSIFIED_TEST_SCRIPT:-$project/bin/ads-unclassified-retain.sh}
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
root=$scratch/unclassified
ads=$scratch/ads/2026-07-10.log
seeweb=$scratch/seeweb/2026-07-10.log
mkdir -p -- "$root" "${ads%/*}" "${seeweb%/*}" "$scratch/fakebin"
printf 'AdS\n' >"$ads"
printf 'Seeweb\n' >"$seeweb"

cat >"$scratch/fakebin/df" <<'EOF'
#!/usr/bin/env bash
printf 'Filesystem 1024-blocks Used Available Capacity Mounted on\n'
printf 'fake       1000        500  500       50%%      /fake\n'
EOF
chmod +x "$scratch/fakebin/df"

inspect() {
    PATH="$scratch/fakebin:$PATH" ADS_UNCLASSIFIED_ROOT="$root" ADS_TODAY=2026-10-08 \
        bash "$script" "$@" 2>&1
}

set +e
out=$(PATH="$scratch/fakebin:$PATH" ADS_UNCLASSIFIED_ROOT="$scratch/missing" ADS_TODAY=2026-10-08 bash "$script" --inspect 2>&1)
code=$?
set -e
[[ $code -eq 2 && $out == *"status=warning result=no-root"* ]] || { printf 'missing archive passed\n' >&2; exit 1; }

set +e
out=$(inspect --inspect)
code=$?
set -e
[[ $code -eq 0 && $out == *"ads-unclassified-retain status=ok mode=inspect sources=0 files=0 bytes=0"* ]] || { printf 'empty quarantine was not healthy\n' >&2; exit 1; }

mkdir -p -- "$root/192.0.2.10"
old=$root/192.0.2.10/2026-07-10.log
boundary=$root/192.0.2.10/2026-07-11.log
today=$root/192.0.2.10/2026-10-08.log
printf 'old\n' >"$old"
printf 'boundary\n' >"$boundary"
printf 'today\n' >"$today"

if inspect --apply >/dev/null 2>&1; then
    printf 'deletion without days accepted\n' >&2; exit 1
fi
out=$(inspect --dry-run --days 90)
[[ $out == *"cutoff=2026-07-11 expired=1 expired_bytes=4"* && $out == *"would-delete=$old"* ]] || { printf 'wrong dry run\n' >&2; exit 1; }
[[ -f $old && -f $ads && -f $seeweb ]] || { printf 'dry run changed an archive\n' >&2; exit 1; }

out=$(inspect --apply --days 90)
[[ $out == *"status=ok mode=apply sources=1 files=2"* && $out == *"deleted=$old"* ]] || { printf 'wrong retention result\n' >&2; exit 1; }
[[ ! -e $old && -f $boundary && -f $today && -f $ads && -f $seeweb ]] || { printf 'archive isolation failed\n' >&2; exit 1; }

cat >"$scratch/fakebin/df" <<'EOF'
#!/usr/bin/env bash
printf 'Filesystem 1024-blocks Used Available Capacity Mounted on\n'
printf 'fake       1000        800  200       80%%      /fake\n'
EOF
set +e
out=$(inspect --inspect)
code=$?
set -e
[[ $code -eq 2 && $out == *"status=warning"* && $out == *"filesystem_used_pct=80"* ]] || { printf 'capacity warning missing\n' >&2; exit 1; }

cat >"$scratch/fakebin/df" <<'EOF'
#!/usr/bin/env bash
exit 9
EOF
set +e
out=$(inspect --inspect)
code=$?
set -e
[[ $code -eq 1 && $out == *"status=error utilizzo filesystem non leggibile"* ]] || { printf 'failed capacity measure was silent\n' >&2; exit 1; }

printf 'test_unclassified_retain: OK\n'
