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
    unattended-upgrades qemu-guest-agent rsyslog rsyslog-gnutls sudo >/dev/null
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

echo "tutte le verifiche superate"
'
