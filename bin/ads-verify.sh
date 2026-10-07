#!/usr/bin/env bash
# Ricalcola hash e legami dei manifest locali; la prova esterna richiedera TSA e WORM.
set -euo pipefail

readonly LOG_ROOT=${ADS_LOG_ROOT:-/srv/ads}
readonly STATE_ROOT=${ADS_STATE_ROOT:-/var/lib/ads}
readonly ARCHIVE_ROOT=$STATE_ROOT/archives
readonly MANIFEST_ROOT=$STATE_ROOT/manifests

die() {
    printf 'ads-verify: errore: %s\n' "$*" >&2
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

verify_day() {
    local day=$1 previous_day=$2 manifest=$MANIFEST_ROOT/manifest-$1.txt
    local previous=$MANIFEST_ROOT/manifest-$2.txt expected header line digest
    local source archive raw actual i
    local -a lines=()
    local -A seen=()
    [[ -f $manifest && ! -L $manifest ]] || die "manifest assente o simbolico: $day"
    if [[ -f $previous ]]; then
        expected=$(hash_file "$previous")
    else
        expected=GENESIS
        local old
        for old in "$MANIFEST_ROOT"/manifest-????-??-??.txt; do
            [[ $old == "$manifest" || $old > "$manifest" ]] || die "manca il manifest precedente a $day"
        done
    fi
    IFS= read -r header <"$manifest" || die "manifest vuoto: $day"
    [[ $header == "prev: $expected" ]] || die "legame prev errato: $day"

    mapfile -t lines <"$manifest"
    for ((i = 1; i < ${#lines[@]}; i++)); do
        line=${lines[$i]}
        [[ $line =~ ^([0-9a-f]{64})[[:space:]][[:space:]]archives/([A-Za-z0-9._-]+)/([0-9]{4}-[0-9]{2}-[0-9]{2})\.log\.gz$ ]] || die "riga del manifest non valida: $day"
        digest=${BASH_REMATCH[1]}
        source=${BASH_REMATCH[2]}
        [[ ${BASH_REMATCH[3]} == "$day" ]] || die "data dell'archivio inattesa: $day"
        valid_source "$source" || die "nome della sorgente non valido: $day"
        [[ -z ${seen[$source]+x} ]] || die "sorgente duplicata nel manifest: $source"
        seen[$source]=1
        archive=$ARCHIVE_ROOT/$source/$day.log.gz
        raw=$LOG_ROOT/$source/$day.log
        [[ -f $archive && ! -L $archive ]] || die "archivio assente o simbolico: $source/$day"
        [[ -f $raw && ! -L $raw ]] || die "log di origine assente o simbolico: $source/$day"
        actual=$(hash_file "$archive")
        [[ $actual == "$digest" ]] || die "hash dell'archivio errato: $source/$day"
        gzip -dc -- "$archive" | cmp -s - "$raw" || die "log di origine diverso dall'archivio: $source/$day"
    done

    shopt -s nullglob
    for archive in "$ARCHIVE_ROOT"/*/"$day.log.gz"; do
        source=$(basename -- "$(dirname -- "$archive")")
        [[ -n ${seen[$source]+x} ]] || die "archivio fuori dal manifest: $source/$day"
    done
    for raw in "$LOG_ROOT"/*/"$day.log"; do
        source=$(basename -- "$(dirname -- "$raw")")
        [[ -n ${seen[$source]+x} ]] || die "log non archiviato: $source/$day"
    done
}

[[ -d $MANIFEST_ROOT ]] || die 'cartella manifest assente'
if (($#)); then
    [[ $# -eq 2 && $1 == --date ]] || die 'uso: ads-verify.sh [--date AAAA-MM-GG]'
    valid_day "$2" || die 'data non valida'
    day=$2
    previous_day=$(date -d "$day - 1 day" +%F)
    verify_day "$day" "$previous_day"
    printf 'ads-verify: ok day=%s\n' "$day"
    exit 0
fi

shopt -s nullglob
manifests=("$MANIFEST_ROOT"/manifest-????-??-??.txt)
((${#manifests[@]})) || die 'nessun manifest da verificare'
previous_day=''
for manifest in "${manifests[@]}"; do
    day=$(basename -- "$manifest")
    day=${day#manifest-}
    day=${day%.txt}
    valid_day "$day" || die "nome manifest non valido: $manifest"
    if [[ -n $previous_day ]]; then
        [[ $(date -d "$previous_day + 1 day" +%F) == "$day" ]] || die "giorno mancante dopo $previous_day"
    fi
    predecessor=$(date -d "$day - 1 day" +%F)
    verify_day "$day" "$predecessor"
    previous_day=$day
done
printf 'ads-verify: ok manifests=%s last=%s\n' "${#manifests[@]}" "$previous_day"
