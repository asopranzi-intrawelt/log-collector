#!/usr/bin/env bash
# PKI minima per il TLS 6514 del collettore (handoff, sezione 3).
#
# Si esegue sulla postazione dell'amministratore non MSP, MAI sul collettore: la chiave della CA
# resta su quella postazione. Sul collettore vanno solo ca.pem, collector.pem e collector.key,
# in /etc/rsyslog.d/tls/, che ads-bootstrap.sh installa con la chiave in modalita' 0600.
#
#   ads-pki.sh ca <cartella>                  crea ca.key e ca.pem (10 anni)
#   ads-pki.sh server <cartella> <fqdn> <ip>  crea collector.key e collector.pem firmato dalla CA,
#                                             SAN = FQDN e IP del collettore, validita' 2 anni
#
# Nessun file esistente viene sovrascritto: un rinnovo si fa spostando prima i file vecchi, cosi'
# una CA non si rigenera mai per sbaglio invalidando la fiducia di tutte le sorgenti.
# Scelta: chiavi RSA 3072, per compatibilita' con GnuTLS di rsyslog sulle sorgenti Debian e
# Proxmox e con OpenSSL di Fluent Bit su Windows.
set -euo pipefail

readonly CA_DAYS=3650
readonly SERVER_DAYS=730
readonly KEY_BITS=3072

# Git Bash su Windows converte gli argomenti che iniziano con / in percorsi Windows, e il
# soggetto "/CN=..." arriverebbe a openssl come "C:/Program Files/Git/CN=...". Altrove e' inerte.
export MSYS2_ARG_CONV_EXCL="/CN="

die() {
    echo "errore: $*" >&2
    exit 1
}

usage() {
    sed -n '8,10p' "$0" | sed 's/^# \{0,1\}//' >&2
    exit 2
}

refuse_existing() {
    local f
    for f in "$@"; do
        [[ ! -e "$f" ]] || die "$f esiste gia': spostarlo prima di rigenerarlo"
    done
}

new_key() {
    local key=$1
    (umask 077 && openssl genpkey -algorithm RSA -pkeyopt "rsa_keygen_bits:${KEY_BITS}" -out "$key" 2>/dev/null)
    chmod 600 "$key"
}

cmd_ca() {
    local dir=$1
    mkdir -p "$dir"
    refuse_existing "$dir/ca.key" "$dir/ca.pem"
    new_key "$dir/ca.key"
    openssl req -new -x509 -key "$dir/ca.key" -out "$dir/ca.pem" -days "$CA_DAYS" -sha256 \
        -subj "/CN=ADS Collector CA" \
        -addext "basicConstraints=critical,CA:TRUE,pathlen:0" \
        -addext "keyUsage=critical,keyCertSign,cRLSign" \
        -addext "subjectKeyIdentifier=hash"
    echo "CA creata in $dir: conservare ca.key su questa postazione, copiare solo ca.pem"
}

valid_fqdn() {
    [[ $1 =~ ^([A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$ ]]
}

valid_ipv4() {
    local IFS=. octet
    local -a parts
    [[ $1 =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]] || return 1
    read -r -a parts <<<"$1"
    for octet in "${parts[@]}"; do
        ((10#$octet <= 255)) || return 1
    done
}

cmd_server() {
    local dir=$1 fqdn=$2 ip=$3
    valid_fqdn "$fqdn" || die "FQDN non valido: $fqdn"
    valid_ipv4 "$ip" || die "IPv4 non valido: $ip"
    [[ -f "$dir/ca.key" && -f "$dir/ca.pem" ]] || die "CA assente in $dir: eseguire prima 'ca'"
    refuse_existing "$dir/collector.key" "$dir/collector.pem"

    local ext
    ext=$(mktemp)
    # I valori si espandono ora: all'uscita dello script le variabili locali non esistono piu'.
    # shellcheck disable=SC2064
    trap "rm -f $(printf '%q %q' "$ext" "$dir/collector.csr")" EXIT
    cat >"$ext" <<EOF
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=DNS:${fqdn},IP:${ip}
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid
EOF
    new_key "$dir/collector.key"
    openssl req -new -key "$dir/collector.key" -out "$dir/collector.csr" -subj "/CN=${fqdn}"
    openssl x509 -req -in "$dir/collector.csr" -CA "$dir/ca.pem" -CAkey "$dir/ca.key" \
        -CAcreateserial -out "$dir/collector.pem" -days "$SERVER_DAYS" -sha256 -extfile "$ext" \
        2>/dev/null
    openssl verify -CAfile "$dir/ca.pem" "$dir/collector.pem" >/dev/null \
        || die "il certificato emesso non si verifica contro la CA"
    echo "certificato del collettore creato: $dir/collector.pem, scadenza $(openssl x509 -in "$dir/collector.pem" -noout -enddate | cut -d= -f2)"
    echo "rinnovo a calendario prima della scadenza; copiare sul collettore ca.pem, collector.pem, collector.key"
}

main() {
    [[ $# -ge 1 ]] || usage
    command -v openssl >/dev/null || die "openssl non trovato"
    case $1 in
    ca)
        [[ $# -eq 2 ]] || usage
        cmd_ca "$2"
        ;;
    server)
        [[ $# -eq 4 ]] || usage
        cmd_server "$2" "$3" "$4"
        ;;
    *) usage ;;
    esac
}

main "$@"
