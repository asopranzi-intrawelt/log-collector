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

command -v mountpoint >/dev/null
if mountpoint -q -- "$ADS_LOG_ROOT"; then
    printf 'ERRORE: il percorso di prova risulta montato\n' >&2
    exit 1
fi
expect_failure env ADS_TODAY=2026-10-07 bash "$project_dir/bin/ads-nightly.sh" --require-log-mount
grep -Fq 'radice dei log non montata' "$scratch/output" || {
    printf 'ERRORE: il rifiuto non dipende dal mount\n' >&2
    cat "$scratch/output" >&2
    exit 1
}
[[ ! -e $ADS_STATE_ROOT/manifests/manifest-2026-10-06.txt ]]

# La radice di stato non può spostare lock, archivi e manifest fuori volume.
(
    export ADS_LOG_ROOT=$scratch/state-link-logs
    export ADS_STATE_ROOT=$scratch/state-link
    mkdir -p -- "$ADS_LOG_ROOT/source-a" "$scratch/state-outside"
    ln -s -- "$scratch/state-outside" "$ADS_STATE_ROOT"
    printf 'access\n' >"$ADS_LOG_ROOT/source-a/2026-10-06.log"
    expect_failure env ADS_TODAY=2026-10-07 bash "$project_dir/bin/ads-nightly.sh"
    grep -Fq 'directory di stato simbolica' "$scratch/output"
    [[ ! -e $scratch/state-outside/manifests/manifest-2026-10-06.txt ]]
)

# Un nome di sorgente valido non autorizza una directory archivio simbolica.
(
    export ADS_LOG_ROOT=$scratch/link-logs
    export ADS_STATE_ROOT=$scratch/link-state
    mkdir -p -- "$ADS_LOG_ROOT/source-a" "$ADS_STATE_ROOT/archives" "$scratch/outside"
    ln -s -- "$scratch/outside" "$ADS_STATE_ROOT/archives/source-a"
    printf 'access\n' >"$ADS_LOG_ROOT/source-a/2026-10-06.log"
    expect_failure env ADS_TODAY=2026-10-07 bash "$project_dir/bin/ads-nightly.sh"
    grep -Fq 'directory archivio simbolica' "$scratch/output"
    [[ ! -e $scratch/outside/2026-10-06.log.gz ]]
)

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
expect_failure python3 "$project_dir/bin/ads-measure-verify.py" --log-root "$ADS_LOG_ROOT" --state-root "$ADS_STATE_ROOT"
python3 -c 'import json,sys; d=json.load(open(sys.argv[1],encoding="utf-8")); assert d["status"] == "verification_failed"' "$scratch/output"
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
python3 "$project_dir/bin/ads-measure-verify.py" --log-root "$ADS_LOG_ROOT" --state-root "$ADS_STATE_ROOT" >"$scratch/measure.json"
python3 -c 'import json,sys; d=json.load(open(sys.argv[1],encoding="utf-8")); assert d["status"] == "ok" and d["manifests"] == 2 and d["archives"] == 3 and d["originals"] == 3 and d["elapsed_seconds"] >= 0' "$scratch/measure.json"
[[ $(grep -Ec 'source-a|source-b|login' "$scratch/measure.json") -eq 0 ]]

# Una verifica mirata non deve seguire un manifest precedente spostato fuori albero.
mv -- "$ADS_STATE_ROOT/manifests/manifest-2026-10-06.txt" "$scratch/manifest-precedente"
ln -s -- "$scratch/manifest-precedente" "$ADS_STATE_ROOT/manifests/manifest-2026-10-06.txt"
expect_failure bash "$project_dir/bin/ads-verify.sh" --date 2026-10-07
grep -Fq 'manifest precedente simbolico' "$scratch/output"
rm -- "$ADS_STATE_ROOT/manifests/manifest-2026-10-06.txt"
mv -- "$scratch/manifest-precedente" "$ADS_STATE_ROOT/manifests/manifest-2026-10-06.txt"
bash "$project_dir/bin/ads-verify.sh" --date 2026-10-07

# Un solo riavvio del timer deve recuperare tutti i giorni saltati nella finestra locale.
printf '2026-10-08T10:00:00Z source-a login ok\n' >"$ADS_LOG_ROOT/source-a/2026-10-08.log"
printf '2026-10-09T10:00:00Z source-b login ok\n' >"$ADS_LOG_ROOT/source-b/2026-10-09.log"
ADS_TODAY=2026-10-10 bash "$project_dir/bin/ads-nightly.sh"
bash "$project_dir/bin/ads-verify.sh"
[[ -f $ADS_STATE_ROOT/manifests/manifest-2026-10-08.txt ]]
[[ -f $ADS_STATE_ROOT/manifests/manifest-2026-10-09.txt ]]
[[ -f $ADS_STATE_ROOT/archives/source-a/2026-10-08.log.gz ]]
[[ -f $ADS_STATE_ROOT/archives/source-b/2026-10-09.log.gz ]]
ADS_TODAY=2026-10-10 bash "$project_dir/bin/ads-nightly.sh"

# Anche il verificatore isolato deve rifiutare un archivio esterno via link.
(
    export ADS_STATE_ROOT=$scratch/verify-link-state
    cp -a -- "$scratch/state" "$ADS_STATE_ROOT"
    mv -- "$ADS_STATE_ROOT/archives/source-a" "$scratch/verify-external"
    ln -s -- "$scratch/verify-external" "$ADS_STATE_ROOT/archives/source-a"
    expect_failure bash "$project_dir/bin/ads-verify.sh"
    grep -Fq 'directory archivio simbolica' "$scratch/output"
)

# Una rottura remota dal giorno corrente deve fermare la nuova chiusura.
(
    export ADS_STATE_ROOT=$scratch/historic-state
    cp -a -- "$scratch/state" "$ADS_STATE_ROOT"
    printf 'x' >>"$ADS_STATE_ROOT/manifests/manifest-2026-10-06.txt"
    expect_failure env ADS_TODAY=2026-10-11 bash "$project_dir/bin/ads-nightly.sh"
    grep -Fq 'catena storica non verificabile' "$scratch/output"
    [[ ! -e $ADS_STATE_ROOT/manifests/manifest-2026-10-10.txt ]]
)

# Un fermo oltre la finestra locale si arresta prima di chiudere giorni senza evidenza.
expect_failure env ADS_TODAY=2027-06-01 bash "$project_dir/bin/ads-nightly.sh"
grep -Fq 'oltre la finestra locale di 213' "$scratch/output"
[[ ! -e $ADS_STATE_ROOT/manifests/manifest-2027-05-31.txt ]]
[[ $(find "$ADS_STATE_ROOT/manifests" -maxdepth 1 -name 'manifest-*.txt' -type f | wc -l) -eq 4 ]]

# Il cambio dell'ora di ottobre non deve creare o saltare una giornata civile.
(
    export ADS_LOG_ROOT=$scratch/dst-logs
    export ADS_STATE_ROOT=$scratch/dst-state
    mkdir -p -- "$ADS_LOG_ROOT/source-a" "$ADS_STATE_ROOT"
    printf 'access\n' >"$ADS_LOG_ROOT/source-a/2026-10-24.log"
    ADS_TODAY=2026-10-25 bash "$project_dir/bin/ads-nightly.sh"
    printf 'access\n' >"$ADS_LOG_ROOT/source-a/2026-10-25.log"
    printf 'access\n' >"$ADS_LOG_ROOT/source-a/2026-10-26.log"
    ADS_TODAY=2026-10-27 bash "$project_dir/bin/ads-nightly.sh"
    bash "$project_dir/bin/ads-verify.sh"
    [[ -f $ADS_STATE_ROOT/manifests/manifest-2026-10-25.txt ]]
    [[ -f $ADS_STATE_ROOT/manifests/manifest-2026-10-26.txt ]]
)

# Senza GENESIS, un archivio di una giornata precedente non può sparire dal perimetro.
(
    export ADS_LOG_ROOT=$scratch/orphan-logs
    export ADS_STATE_ROOT=$scratch/orphan-state
    mkdir -p -- "$ADS_LOG_ROOT/source-a" "$ADS_STATE_ROOT/archives/source-a"
    printf 'access\n' >"$ADS_LOG_ROOT/source-a/2026-10-09.log"
    printf 'orphan\n' >"$ADS_STATE_ROOT/archives/source-a/2026-10-08.log.gz"
    expect_failure env ADS_TODAY=2026-10-10 bash "$project_dir/bin/ads-nightly.sh"
    grep -Fq 'archivio senza manifest precedente' "$scratch/output"
    [[ ! -e $ADS_STATE_ROOT/manifests/manifest-2026-10-09.txt ]]
)

# Un archivio di D-1 creato prima di un arresto viene riusato e verificato.
(
    export ADS_LOG_ROOT=$scratch/interrupted-logs
    export ADS_STATE_ROOT=$scratch/interrupted-state
    mkdir -p -- "$ADS_LOG_ROOT/source-a" "$ADS_STATE_ROOT/archives/source-a"
    printf 'access\n' >"$ADS_LOG_ROOT/source-a/2026-10-09.log"
    gzip -n -9 -c -- "$ADS_LOG_ROOT/source-a/2026-10-09.log" >"$ADS_STATE_ROOT/archives/source-a/2026-10-09.log.gz"
    ADS_TODAY=2026-10-10 bash "$project_dir/bin/ads-nightly.sh"
    bash "$project_dir/bin/ads-verify.sh" --date 2026-10-09
)

# Anche alterare il manifest precedente deve spezzare il legame del giorno seguente.
printf 'x' >>"$ADS_STATE_ROOT/manifests/manifest-2026-10-06.txt"
expect_failure bash "$project_dir/bin/ads-verify.sh"

# Il rapporto non può essere valido se il campione cambia durante la misura.
mkdir -p -- "$scratch/measure-case"
cp -- "$project_dir/bin/ads-measure-verify.py" "$scratch/measure-case/ads-measure-verify.py"
printf '%s\n' '#!/usr/bin/env bash' 'printf "private-marker" >&2' 'printf x >>"$ADS_LOG_ROOT/source-a/2026-10-07.log"' >"$scratch/measure-case/ads-verify.sh"
expect_failure python3 "$scratch/measure-case/ads-measure-verify.py" --log-root "$ADS_LOG_ROOT" --state-root "$ADS_STATE_ROOT"
python3 -c 'import json,sys; d=json.load(open(sys.argv[1],encoding="utf-8")); assert d["status"] == "dataset_changed" and "private-marker" not in open(sys.argv[1],encoding="utf-8").read()' "$scratch/output"
printf 'test-nightly: OK (recupero, 213 giorni, ora legale, idempotenza, alterazioni, link simbolici e manifest precedente)\n'
