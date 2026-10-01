#!/usr/bin/env bash
# Configurazione di base del collettore Debian 13 (handoff, sezione 2 punti 3-6 e sezione 3).
#
#   ads-bootstrap.sh [--prova] <albero-generato> <cartella-tls> <cartella-chiavi>
#
# <albero-generato> e' l'uscita di ads-render.py su config/collettore; <cartella-tls> contiene
# ca.pem, collector.pem e collector.key prodotti da ads-pki.sh; <cartella-chiavi> contiene una
# chiave pubblica SSH <utente>.pub per ogni amministratore elencato in etc/ads/amministratori
# (ADR-008: account personali, cosi' ogni accesso al collettore e' attribuibile). Si esegue come
# root dalla console di Proxmox, non da una sessione SSH perche' ricarica sshd, dopo
# l'installazione netinst e dopo aver montato scsi1 su /srv/ads con
# nodev,nosuid,noexec: se il montaggio non c'e' o manca un'opzione lo script si ferma.
# Con --prova stampa i comandi senza eseguirne nessuno e non richiede root.
#
# Ogni passo fallito ferma lo script (set -e); il ruleset nftables si controlla con nft -c
# prima di caricarlo, cosi' un errore di sintassi non lascia il collettore senza firewall, e
# sshd si ricarica solo dopo che ogni amministratore ha account e chiave, cosi' AllowGroups non
# chiude fuori nessuno. La password locale di ciascuno, che serve a sudo, si imposta a mano alla
# fine e il titolare la cambia con passwd: lo script non la conosce e non la genera.
set -euo pipefail

readonly PACKAGES=(rsyslog rsyslog-gnutls chrony nftables openssl curl python3-requests
    msmtp-mta cifs-utils unattended-upgrades qemu-guest-agent sudo openssh-server)
readonly CONFIG_FILES=(
    etc/nftables.conf
    etc/chrony/sources.d/inrim.sources
    etc/ssh/sshd_config.d/10-ads.conf
    etc/apt/apt.conf.d/52ads-unattended-upgrades
    etc/qemu/qemu-ga.conf
    etc/sudoers.d/ads-admin
    etc/ads/amministratori
    etc/rsyslog.d/10-ads.conf
)
readonly TLS_FILES=(ca.pem collector.pem collector.key)
readonly DATA_MOUNT=/srv/ads
readonly ADMIN_GROUP=ads-admin
# Fuso dell'Italia: l'orologio resta in UTC, il fuso decide come l'ora locale viene mostrata.
readonly TIMEZONE=Europe/Rome
readonly USER_NAME='^[a-z][a-z0-9-]{0,30}$'

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

# Legge etc/ads/amministratori: righe di commento con #, poi i nomi separati da virgole.
read_admins() {
    local file=$1
    grep -v '^[[:space:]]*#' "$file" | tr ',' '\n' | tr -d ' \t' | grep -v '^$' || true
}

check_admins() {
    local keys=$1 user count=0
    shift
    [[ -d "$keys" ]] || die "cartella delle chiavi assente: $keys"
    for user in "$@"; do
        [[ $user =~ $USER_NAME ]] || die "nome utente non valido: $user"
        [[ $user != root && $user != ads ]] || die "$user non puo' essere un amministratore"
        [[ -f "$keys/$user.pub" ]] || die "manca la chiave pubblica $keys/$user.pub"
        ssh-keygen -l -f "$keys/$user.pub" >/dev/null 2>&1 \
            || die "$keys/$user.pub non e' una chiave pubblica SSH valida"
        count=$((count + 1))
    done
    ((count > 0)) || die "nessun amministratore in etc/ads/amministratori"
}

install_admin() {
    local keys=$1 user=$2 home
    if ((DRY_RUN)) || ! id "$user" >/dev/null 2>&1; then
        run useradd --create-home --shell /bin/bash --groups "$ADMIN_GROUP" "$user"
    else
        run usermod --append --groups "$ADMIN_GROUP" "$user"
    fi
    home=${ROOT}/home/$user
    run install -d -o "$user" -g "$user" -m 0700 "$home/.ssh"
    run install -o "$user" -g "$user" -m 0600 "$keys/$user.pub" "$home/.ssh/authorized_keys"
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
    [[ $# -eq 3 ]] || die "uso: ads-bootstrap.sh [--prova] <albero-generato> <cartella-tls> <cartella-chiavi>"
    local tree=$1 tls=$2 keys=$3 f user
    local -a admins

    if ((!DRY_RUN)) && [[ $EUID -ne 0 ]]; then
        die "va eseguito come root (oppure con --prova)"
    fi
    check_inputs "$tree" "$tls"
    mapfile -t admins < <(read_admins "$tree/etc/ads/amministratori")
    check_admins "$keys" "${admins[@]}"
    check_data_mount

    run timedatectl set-timezone "$TIMEZONE"
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
    # I file dei log li scrive rsyslog come root; il gruppo ads li legge per i job notturni.
    run install -d -o root -g ads -m 0750 "${ROOT}${DATA_MOUNT}"

    # Amministratori non MSP: un account personale ciascuno, prima di toccare sshd (ADR-008).
    if ((DRY_RUN)) || ! getent group "$ADMIN_GROUP" >/dev/null; then
        run groupadd "$ADMIN_GROUP"
    fi
    for user in "${admins[@]}"; do
        install_admin "$keys" "$user"
    done

    for f in "${CONFIG_FILES[@]}"; do
        case $f in
        etc/sudoers.d/*) install_file "$tree/$f" "/$f" 0440 ;;
        *) install_file "$tree/$f" "/$f" 0644 ;;
        esac
    done
    run visudo -c -f "${ROOT}/etc/sudoers.d/ads-admin"
    install_file "$tls/ca.pem" /etc/rsyslog.d/tls/ca.pem 0644
    install_file "$tls/collector.pem" /etc/rsyslog.d/tls/collector.pem 0644
    install_file "$tls/collector.key" /etc/rsyslog.d/tls/collector.key 0600

    # chrony: solo INRIM, pool Debian commentato (forma della riga verificata su Debian 13 in container).
    run sed -i -E 's/^(pool[[:space:]].*)$/# \1  # disattivato da ads-bootstrap: solo INRIM/' \
        "${ROOT}/etc/chrony/chrony.conf"

    run nft -c -f "${ROOT}/etc/nftables.conf"
    run sshd -t
    run rsyslogd -N1 -f "${ROOT}/etc/rsyslog.conf"
    run systemctl enable --now nftables
    run systemctl restart chrony
    run systemctl restart rsyslog
    run systemctl reload ssh
    run systemctl restart qemu-guest-agent
    run systemctl enable --now unattended-upgrades

    echo "bootstrap completato; verifiche: chronyc sources, nft list ruleset, qemu-ga --dump-conf"
    # Niente 'chage -d 0': con SSH solo a chiave una password scaduta puo' bloccare il login.
    echo "resta a mano: per ogni amministratore 'sudo passwd <utente>' con una password temporanea,"
    echo "che lui cambia con 'passwd' al primo accesso: ${admins[*]}"
}

main "$@"
