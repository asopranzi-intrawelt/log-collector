#!/usr/bin/env bash
# Inspect a technical log archive; expire daily files only with an explicit policy.
set -euo pipefail

export TZ=Europe/Rome
export LC_ALL=C
readonly ROOT=${ADS_TECH_ROOT:?ADS_TECH_ROOT obbligatoria}
readonly LABEL=${ADS_TECH_LABEL:-ads-technical-retain}
readonly TODAY=${ADS_TODAY:-$(date +%F)}
readonly WARN_PCT=80
readonly EMPTY_OK=${ADS_TECH_EMPTY_OK:-0}

status() { printf '%s %s\n' "$LABEL" "$*" >&2; }
die() { status "status=error $*"; exit 1; }

[[ $LABEL =~ ^[a-z0-9-]+$ ]] || die 'etichetta non valida'
[[ $EMPTY_OK == 0 || $EMPTY_OK == 1 ]] || die 'politica archivio vuoto non valida'

mode=${1:-}
days=
case "$mode" in
    --inspect) [[ $# -eq 1 ]] || die 'uso: --inspect | (--dry-run|--apply) --days N' ;;
    --dry-run|--apply)
        [[ $# -eq 3 && $2 == --days ]] || die 'uso: --inspect | (--dry-run|--apply) --days N'
        days=$3
        [[ $days =~ ^[1-9][0-9]{0,3}$ ]] || die 'giorni non validi'
        ((10#$days <= 3650)) || die 'giorni oltre il limite'
        ;;
    *) die 'uso: --inspect | (--dry-run|--apply) --days N' ;;
esac
[[ $TODAY =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || die 'data corrente non valida'
[[ $(date -d "$TODAY" +%F 2>/dev/null) == "$TODAY" ]] || die 'data corrente impossibile'
[[ $ROOT == /* ]] || die 'radice non assoluta'
[[ ! -L $ROOT ]] || die 'radice simbolica non ammessa'
if [[ ! -d $ROOT ]]; then
    status 'status=warning result=no-root files=0 bytes=0'
    exit 2
fi

cutoff=
if [[ -n $days ]]; then
    cutoff=$(date -d "$TODAY - $((10#$days - 1)) days" +%F)
fi

shopt -s nullglob dotglob
expired=()
sources=0
files=0
bytes=0
expired_bytes=0
oldest=
newest=
kept_files=0
kept_bytes=0
kept_oldest=
kept_newest=
for source_dir in "$ROOT"/*; do
    [[ ! -L $source_dir ]] || die 'directory sorgente simbolica non ammessa'
    [[ -d $source_dir ]] || die 'voce non directory nella radice'
    source_name=${source_dir##*/}
    [[ $source_name =~ ^[0-9A-Fa-f:.]+$ ]] || die 'nome sorgente inatteso'
    ((sources+=1))
    for path in "$source_dir"/*; do
        [[ ! -L $path ]] || die 'log simbolico non ammesso'
        [[ -f $path ]] || die 'voce non regolare nella sorgente'
        name=${path##*/}
        [[ $name =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}\.log$ ]] || die 'nome log inatteso'
        day=${name%.log}
        [[ $(date -d "$day" +%F 2>/dev/null) == "$day" ]] || die 'data del log impossibile'
        [[ $(stat -c %h -- "$path") == 1 ]] || die 'hard link del log non ammesso'
        size=$(stat -c %s -- "$path") || die 'dimensione non leggibile'
        files=$((files + 1))
        bytes=$((bytes + size))
        [[ -z $oldest || $day < $oldest ]] && oldest=$day
        [[ -z $newest || $day > $newest ]] && newest=$day
        if [[ -n $cutoff && $day < $cutoff ]]; then
            expired+=("$path")
            expired_bytes=$((expired_bytes + size))
        else
            kept_files=$((kept_files + 1))
            kept_bytes=$((kept_bytes + size))
            [[ -z $kept_oldest || $day < $kept_oldest ]] && kept_oldest=$day
            [[ -z $kept_newest || $day > $kept_newest ]] && kept_newest=$day
        fi
    done
done

if [[ $mode == --dry-run ]]; then
    for path in "${expired[@]}"; do status "would-delete=$path"; done
elif [[ $mode == --apply ]]; then
    for path in "${expired[@]}"; do
        rm -- "$path" || die 'cancellazione fallita'
        status "deleted=$path"
    done
    files=$kept_files
    bytes=$kept_bytes
    oldest=$kept_oldest
    newest=$kept_newest
fi

read -r available_kib usage_pct < <(df -Pk -- "$ROOT" | awk 'NR == 2 {gsub(/%/, "", $5); print $4, $5}') || die 'utilizzo filesystem non leggibile'
[[ $available_kib =~ ^[0-9]+$ && $usage_pct =~ ^[0-9]+$ ]] || die 'utilizzo filesystem non leggibile'

result=ok
exit_code=0
if (((files == 0 && EMPTY_OK == 0) || usage_pct >= WARN_PCT)); then result=warning; exit_code=2; fi
status "status=$result mode=${mode#--} sources=$sources files=$files bytes=$bytes oldest=${oldest:-none} newest=${newest:-none} available_kib=$available_kib filesystem_used_pct=$usage_pct cutoff=${cutoff:-none} expired=${#expired[@]} expired_bytes=$expired_bytes"
exit "$exit_code"
