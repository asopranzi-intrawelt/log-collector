#!/usr/bin/env bash
# Configurazione di base del collettore Debian 13 (handoff, sezione 2 punti 3-6 e sezione 3).
#
#   ads-bootstrap.sh [--prova] <albero-generato> <cartella-tls>
#
# <albero-generato> e' l'uscita di ads-render.py su config/collettore; <cartella-tls> contiene
# ca.pem, collector.pem e collector.key prodotti da ads-pki.sh. Si esegue come root sul
# collettore, dopo l'installazione netinst e dopo aver montato scsi1 su /srv/ads con
# nodev,nosuid,noexec: se il montaggio non c'e' o manca un'opzione lo script si ferma.
# Con --prova stampa i comandi senza eseguirne nessuno e non richiede root.
#
# Ogni passo fallito ferma lo script (set -e); il ruleset nftables si controlla con nft -c
# prima di caricarlo, cosi' un errore di sintassi non lascia il collettore senza firewall.
set -euo pipefail

readonly PACKAGES=(rsyslog rsyslog-gnutls chrony nftables openssl curl python3-requests
    msmtp-mta cifs-utils unattended-upgrades qemu-guest-agent)
readonly CONFIG_FILES=(
    etc/nftables.conf
    etc/chrony/sources.d/inrim.sources
    etc/ssh/sshd_config.d/10-ads.conf
    etc/apt/apt.conf.d/52ads-unattended-upgrades
    etc/qemu/qemu-ga.conf
)
readonly TLS_FILES=(ca.pem collector.pem collector.key)
readonly DATA_MOUNT=/srv/ads

DRY_RUN=0
ROOT=${ADS_ROOT:-}

die() {
    echo "errore: $*" >&2
    exit 1
}

# Esegue un comando, oppure in prova lo stampa senza eseguirlo.
run() {
    if ((DRY_RUN)); then
        printf '+'
        printf ' %q' "$@"
        printf '\n'
    else
        "$@"
    fi
}

check_inputs() {
    local tree=$1 tls=$2 f
    [[ -d "$tree" ]] || die "albero generato assente: $tree"
    [[ -d "$tls" ]] || die "cartella TLS assente: $tls"
    for f in "${CONFIG_FILES[@]}"; do
        [[ -f "$tree/$f" ]] || die "manca $f in $tree: rigenerarlo con ads-render.py"
    done
    if grep -q '{{' "$tree/etc/nftables.conf"; then
        die "$tree/etc/nftables.conf contiene segnaposto non sostituiti"
    fi
    for f in "${TLS_FILES[@]}"; do
        [[ -f "$tls/$f" ]] || die "manca $f in $tls: generarlo con ads-pki.sh"
    done
    [[ ! -e "$tls/ca.key" ]] || die "$tls contiene ca.key: la chiave della CA non va sul collettore"
}

check_data_mount() {
    local opts opt
    if ((DRY_RUN)); then
        echo "# prova: controllo del montaggio di $DATA_MOUNT saltato"
        return
    fi
    opts=$(findmnt -n -o OPTIONS --mountpoint "$DATA_MOUNT" 2>/dev/null) \
        || die "$DATA_MOUNT non e' un punto di montaggio: montare scsi1 prima (handoff, sez. 2 punto 1)"
    for opt in nodev nosuid noexec; do
        [[ ",$opts," == *",$opt,"* ]] || die "$DATA_MOUNT montato senza $opt"
    done
}

install_file() {
    local src=$1 dest=$2 mode=$3
    run install -D -o root -g root -m "$mode" "$src" "${ROOT}${dest}"
}

main() {
    if [[ ${1:-} == --prova ]]; then
        DRY_RUN=1
        shift
    fi
    [[ $# -eq 2 ]] || die "uso: ads-bootstrap.sh [--prova] <albero-generato> <cartella-tls>"
    local tree=$1 tls=$2 f

    if ((!DRY_RUN)) && [[ $EUID -ne 0 ]]; then
        die "va eseguito come root (oppure con --prova)"
    fi
    check_inputs "$tree" "$tls"
    check_data_mount

    run apt-get update
    run env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${PACKAGES[@]}"

    # Utente di servizio e cartelle (handoff, sezione 4): gli script girano come ads, non root.
    if ((DRY_RUN)) || ! id ads >/dev/null 2>&1; then
        run useradd --system --home-dir /var/lib/ads --shell /usr/sbin/nologin ads
    fi
    run install -d -o root -g root -m 0755 "${ROOT}/opt/ads/bin"
    run install -d -o root -g ads -m 0750 "${ROOT}/etc/ads"
    run install -d -o ads -g ads -m 0700 "${ROOT}/etc/ads/secrets"
    run install -d -o ads -g ads -m 0750 "${ROOT}/var/lib/ads"
    run install -d -o root -g root -m 0755 "${ROOT}${DATA_MOUNT}"

    for f in "${CONFIG_FILES[@]}"; do
        install_file "$tree/$f" "/$f" 0644
    done
    install_file "$tls/ca.pem" /etc/rsyslog.d/tls/ca.pem 0644
    install_file "$tls/collector.pem" /etc/rsyslog.d/tls/collector.pem 0644
    install_file "$tls/collector.key" /etc/rsyslog.d/tls/collector.key 0600

    # chrony: solo INRIM, pool Debian commentato. [Non verificato] forma della riga su Debian 13.
    run sed -i -E 's/^(pool[[:space:]].*)$/# \1  # disattivato da ads-bootstrap: solo INRIM/' \
        "${ROOT}/etc/chrony/chrony.conf"

    run nft -c -f "${ROOT}/etc/nftables.conf"
    run sshd -t
    run systemctl enable --now nftables
    run systemctl restart chrony
    run systemctl reload ssh
    run systemctl restart qemu-guest-agent
    run systemctl enable --now unattended-upgrades

    echo "bootstrap completato; verifiche: chronyc sources, nft list ruleset, qemu-ga --dump-conf"
}

main "$@"
