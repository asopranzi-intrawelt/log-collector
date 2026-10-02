#!/usr/bin/env bash
# Verifica dell'invio dall'host Proxmox al collettore, in un container usa e getta.
#
#   tests/debian12/verifica-sorgente-proxmox.sh      dalla radice del repository, con Docker attivo
#
# L'host e' PVE 8 su Debian 12, quindi la prova gira in debian:bookworm con il suo rsyslog. Nello
# stesso container girano due rsyslog: uno con la configurazione del collettore (10-ads.conf),
# l'altro con quella dell'host (90-ads.conf generato da config/proxmox-host), che invia in TLS con
# verifica del certificato per nome. Certificati emessi da bin/ads-pki.sh, cioe' dalla PKI vera.
# Le righe iniettate sono quelle lette sull'host il 2026-10-01, con indirizzi di documentazione al
# posto di quelli veri: una prova scritta a partire da cio' che il codice si aspetta non misura
# nulla (docs/runbook-componente-2.md). Un terzo rsyslog con un nome permesso sbagliato non deve
# consegnare nulla.
set -euo pipefail

readonly IMAGE=debian:bookworm
root=$(cd "$(dirname "$0")/../.." && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

py=""
for candidate in python3 python; do
    if "$candidate" -c 'import sys' >/dev/null 2>&1; then
        py=$candidate
        break
    fi
done

# Parametri di prova: la fixture, con il collettore su 127.0.0.1 perche' tutto gira nel container.
sed 's/^  ip: "192.0.2.50"/  ip: "127.0.0.1"/' "$root/tests/fixtures/parametri-completi.yaml" >"$work/parametri.yaml"
"$py" "$root/bin/ads-render.py" --parametri "$work/parametri.yaml" \
    --sorgente "$root/config/collettore" --destinazione "$work/collettore" >/dev/null
"$py" "$root/bin/ads-render.py" --parametri "$work/parametri.yaml" \
    --sorgente "$root/config/proxmox-host" --destinazione "$work/host" >/dev/null
cp "$root/bin/ads-pki.sh" "$work/ads-pki.sh"

# Righe reali dell'access log di pveproxy, in file a parte per non doverle quotare nel container.
cat >"$work/access-storico.log" <<'EOF'
::ffff:192.0.2.73 - - [30/09/2026:09:00:00 +0200] "POST /api2/extjs/access/ticket HTTP/1.1" 200 763 RIGA-STORICA
EOF
cat >"$work/access-nuovo.log" <<'EOF'
::ffff:192.0.2.73 - root@pam [01/10/2026:16:31:54 +0200] "GET /api2/json/cluster/resources HTTP/1.1" 200 1781
::ffff:192.0.2.73 - - [01/10/2026:16:31:31 +0200] "POST /api2/extjs/access/ticket HTTP/1.1" 200 763
EOF
printf "%s\n" "<root@pam> successful auth for user 'root@pam'" >"$work/pvedaemon-auth.txt"

mount_src=$work
if command -v cygpath >/dev/null; then
    mount_src=$(cygpath -w "$work")
fi

MSYS_NO_PATHCONV=1 docker run --rm -v "$mount_src:/prova:ro" "$IMAGE" bash -c '
set -euo pipefail
fail() { echo "FALLITO: $*"; exit 1; }
ok() { echo "ok  $*"; }

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends rsyslog rsyslog-gnutls openssl bsdutils >/dev/null
ok "rsyslog $(rsyslogd -v | head -1 | tr -s " " | cut -d" " -f2 | tr -d ,) su $(. /etc/os-release && echo "$PRETTY_NAME")"

# PKI del progetto: CA e certificato con il FQDN della fixture e 127.0.0.1 nel SAN.
bash /prova/ads-pki.sh ca /pki >/dev/null
bash /prova/ads-pki.sh server /pki ads-collector.example.com 127.0.0.1 >/dev/null
mkdir -p /etc/rsyslog.d/tls
cp /pki/ca.pem /pki/collector.pem /pki/collector.key /etc/rsyslog.d/tls/

# Collettore: rsyslog di sistema con 10-ads.conf.
groupadd ads
mkdir -p /srv/ads && chown root:ads /srv/ads && chmod 0750 /srv/ads
cp /prova/collettore/etc/rsyslog.d/10-ads.conf /etc/rsyslog.d/
rsyslogd -N1 >/dev/null 2>&1 || { rsyslogd -N1; fail "configurazione del collettore rifiutata"; }
rsyslogd -iNONE

# Host: secondo rsyslog con 90-ads.conf; i messaggi del journal si iniettano in UDP sulla 10514.
# L access log esiste gia con una riga di login vecchia, che freshStartTail non deve rimandare.
mkdir -p /var/log/pveproxy /var/spool/rsyslog-host /var/spool/rsyslog-sbagliato
cp /prova/access-storico.log /var/log/pveproxy/access.log
cat >/etc/rsyslog-host.conf <<EOF
global(workDirectory="/var/spool/rsyslog-host")
module(load="imudp")
input(type="imudp" port="10514")
include(file="/prova/host/etc/rsyslog.d/90-ads.conf")
EOF
rsyslogd -N1 -f /etc/rsyslog-host.conf >/dev/null 2>&1 || { rsyslogd -N1 -f /etc/rsyslog-host.conf; fail "configurazione dell host rifiutata"; }
rsyslogd -f /etc/rsyslog-host.conf -i /run/rsyslog-host.pid

# Terzo rsyslog: stessa configurazione, senza access log, con un nome permesso che il
# certificato non porta e code con nomi propri.
sed "s/StreamDriverPermittedPeers=\"[^\"]*\"/StreamDriverPermittedPeers=\"altro.example.com\"/; s/ads_fwd/ads_fwd_sbagliato/g; s/ads_pveproxy/ads_pveproxy_sbagliato/g" \
    /prova/host/etc/rsyslog.d/90-ads.conf | grep -vE "imfile|freshStartTail" >/etc/rsyslog-sbagliato-90.conf
cat >/etc/rsyslog-sbagliato.conf <<EOF
global(workDirectory="/var/spool/rsyslog-sbagliato")
module(load="imudp")
input(type="imudp" port="10515")
include(file="/etc/rsyslog-sbagliato-90.conf")
EOF
rsyslogd -N1 -f /etc/rsyslog-sbagliato.conf >/dev/null 2>&1 || { rsyslogd -N1 -f /etc/rsyslog-sbagliato.conf; fail "configurazione del terzo rsyslog rifiutata"; }
rsyslogd -f /etc/rsyslog-sbagliato.conf -i /run/rsyslog-sbagliato.pid

sleep 2
logger -n 127.0.0.1 -P 10514 -d --rfc3164 -t sshd "Accepted password for root from 192.0.2.9 port 58346 ssh2"
logger -n 127.0.0.1 -P 10514 -d --rfc3164 -t pvedaemon "$(cat /prova/pvedaemon-auth.txt)"
logger -n 127.0.0.1 -P 10514 -d --rfc3164 -t pvedaemon "<root@pam> starting task UPID:pve:00071D61:452B0114:6ABE6EC3:vncproxy:210:root@pam:"
logger -n 127.0.0.1 -P 10514 -d --rfc3164 -t cron "messaggio estraneo agli accessi"
cat /prova/access-nuovo.log >>/var/log/pveproxy/access.log
logger -n 127.0.0.1 -P 10515 -d --rfc3164 -t sshd "PEER-SBAGLIATO non deve arrivare"
sleep 6

f=/srv/ads/127.0.0.1/$(date +%Y-%m-%d).log
[ -f "$f" ] || { ls -R /srv/ads; fail "file del giorno assente"; }
grep -q "sshd: Accepted password for root" "$f" || { cat "$f"; fail "login sshd non inoltrato"; }
grep -q "pvedaemon: <root@pam> successful auth for user" "$f" || { cat "$f"; fail "autenticazione pvedaemon non inoltrata"; }
grep -q "starting task" "$f" && fail "task di pvedaemon inoltrato: e un attivita, non un accesso"
grep -q "16:31:31 +0200\] \"POST /api2/extjs/access/ticket" "$f" || { cat "$f"; fail "login web dello access log non inoltrato"; }
grep -q "cluster/resources" "$f" && fail "richiesta periodica dell interfaccia inoltrata: non e un accesso"
grep -q "RIGA-STORICA" "$f" && fail "lo storico dello access log e stato rimandato"
grep -q "messaggio estraneo" "$f" && fail "messaggio non di accesso inoltrato"
grep -q "PEER-SBAGLIATO" "$f" && fail "consegnato con un nome permesso che il certificato non porta"
ok "host: login SSH, autenticazione pvedaemon e login web inoltrati in TLS con verifica del nome"
ok "host: esclusi storico dello access log, task di pvedaemon, richieste periodiche, messaggi estranei"
ok "host: nessuna consegna con un nome permesso diverso da quello del certificato"

echo "tutte le verifiche superate"
'
