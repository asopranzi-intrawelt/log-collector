#!/usr/bin/env bash
# Chiude D-1 in un archivio locale e concatena i manifest. TSA e WORM sono fasi successive.
set -euo pipefail

export TZ=Europe/Rome
readonly LOG_ROOT=${ADS_LOG_ROOT:-/srv/ads}
readonly STATE_ROOT=${ADS_STATE_ROOT:-/var/lib/ads}
readonly ARCHIVE_ROOT=$STATE_ROOT/archives
readonly MANIFEST_ROOT=$STATE_ROOT/manifests
readonly TODAY=${ADS_TODAY:-$(date +%F)}
readonly SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

log_status() {
    local now
    now=$(date --iso-8601=seconds)
    printf '%s 127.0.0.1 %s ads-nightly %s\n' "$now" "$now" "$*" >&2
}

die() {
    log_status "status=error $*"
    exit 1
}

valid_day() {
    [[ $1 =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] &&
        [[ $(date -d "$1" +%F 2>/dev/null) == "$1" ]]
}

valid_source() {
    [[ $1 =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ && $1 != *..* ]]
}

hash_file() {
    local result
    result=$(sha256sum -- "$1") || die 'calcolo SHA-256 fallito'
    printf '%s' "${result%% *}"
}

[[ $# -eq 0 ]] || die 'nessun argomento previsto: il job lavora solo su D-1'
valid_day "$TODAY" || die 'data corrente non valida'
readonly DAY=$(date -d "$TODAY - 1 day" +%F)
readonly PREVIOUS_DAY=$(date -d "$DAY - 1 day" +%F)
[[ -d $LOG_ROOT ]] || die 'radice dei log assente'
mkdir -p -- "$ARCHIVE_ROOT" "$MANIFEST_ROOT"
exec 9>"$STATE_ROOT/nightly.lock"
flock -n 9 || die 'un altro job notturno e in corso'

shopt -s nullglob
manifests=("$MANIFEST_ROOT"/manifest-????-??-??.txt)
latest=''
if ((${#manifests[@]})); then
    latest=$(basename -- "${manifests[-1]}")
    latest=${latest#manifest-}
    latest=${latest%.txt}
fi

manifest=$MANIFEST_ROOT/manifest-$DAY.txt
if [[ -f $manifest ]]; then
    [[ $latest == "$DAY" ]] || die 'esiste un manifest successivo a D-1'
    bash "$SCRIPT_DIR/ads-verify.sh" --date "$DAY" || die 'verifica del manifest esistente fallita'
    log_status "status=ok day=$DAY result=already-closed"
    exit 0
fi
if [[ -n $latest && $latest != "$PREVIOUS_DAY" ]]; then
    die "catena discontinua: ultimo manifest $latest, atteso $PREVIOUS_DAY"
fi

archives=()
for raw in "$LOG_ROOT"/*/"$DAY.log"; do
    source=$(basename -- "$(dirname -- "$raw")")
    valid_source "$source" || die 'nome della sorgente non valido'
    [[ ! -L $raw && ! -L $(dirname -- "$raw") ]] || die 'sorgente simbolica non ammessa'
    destination=$ARCHIVE_ROOT/$source
    mkdir -p -- "$destination"
    archive=$destination/$DAY.log.gz
    [[ ! -L $archive ]] || die 'archivio simbolico non ammesso'
    if [[ -f $archive ]]; then
        gzip -n -9 -c -- "$raw" | cmp -s - "$archive" || die "archivio esistente diverso da $source/$DAY.log"
    else
        temporary=$(mktemp -- "$destination/.$DAY.XXXXXX")
        if ! gzip -n -9 -c -- "$raw" >"$temporary"; then
            rm -f -- "$temporary"
            die "compressione fallita per $source/$DAY.log"
        fi
        if ! gzip -dc -- "$temporary" | cmp -s - "$raw"; then
            rm -f -- "$temporary"
            die "il log $source/$DAY.log e cambiato durante la compressione"
        fi
        mv -- "$temporary" "$archive"
    fi
    archives+=("$archive")
done

# Un archivio rimasto da una corsa interrotta senza il log di origine non e verificabile.
for archive in "$ARCHIVE_ROOT"/*/"$DAY.log.gz"; do
    source=$(basename -- "$(dirname -- "$archive")")
    valid_source "$source" || die 'nome della sorgente archiviata non valido'
    [[ -f $LOG_ROOT/$source/$DAY.log ]] || die "manca il log di origine di $source/$DAY.log.gz"
done

previous=$MANIFEST_ROOT/manifest-$PREVIOUS_DAY.txt
prev_hash=GENESIS
if [[ -n $latest ]]; then
    [[ -f $previous ]] || die 'manifest precedente assente'
    bash "$SCRIPT_DIR/ads-verify.sh" --date "$PREVIOUS_DAY" || die 'manifest precedente non verificabile'
    prev_hash=$(hash_file "$previous")
fi

temporary=$(mktemp -- "$MANIFEST_ROOT/.manifest-$DAY.XXXXXX")
{
    printf 'prev: %s\n' "$prev_hash"
    for archive in "${archives[@]}"; do
        source=$(basename -- "$(dirname -- "$archive")")
        printf '%s  archives/%s/%s.log.gz\n' "$(hash_file "$archive")" "$source" "$DAY"
    done
} >"$temporary"
mv -- "$temporary" "$manifest"
bash "$SCRIPT_DIR/ads-verify.sh" --date "$DAY" || die 'verifica del nuovo manifest fallita'
log_status "status=ok day=$DAY archives=${#archives[@]}"
