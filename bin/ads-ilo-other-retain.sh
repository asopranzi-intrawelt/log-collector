#!/usr/bin/env bash
# Retain daily non-AdS iLO files for 90 calendar days, including today.
# The rsyslog filename already rotates at midnight; this job only expires days.
set -euo pipefail

export TZ=Europe/Rome
export LC_ALL=C
readonly ROOT=${ADS_ILO_OTHER_ROOT:-/var/log/ads-ilo-other}
readonly TODAY=${ADS_TODAY:-$(date +%F)}
readonly DAYS=90

status() {
    printf 'ads-ilo-other-retain %s\n' "$*" >&2
}

die() {
    status "status=error $*"
    exit 1
}

[[ $# -eq 1 && ( $1 == --dry-run || $1 == --apply ) ]] || die 'uso: --dry-run | --apply'
mode=$1
[[ $TODAY =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || die 'data corrente non valida'
[[ $(date -d "$TODAY" +%F 2>/dev/null) == "$TODAY" ]] || die 'data corrente impossibile'
readonly CUTOFF=$(date -d "$TODAY - $((DAYS - 1)) days" +%F)

[[ ! -L $ROOT ]] || die 'radice simbolica non ammessa'
if [[ ! -d $ROOT ]]; then
    status "status=ok result=no-root cutoff=$CUTOFF"
    exit 0
fi

shopt -s nullglob
expired=()
for source_dir in "$ROOT"/*; do
    [[ ! -L $source_dir ]] || die 'directory sorgente simbolica non ammessa'
    [[ -d $source_dir ]] || continue
    source_name=${source_dir##*/}
    [[ $source_name =~ ^[0-9A-Fa-f:.]+$ ]] || die 'nome sorgente inatteso'
    for path in "$source_dir"/*.log; do
        [[ ! -L $path ]] || die 'log simbolico non ammesso'
        [[ -f $path ]] || die 'log non regolare'
        name=${path##*/}
        [[ $name =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}\.log$ ]] || die 'nome log inatteso'
        day=${name%.log}
        [[ $(date -d "$day" +%F 2>/dev/null) == "$day" ]] || die 'data del log impossibile'
        if [[ $day < $CUTOFF ]]; then
            expired+=("$path")
        fi
    done
done

if [[ $mode == --dry-run ]]; then
    for path in "${expired[@]}"; do
        status "would-delete=$path"
    done
    status "status=ok mode=dry-run cutoff=$CUTOFF expired=${#expired[@]}"
    exit 0
fi

for path in "${expired[@]}"; do
    rm -- "$path" || die 'cancellazione fallita'
done
usage=$(df -P -- "$ROOT" | awk 'NR == 2 {gsub(/%/, "", $5); print $5}')
[[ $usage =~ ^[0-9]+$ ]] || die 'utilizzo filesystem non leggibile'
if ((usage >= 80)); then
    status "status=warning mode=apply cutoff=$CUTOFF deleted=${#expired[@]} filesystem_used_pct=$usage"
else
    status "status=ok mode=apply cutoff=$CUTOFF deleted=${#expired[@]} filesystem_used_pct=$usage"
fi
