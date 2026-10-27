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
sed 's/ilo: \[\]/ilo: ["127.0.0.1"]/' "$root/tests/fixtures/parametri-completi.yaml" >"$work/parametri-ilo.yaml"
"$py" "$root/bin/ads-render.py" --parametri "$work/parametri-ilo.yaml" \
    --sorgente "$root/config/collettore" --destinazione "$work/ilo-tree" >/dev/null
sed 's/seeweb_opnsense: \[\]/seeweb_opnsense: ["127.0.0.2"]/' "$root/tests/fixtures/parametri-completi.yaml" >"$work/parametri-seeweb.yaml"
"$py" "$root/bin/ads-render.py" --parametri "$work/parametri-seeweb.yaml" \
    --sorgente "$root/config/collettore" --destinazione "$work/seeweb-tree" >/dev/null
sed 's/windows_pilota: \[\]/windows_pilota: ["127.0.0.1"]/' "$root/tests/fixtures/parametri-completi.yaml" >"$work/parametri-heartbeat.yaml"
"$py" "$root/bin/ads-render.py" --parametri "$work/parametri-heartbeat.yaml" \
    --sorgente "$root/config/collettore" --destinazione "$work/heartbeat-tree" >/dev/null

# Su Git Bash il percorso va passato a Docker in forma Windows.
mount_src=$work/tree
mount_ilo=$work/ilo-tree
mount_seeweb=$work/seeweb-tree
mount_heartbeat=$work/heartbeat-tree
mount_bin=$root/bin
mount_fixtures=$root/tests/fixtures
if command -v cygpath >/dev/null; then
    mount_src=$(cygpath -w "$work/tree")
    mount_ilo=$(cygpath -w "$work/ilo-tree")
    mount_seeweb=$(cygpath -w "$work/seeweb-tree")
    mount_heartbeat=$(cygpath -w "$work/heartbeat-tree")
    mount_bin=$(cygpath -w "$root/bin")
    mount_fixtures=$(cygpath -w "$root/tests/fixtures")
fi

MSYS_NO_PATHCONV=1 docker run --rm --cap-add NET_ADMIN -v "$mount_src:/tree:ro" -v "$mount_ilo:/ilo-tree:ro" -v "$mount_seeweb:/seeweb-tree:ro" -v "$mount_heartbeat:/heartbeat-tree:ro" -v "$mount_bin:/ads-bin:ro" -v "$mount_fixtures:/ads-fixtures:ro" "$IMAGE" bash -c '
set -euo pipefail
fail() { echo "FALLITO: $*"; exit 1; }
ok() { echo "ok  $*"; }

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends nftables openssh-server chrony \
    unattended-upgrades qemu-guest-agent rsyslog rsyslog-gnutls sudo openssl iproute2 python3-minimal >/dev/null
ok "pacchetti installabili su $(. /etc/os-release && echo "$PRETTY_NAME")"

nft -c -f /tree/etc/nftables.conf || fail "nft -c rifiuta il ruleset"
nft -c -f /seeweb-tree/etc/nftables.conf || fail "nft -c rifiuta la regola Seeweb"
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
rsyslogd -i /run/rsyslogd-ads.pid
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
# Riga del firewall Zyxel ZLD 5.42 come arriva sulla 514 (letta sul collettore il 2026-10-02, con
# indirizzi di documentazione e identificativo del dispositivo azzerato): anno dopo l ora e nessun
# nome di programma, con i due punti dentro il primo campo.
printf "<142>Oct  2 05:35:37 2026 usgflex500 src=\"192.0.2.73:0\" dst=\"192.0.2.1:0\" msg=\"Failed login attempt to Device from http/https (incorrect password or inexistent username)\" note=\"Account: admin\" user=\"unknown\" devID=\"000000000000\" cat=\"User\"" > /dev/udp/127.0.0.1/514
sleep 2
f=/srv/ads/127.0.0.1/$(date +%Y-%m-%d).log
[ -f "$f" ] || { ls -R /srv/ads; fail "file del giorno assente: $f"; }
grep -q "prova-udp messaggio udp" "$f" || { cat "$f"; fail "riga UDP RFC 5424 assente o con tag e messaggio fusi"; }
grep -q "prova-3164: messaggio 3164" "$f" || { cat "$f"; fail "riga UDP RFC 3164 assente"; }
grep -q "prova-udpmessaggio" "$f" && fail "tag e messaggio fusi"
grep -qF " usgflex500 src=\"192.0.2.73:0\" dst=\"192.0.2.1:0\" msg=\"Failed login attempt" "$f" || { cat "$f"; fail "riga Zyxel alterata o con il sistema sbagliato"; }
grep -q " 2026 usgflex500 " "$f" && fail "anno preso per nome del sistema"
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
ok "rsyslog: UDP (RFC 5424 e 3164, riga Zyxel identica con sistema giusto) e TLS ricevuti, TCP in chiaro scartato, accessi sshd-session, sshd-auth e sudo nel ruleset ads, $(wc -l < "$f") righe AdsLine, permessi root:ads"

# Seconda istanza con IP della sorgente iLO impostato: usa i testi osservati sul dispositivo,
# non messaggi inventati intorno alla regola. Un evento sconosciuto deve restare nel file di
# revisione, mentre i login Browser devono essere gli unici tre eventi in AdsFile.
kill "$(cat /run/rsyslogd-ads.pid)"
for i in 1 2 3 4 5 6 7 8 9 10; do [ ! -e /run/rsyslogd-ads.pid ] && break; sleep 0.2; done
install -m 0644 /ilo-tree/etc/rsyslog.d/10-ads.conf /etc/rsyslog.d/
rsyslogd -N1 >/dev/null 2>&1 || { rsyslogd -N1; fail "rsyslogd -N1 rifiuta il filtro iLO"; }
mv "$f" "$f.baseline"
rsyslogd -i /run/rsyslogd-ads.pid
sleep 1
printf "<134>Oct  7 14:43:16 ilo-test iLO5 Browser login: administrator - 192.0.2.73(DNS name not found).\n" > /dev/udp/127.0.0.1/514
printf "<134>Oct  7 14:43:17 ilo-test iLO5 Browser login failure from: 192.0.2.73(DNS name not found).\n" > /dev/udp/127.0.0.1/514
printf "<134>Oct  7 14:43:18 ilo-test iLO5 Browser logout: Administrator - 192.0.2.73(DNS name not found).\n" > /dev/udp/127.0.0.1/514
printf "<134>Oct  7 14:43:19 ilo-test iLO5 iLO clock has been synchronized with 192.0.2.123.\n" > /dev/udp/127.0.0.1/514
printf "<134>Oct  7 14:43:20 ilo-test Network HPE Ethernet adapter status changed to OK.\n" > /dev/udp/127.0.0.1/514
printf "<134>Oct  7 14:43:21 ilo-test iLO5 Future login format from: 192.0.2.73.\n" > /dev/udp/127.0.0.1/514
sleep 2
other=/var/log/ads-ilo-other/127.0.0.1/$(date +%Y-%m-%d).log
[ -f "$f" ] && [ -f "$other" ] || fail "manca uno dei due flussi iLO"
[ "$(wc -l < "$f")" -eq 3 ] || { cat "$f"; fail "attesi tre accessi iLO nel flusso AdS"; }
[ "$(wc -l < "$other")" -eq 3 ] || { cat "$other"; fail "attesi tre altri eventi iLO nel flusso di revisione"; }
grep -qF "Browser login failure from:" "$f" || fail "fallimento Browser assente dal flusso AdS"
grep -qF "iLO clock has been synchronized" "$other" || fail "NTP iLO assente dal flusso distinto"
grep -qF "Future login format" "$other" || fail "formato nuovo iLO non conservato per revisione"
grep -qF "iLO clock has been synchronized" "$f" && fail "NTP iLO entrato nel flusso AdS"
[ "$(stat -c "%U:%G %a" "$other")" = "root:root 640" ] || fail "permessi del flusso distinto"
[ "$(stat -c "%U:%G %a" "$(dirname "$other")")" = "root:root 750" ] || fail "permessi della directory iLO tecnica"
ok "iLO: tre accessi nel flusso AdS, tre eventi tecnici o ignoti nel file distinto, nessuna riga persa"

# Il mittente Seeweb usa un IP loopback diverso: il nome host nel payload non conta per lo
# smistamento. La prova misura realmente $fromhost-ip, non un testo che imita la sorgente.
kill "$(cat /run/rsyslogd-ads.pid)"
for i in 1 2 3 4 5 6 7 8 9 10; do [ ! -e /run/rsyslogd-ads.pid ] && break; sleep 0.2; done
install -m 0644 /seeweb-tree/etc/rsyslog.d/10-ads.conf /etc/rsyslog.d/
rsyslogd -N1 >/dev/null 2>&1 || { rsyslogd -N1; fail "rsyslogd -N1 rifiuta il filtro Seeweb"; }
rsyslogd -i /run/rsyslogd-ads.pid
sleep 1
python3 -c "import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.bind((\"127.0.0.2\",0)); s.sendto(b\"<134>Oct 20 12:00:00 opnsense SEEWEB_TEST_EVENT\\n\",(\"127.0.0.1\",514))"
logger -n 127.0.0.1 -P 514 -d -t prova-ads "ADS_TEST_EVENT"
sleep 2
tech=/var/log/ads-seeweb-technical/127.0.0.2/$(date +%Y-%m-%d).log
[ -f "$tech" ] || fail "file tecnico Seeweb assente"
grep -qF "SEEWEB_TEST_EVENT" "$tech" || fail "evento Seeweb assente dal flusso tecnico"
[ ! -e "/srv/ads/127.0.0.2/$(date +%Y-%m-%d).log" ] || fail "Seeweb entrato nel flusso AdS"
grep -qF "ADS_TEST_EVENT" "$f" || fail "sorgente AdS locale persa"
[ "$(stat -c "%U:%G %a" "$tech")" = "root:root 640" ] || fail "permessi file Seeweb"
[ "$(stat -c "%U:%G %a" "$(dirname "$tech")")" = "root:root 750" ] || fail "permessi cartella Seeweb"
ok "Seeweb: sorgente UDP distinta, file tecnico root:root e zero righe nel flusso AdS"

# Il segnale Windows deve attraversare TLS da una sorgente autorizzata e arrivare nel file
# letto da D6; lo stesso APP-NAME su UDP e un RFC 3164 restano nel flusso tecnico separato.
kill "$(cat /run/rsyslogd-ads.pid)"
for i in 1 2 3 4 5 6 7 8 9 10; do [ ! -e /run/rsyslogd-ads.pid ] && break; sleep 0.2; done
install -m 0644 /heartbeat-tree/etc/rsyslog.d/10-ads.conf /etc/rsyslog.d/
rsyslogd -N1 >/dev/null 2>&1 || { rsyslogd -N1; fail "rsyslogd -N1 rifiuta il filtro heartbeat"; }
rsyslogd -i /run/rsyslogd-ads.pid
sleep 1
# Byte catturati da Fluent Bit 4.1.1: RFC 5424 con PRI 14 e BOM UTF-8 prima del MSG.
cat /ads-fixtures/fluent-bit-heartbeat-wire.bin \
    | timeout 5 openssl s_client -connect 127.0.0.1:6514 -quiet -CAfile /etc/rsyslog.d/tls/ca.pem >/dev/null 2>&1 || true
# Quattro messaggi sintetici emessi dal binario Windows 5.1.3 con il filtro Lua.
# I tre eventi Security fittizi devono entrare in AdS e il marker nel solo segnale D6.
ads_before_windows=$(wc -l < "$f")
cat /ads-fixtures/fluent-bit-windows-wire.bin \
    | timeout 5 openssl s_client -connect 127.0.0.1:6514 -quiet -CAfile /etc/rsyslog.d/tls/ca.pem >/dev/null 2>&1 || true
python3 - <<PY
import socket
import ssl

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(("127.0.0.2", 0))
sock.settimeout(5)
context = ssl.create_default_context(cafile="/etc/rsyslog.d/tls/ca.pem")
context.check_hostname = False
with context.wrap_socket(sock, server_hostname="127.0.0.1") as transport:
    transport.connect(("127.0.0.1", 6514))
    transport.sendall(b"<134>1 2026-10-26T09:00:00Z win-test ads-heartbeat - - - heartbeat-unlisted\n")
PY
printf "<134>1 2026-10-26T09:00:00Z win-test ads-heartbeat - - - heartbeat-udp\n" > /dev/udp/127.0.0.1/514
printf "<134>Oct 26 09:00:00 win-test ads-heartbeat: heartbeat-3164\n" > /dev/udp/127.0.0.1/514
sleep 2
hb=/var/lib/ads/heartbeats/127.0.0.1/$(date +%Y-%m-%d).heartbeat
rejected=/var/log/ads-heartbeat-rejected/127.0.0.1/$(date +%Y-%m-%d).log
rejected_unlisted=/var/log/ads-heartbeat-rejected/127.0.0.2/$(date +%Y-%m-%d).log
[ -f "$hb" ] && [ -f "$rejected" ] && [ -f "$rejected_unlisted" ] || fail "manca il segnale D6 o il flusso tecnico rifiutato"
grep -qF "$(printf "\357\273\277heartbeat")" "$hb" || fail "heartbeat TLS autorizzato non ricevuto"
[ "$(wc -l < "$hb")" -eq 2 ] || fail "heartbeat Windows 5.1.3 non ricevuto una volta"
grep -qF "user=\"ads_test\" event=\"4624\"" "$f" || fail "evento Windows 5.1.3 non entrato nel flusso AdS"
grep -qF "record_id=\"42\"" "$f" || fail "record ID Windows assente dal flusso AdS"
grep -F "event=\"4624\"" "$f" | grep -qF "user_domain=\"PILOT-01\"" || fail "dominio 4624 assente"
grep -qF "user=\"ads_test\" event=\"4648\"" "$f" || fail "attore 4648 assente dal flusso AdS"
grep -F "event=\"4648\"" "$f" | grep -qF "user_domain=\"EXAMPLE\"" || fail "dominio attore 4648 assente"
grep -qF "target_user=\"other_test\" target_domain=\"PILOT-01\"" "$f" || fail "bersaglio 4648 assente dal flusso AdS"
grep -qF "user=\"ads_test\" event=\"4672\"" "$f" || fail "evento 4672 assente dal flusso AdS"
[ "$(wc -l < "$f")" -eq "$((ads_before_windows + 3))" ] || fail "numero di accessi Windows inatteso nel flusso AdS"
grep -qF "heartbeat-udp" "$rejected" || fail "heartbeat UDP non separato"
grep -qF "heartbeat-3164" "$rejected" || fail "heartbeat RFC 3164 non separato"
grep -qF "heartbeat-unlisted" "$rejected_unlisted" || fail "heartbeat TLS da IP non autorizzato non separato"
grep -qF "heartbeat-unlisted" "$hb" && fail "heartbeat TLS da IP non autorizzato contato da D6"
grep -qF "heartbeat-udp" "$hb" && fail "heartbeat UDP contato da D6"
grep -qF "heartbeat-3164" "$hb" && fail "heartbeat RFC 3164 contato da D6"
grep -qF "ads-heartbeat" "$f" && fail "heartbeat entrato nel flusso AdS"
[ "$(stat -c "%U:%G %a" "$hb")" = "root:ads 640" ] || fail "permessi del segnale D6"
[ "$(stat -c "%U:%G %a" "$rejected")" = "root:root 640" ] || fail "permessi del heartbeat rifiutato"
printf "{\"version\":2,\"sources\":[{\"id\":\"127.0.0.1\",\"signal\":\"daily_heartbeat\",\"active_from\":\"$(date +%Y-%m-%d)\"}]}\n" > /tmp/heartbeat-policy.json
python3 /ads-bin/ads-silence.py --policy /tmp/heartbeat-policy.json --day "$(date +%Y-%m-%d)" > /tmp/heartbeat-report.json || fail "D6 non vede il heartbeat ricevuto"
grep -qF "\"status\":\"observed\"" /tmp/heartbeat-report.json || fail "D6 non classifica il segnale come osservato"
ok "Windows 5.1.3: tre eventi AdS e heartbeat D6 separati; IP estraneo, UDP e RFC 3164 rifiutati"

echo "tutte le verifiche superate"
'
