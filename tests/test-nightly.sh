#!/usr/bin/env bash
# Prova end-to-end della catena locale su dati temporanei, senza host reali.
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
project_dir=$(cd -- "$script_dir/.." && pwd)
scratch=$(mktemp -d)
cleanup() {
    [[ $scratch == /tmp/tmp.* && -d $scratch ]] && rm -rf -- "$scratch"
}
trap cleanup EXIT

export ADS_LOG_ROOT=$scratch/logs
export ADS_STATE_ROOT=$scratch/state
mkdir -p -- "$ADS_LOG_ROOT/source-a" "$ADS_LOG_ROOT/source-b" "$ADS_STATE_ROOT"
printf '2026-10-06T14:43:16Z source-a login failure\n' >"$ADS_LOG_ROOT/source-a/2026-10-06.log"
printf '2026-10-06T14:44:00Z source-b login ok\n' >"$ADS_LOG_ROOT/source-b/2026-10-06.log"
cp -- "$ADS_LOG_ROOT/source-a/2026-10-06.log" "$scratch/original.log"

expect_failure() {
    if "$@" >"$scratch/output" 2>&1; then
        printf 'ERRORE: il comando doveva fallire: %s\n' "$*" >&2
        exit 1
    fi
}

ADS_TODAY=2026-10-07 bash "$project_dir/bin/ads-nightly.sh"
bash "$project_dir/bin/ads-verify.sh"
ADS_TODAY=2026-10-07 bash "$project_dir/bin/ads-nightly.sh"

# Il collaudo punto 5 deve cadere quando cambia anche un solo byte del log D-1.
printf 'X' | dd of="$ADS_LOG_ROOT/source-a/2026-10-06.log" bs=1 seek=0 count=1 conv=notrunc status=none
expect_failure bash "$project_dir/bin/ads-verify.sh"
grep -Fq 'log di origine diverso' "$scratch/output" || {
    printf 'ERRORE: il fallimento non dipende dal byte alterato\n' >&2
    exit 1
}
grep -Fq 'gzip -dc -- "$archive" | cmp -s - "$raw"' "$project_dir/bin/ads-verify.sh"
sed '/gzip -dc -- "\$archive" | cmp -s - "\$raw"/d' "$project_dir/bin/ads-verify.sh" >"$scratch/ads-verify-mutant.sh"
if grep -Fq 'gzip -dc -- "$archive" | cmp -s - "$raw"' "$scratch/ads-verify-mutant.sh"; then
    printf 'ERRORE: mutazione della verifica non applicata\n' >&2
    exit 1
fi
bash "$scratch/ads-verify-mutant.sh" --date 2026-10-06 >"$scratch/mutant-output"
cp -- "$scratch/original.log" "$ADS_LOG_ROOT/source-a/2026-10-06.log"
bash "$project_dir/bin/ads-verify.sh"

printf '2026-10-07T10:00:00Z source-a login ok\n' >"$ADS_LOG_ROOT/source-a/2026-10-07.log"
ADS_TODAY=2026-10-08 bash "$project_dir/bin/ads-nightly.sh"
bash "$project_dir/bin/ads-verify.sh"

# Anche alterare il manifest precedente deve spezzare il legame del giorno seguente.
printf 'x' >>"$ADS_STATE_ROOT/manifests/manifest-2026-10-06.txt"
expect_failure bash "$project_dir/bin/ads-verify.sh"
printf 'test-nightly: OK (due giorni, idempotenza, log alterato, catena alterata)\n'
