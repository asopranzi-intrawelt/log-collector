#!/usr/bin/env bash
# Verifica della configurazione generata contro Debian 13 vero, in un container usa e getta.
#
#   tests/debian13/verifica-config.sh              dalla radice del repository, con Docker attivo
#
# Genera l'albero con ads-render.py dalla fixture (valori di documentazione, mai reali) e lo
# controlla dentro debian:trixie con gli strumenti della distribuzione: nft -c sul ruleset,
# sshd -T sui valori effettivi dopo il drop-in, qemu-ga --dump-conf sull'elenco degli RPC,
# apt-config e unattended-upgrade --dry-run sulle origini, e la forma delle righe pool di
# chrony.conf che ads-bootstrap.sh commenta. Risponde a voci [Non verificato] dell'handoff sulla
# distribuzione, non sulla VM: Secure Boot, netinst e guest agent visto dall'host restano da
# collaudare sul Proxmox. Non tocca host reali; serve la rete per scaricare immagine e pacchetti.
set -euo pipefail

readonly IMAGE=debian:trixie
root=$(cd "$(dirname "$0")/../.." && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# Primo interprete che risponde davvero: su Windows python3 puo' essere lo stub dello Store.
py=""
for candidate in python3 python; do
    if "$candidate" -c 'import sys' >/dev/null 2>&1; then
        py=$candidate
        break
    fi
done
"$py" "$root/bin/ads-render.py" --parametri "$root/tests/fixtures/parametri-completi.yaml" \
    --sorgente "$root/config/collettore" --destinazione "$work/tree" >/dev/null

# Su Git Bash il percorso va passato a Docker in forma Windows.
mount_src=$work/tree
if command -v cygpath >/dev/null; then
    mount_src=$(cygpath -w "$work/tree")
fi

MSYS_NO_PATHCONV=1 docker run --rm --cap-add NET_ADMIN -v "$mount_src:/tree:ro" "$IMAGE" bash -c '
set -euo pipefail
fail() { echo "FALLITO: $*"; exit 1; }
ok() { echo "ok  $*"; }

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends nftables openssh-server chrony \
    unattended-upgrades qemu-guest-agent rsyslog rsyslog-gnutls sudo openssl iproute2 >/dev/null
ok "pacchetti installabili su $(. /etc/os-release && echo "$PRETTY_NAME")"

nft -c -f /tree/etc/nftables.conf || fail "nft -c rifiuta il ruleset"
ok "nftables: ruleset valido per nft $(nft --version | cut -d" " -f2)"

install -m 0644 /tree/etc/ssh/sshd_config.d/10-ads.conf /etc/ssh/sshd_config.d/
groupadd ads-admin
admins=$(grep -v "^#" /tree/etc/ads/amministratori | tr "," " ")
for u in $admins; do useradd -m -G ads-admin "$u"; done
mkdir -p /run/sshd
ssh-keygen -A >/dev/null
sshd -t || fail "sshd -t rifiuta la configurazione"
eff=$(sshd -T)
grep -qx "permitrootlogin no" <<<"$eff" || fail "PermitRootLogin effettivo non e no"
grep -qx "passwordauthentication no" <<<"$eff" || fail "PasswordAuthentication effettivo non e no"
grep -qx "kbdinteractiveauthentication no" <<<"$eff" || fail "KbdInteractiveAuthentication non e no"
grep -qx "allowgroups ads-admin" <<<"$eff" || fail "AllowGroups effettivo non e ads-admin"
grep -q "^allowusers" <<<"$eff" && fail "AllowUsers presente: restringerebbe oltre il gruppo"
for u in $admins; do
    sshd -T -C "user=$u,host=h,addr=192.0.2.9" | grep -qx "allowgroups ads-admin" || fail "sshd -T per $u"
done
grep -q "^Include /etc/ssh/sshd_config.d/\*.conf" /etc/ssh/sshd_config || fail "sshd_config non include il drop-in"
ok "sshd: il drop-in prevale, valori effettivi verificati con sshd -T"

install -m 0440 /tree/etc/sudoers.d/ads-admin /etc/sudoers.d/ads-admin
visudo -c -f /etc/sudoers.d/ads-admin >/dev/null || fail "visudo rifiuta sudoers.d/ads-admin"
for u in $admins; do
    sudo -l -U "$u" | grep -q "(ALL : ALL) ALL" || fail "$u non ha i privilegi sudo attesi"
done
useradd --system --shell /usr/sbin/nologin ads
sudo -l -U ads | grep -q "(ALL" && fail "l utente di servizio ha sudo"
ok "sudo: file valido, privilegi a ogni amministratore dell elenco ($admins)"

install -m 0644 /tree/etc/qemu/qemu-ga.conf /etc/qemu/qemu-ga.conf
dump=$(qemu-ga --dump-conf 2>&1) || fail "qemu-ga --dump-conf: $dump"
grep -q "^allow-rpcs=.*guest-ping" <<<"$dump" || fail "qemu-ga non legge allow-rpcs da /etc/qemu/qemu-ga.conf"
for rpc in guest-exec guest-file-open guest-set-user-password guest-ssh-add-authorized-keys; do
    grep -q "^allow-rpcs=.*\\b$rpc\\b" <<<"$dump" && fail "$rpc risulta ammesso"
done
ok "qemu-ga: allow-rpcs letto dal file di default, RPC pericolosi esclusi"

install -m 0644 /tree/etc/apt/apt.conf.d/52ads-unattended-upgrades /etc/apt/apt.conf.d/
origins=$(apt-config dump | grep "^Unattended-Upgrade::Origins-Pattern::")
echo "$origins" | grep -qv "Debian-Security" && fail "origine non di sicurezza ancora attiva: $origins"
[ "$(echo "$origins" | wc -l)" -eq 2 ] || fail "attese 2 origini, trovate: $origins"
apt-config dump | grep -qx "Unattended-Upgrade::Automatic-Reboot \"false\";" || fail "riavvio automatico non disattivato"
ua=$(unattended-upgrade --dry-run --debug 2>&1 || true)
grep -q "Allowed origins are:" <<<"$ua" || fail "unattended-upgrade non riporta le origini: $ua"
grep "Allowed origins are:" <<<"$ua" | grep -qi "label=Debian," && fail "origini ammesse oltre la sicurezza"
ok "unattended-upgrades: solo origini di sicurezza, nessun riavvio automatico"

grep -q "^sourcedir /etc/chrony/sources.d" /etc/chrony/chrony.conf || fail "chrony.conf non legge sources.d"
pools=$(grep -cE "^pool[[:space:]]" /etc/chrony/chrony.conf || true)
[ "$pools" -ge 1 ] || fail "nessuna riga pool in chrony.conf: il sed di ads-bootstrap non ha niente da commentare"
sed -i -E "s/^(pool[[:space:]].*)$/# \1  # disattivato da ads-bootstrap: solo INRIM/" /etc/chrony/chrony.conf
grep -qE "^pool[[:space:]]" /etc/chrony/chrony.conf && fail "righe pool rimaste attive"
install -m 0644 /tree/etc/chrony/sources.d/inrim.sources /etc/chrony/sources.d/
chronyd -p -f /etc/chrony/chrony.conf >/dev/null || fail "chronyd -p rifiuta la configurazione"
ok "chrony: $pools righe pool commentate, sources.d letto, configurazione accettata"

# rsyslog: ricezione UDP e TLS, rifiuto del TCP in chiaro sulla 6514, accessi locali nel ruleset
# ads e nient altro. Certificato di prova sul solo 127.0.0.1, valido un giorno.
install -m 0644 /tree/etc/rsyslog.d/10-ads.conf /etc/rsyslog.d/
mkdir -p /etc/rsyslog.d/tls /srv/ads
openssl req -x509 -newkey rsa:2048 -nodes -days 1 -subj "/CN=prova" -addext "subjectAltName=IP:127.0.0.1" \
    -keyout /etc/rsyslog.d/tls/collector.key -out /etc/rsyslog.d/tls/collector.pem 2>/dev/null
cp /etc/rsyslog.d/tls/collector.pem /etc/rsyslog.d/tls/ca.pem
chmod 0600 /etc/rsyslog.d/tls/collector.key
chown root:ads /srv/ads && chmod 0750 /srv/ads
rsyslogd -N1 >/dev/null 2>&1 || { rsyslogd -N1; fail "rsyslogd -N1 rifiuta la configurazione"; }
rsyslogd -iNONE
for i in 1 2 3 4 5 6 7 8 9 10; do [ -S /dev/log ] && break; sleep 0.5; done
sleep 1
logger -n 127.0.0.1 -P 514 -d -t prova-udp "messaggio udp"
logger -n 127.0.0.1 -P 514 -d --rfc3164 -t prova-3164 "messaggio 3164"
printf "<13>Oct  1 12:00:00 sorgente-tls prova-tls: messaggio tls\n" \
    | timeout 5 openssl s_client -connect 127.0.0.1:6514 -quiet -CAfile /etc/rsyslog.d/tls/ca.pem >/dev/null 2>&1 || true
printf "<13>Oct  1 12:00:00 sorgente-tcp prova-tcp: messaggio in chiaro\n" > /dev/tcp/127.0.0.1/6514 || true
# Nomi dei programmi presi dai log reali del collettore (OpenSSH 10.0 su Debian 13), non ipotizzati:
# una prova che genera il messaggio con lo stesso nome che il codice si aspetta non misura nulla.
logger -t sshd-session "Accepted publickey for admuno from 192.0.2.9 port 50000 ssh2: ED25519 SHA256:prova"
logger -t sshd-auth "Invalid user prova from 192.0.2.9 port 50001"
logger -t sudo "admuno : TTY=pts/1 ; PWD=/home/admuno ; USER=root ; COMMAND=/usr/bin/id"
logger -t cron "messaggio estraneo agli accessi"
sleep 2
f=/srv/ads/127.0.0.1/$(date +%Y-%m-%d).log
[ -f "$f" ] || { ls -R /srv/ads; fail "file del giorno assente: $f"; }
grep -q "prova-udp messaggio udp" "$f" || { cat "$f"; fail "riga UDP RFC 5424 assente o con tag e messaggio fusi"; }
grep -q "prova-3164: messaggio 3164" "$f" || { cat "$f"; fail "riga UDP RFC 3164 assente"; }
grep -q "prova-udpmessaggio" "$f" && fail "tag e messaggio fusi"
grep -q "sorgente-tls prova-tls: messaggio tls" "$f" || fail "riga TLS assente"
grep -q "messaggio in chiaro" "$f" && fail "TCP in chiaro accettato sulla porta TLS"
grep -q "sshd-session: Accepted publickey for admuno" "$f" || fail "login sshd-session assente dal ruleset ads"
grep -q "sshd-auth: Invalid user prova" "$f" || fail "tentativo sshd-auth assente dal ruleset ads"
grep -q "sudo: admuno : TTY=pts/1" "$f" || fail "sudo assente dal ruleset ads"
grep -q "messaggio estraneo" "$f" && fail "messaggio locale non di accesso finito nel ruleset ads"
rfc="[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.]+[+-][0-9]{2}:[0-9]{2}"
bad=$(grep -cvE "^$rfc 127\.0\.0\.1 $rfc [^ ]+ [^ ]+" "$f" || true)
[ "$bad" -eq 0 ] || { cat "$f"; fail "$bad righe non rispettano i cinque campi di AdsLine"; }
[ "$(stat -c "%U:%G %a" "$f")" = "root:ads 640" ] || fail "permessi del file: $(stat -c "%U:%G %a" "$f")"
[ "$(stat -c "%U:%G %a" "$(dirname "$f")")" = "root:ads 750" ] || fail "permessi della cartella: $(stat -c "%U:%G %a" "$(dirname "$f")")"
ok "rsyslog: UDP (RFC 5424 e 3164) e TLS ricevuti con tag e messaggio separati, TCP in chiaro scartato, accessi sshd-session, sshd-auth e sudo nel ruleset ads, $(wc -l < "$f") righe AdsLine, permessi root:ads"

echo "tutte le verifiche superate"
'
