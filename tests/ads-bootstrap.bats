#!/usr/bin/env bats
# Bootstrap del collettore in modalita' di prova: controlli sugli ingressi e comandi previsti.

setup() {
    ROOT_DIR="$BATS_TEST_DIRNAME/.."
    BOOT="$ROOT_DIR/bin/ads-bootstrap.sh"
    TREE="$BATS_TEST_TMPDIR/tree"
    TLS="$BATS_TEST_TMPDIR/tls"
    # Primo interprete che risponde davvero: su Windows python3 puo' essere lo stub dello Store.
    PY=""
    for candidate in python3 python; do
        if "$candidate" -c 'import sys' >/dev/null 2>&1; then
            PY=$candidate
            break
        fi
    done
    "$PY" "$ROOT_DIR/bin/ads-render.py" --parametri "$BATS_TEST_DIRNAME/fixtures/parametri-completi.yaml" \
        --sorgente "$ROOT_DIR/config/collettore" --destinazione "$TREE" >/dev/null
    mkdir -p "$TLS"
    touch "$TLS/ca.pem" "$TLS/collector.pem" "$TLS/collector.key"
    # Una chiave vera per ciascun amministratore della fixture, generata al volo e mai versionata.
    KEYS="$BATS_TEST_TMPDIR/keys"
    mkdir -p "$KEYS"
    for user in admuno admdue; do
        ssh-keygen -q -t ed25519 -N "" -C "$user@prova" -f "$BATS_TEST_TMPDIR/$user" </dev/null
        cp "$BATS_TEST_TMPDIR/$user.pub" "$KEYS/$user.pub"
    done
}

@test "in prova elenca i comandi e non ne esegue nessuno" {
    run bash "$BOOT" --prova "$TREE" "$TLS" "$KEYS"
    [ "$status" -eq 0 ]
    [[ "$output" == *"+ apt-get update"* ]]
    [[ "$output" == *"rsyslog-gnutls"* ]]
    [[ "$output" == *"+ nft -c -f /etc/nftables.conf"* ]]
    [[ "$output" == *"+ sshd -t"* ]]
    [[ "$output" == *"/etc/rsyslog.d/tls/collector.key"* ]]
}

@test "la chiave TLS si installa in 0600 e la verifica nft precede il caricamento" {
    run bash "$BOOT" --prova "$TREE" "$TLS" "$KEYS"
    [ "$status" -eq 0 ]
    key_line=$(grep -F "collector.key /etc/rsyslog.d/tls/collector.key" <<<"$output")
    [[ "$key_line" == *"-m 0600"* ]]
    check=$(grep -n -F "+ nft -c -f" <<<"$output" | cut -d: -f1)
    enable=$(grep -n -F "enable --now nftables" <<<"$output" | cut -d: -f1)
    [ "$check" -lt "$enable" ]
}

@test "rifiuta una cartella TLS che contiene la chiave della CA" {
    touch "$TLS/ca.key"
    run bash "$BOOT" --prova "$TREE" "$TLS" "$KEYS"
    [ "$status" -eq 1 ]
    [[ "$output" == *"la chiave della CA non va sul collettore"* ]]
}

@test "rifiuta un albero con segnaposto non sostituiti" {
    echo "ip saddr {{ rete.subnet_lan }}" >>"$TREE/etc/nftables.conf"
    run bash "$BOOT" --prova "$TREE" "$TLS" "$KEYS"
    [ "$status" -eq 1 ]
    [[ "$output" == *"segnaposto non sostituiti"* ]]
}

@test "rifiuta un albero incompleto" {
    rm "$TREE/etc/qemu/qemu-ga.conf"
    run bash "$BOOT" --prova "$TREE" "$TLS" "$KEYS"
    [ "$status" -eq 1 ]
    [[ "$output" == *"manca etc/qemu/qemu-ga.conf"* ]]
}

@test "rifiuta un file TLS mancante" {
    rm "$TLS/collector.pem"
    run bash "$BOOT" --prova "$TREE" "$TLS" "$KEYS"
    [ "$status" -eq 1 ]
    [[ "$output" == *"manca collector.pem"* ]]
}

@test "senza --prova e senza root si ferma prima di toccare qualcosa" {
    [ "$(id -u)" -ne 0 ] || skip "eseguito come root"
    run bash "$BOOT" "$TREE" "$TLS" "$KEYS"
    [ "$status" -eq 1 ]
    [[ "$output" == *"va eseguito come root"* ]]
    [[ "$output" != *"apt-get"* ]]
}

@test "crea un account personale per amministratore, con la sua chiave, prima di ricaricare sshd" {
    run bash "$BOOT" --prova "$TREE" "$TLS" "$KEYS"
    [ "$status" -eq 0 ]
    [[ "$output" == *"+ groupadd ads-admin"* ]]
    [[ "$output" == *"useradd --create-home --shell /bin/bash --groups ads-admin admuno"* ]]
    [[ "$output" == *"useradd --create-home --shell /bin/bash --groups ads-admin admdue"* ]]
    [[ "$output" == *"admdue.pub /home/admdue/.ssh/authorized_keys"* ]]
    last_user=$(grep -n -F "authorized_keys" <<<"$output" | tail -1 | cut -d: -f1)
    reload=$(grep -n -F "+ systemctl reload ssh" <<<"$output" | cut -d: -f1)
    [ "$last_user" -lt "$reload" ]
    [[ "$output" == *"visudo -c -f /etc/sudoers.d/ads-admin"* ]]
    [[ "$(grep -F "sudoers.d/ads-admin /etc/sudoers.d/ads-admin" <<<"$output")" == *"-m 0440"* ]]
}

@test "rifiuta un amministratore senza chiave pubblica" {
    rm "$KEYS/admdue.pub"
    run bash "$BOOT" --prova "$TREE" "$TLS" "$KEYS"
    [ "$status" -eq 1 ]
    [[ "$output" == *"manca la chiave pubblica"*"admdue.pub"* ]]
    [[ "$output" != *"apt-get"* ]]
}

@test "rifiuta un file che non e' una chiave pubblica SSH" {
    echo "non una chiave" >"$KEYS/admuno.pub"
    run bash "$BOOT" --prova "$TREE" "$TLS" "$KEYS"
    [ "$status" -eq 1 ]
    [[ "$output" == *"non e' una chiave pubblica SSH valida"* ]]
}

@test "rifiuta un elenco di amministratori vuoto" {
    echo "# nessuno" >"$TREE/etc/ads/amministratori"
    run bash "$BOOT" --prova "$TREE" "$TLS" "$KEYS"
    [ "$status" -eq 1 ]
    [[ "$output" == *"nessun amministratore"* ]]
}

@test "rifiuta root come amministratore" {
    echo "root" >"$TREE/etc/ads/amministratori"
    cp "$KEYS/admuno.pub" "$KEYS/root.pub"
    run bash "$BOOT" --prova "$TREE" "$TLS" "$KEYS"
    [ "$status" -eq 1 ]
    [[ "$output" == *"root non puo' essere un amministratore"* ]]
}

@test "imposta il fuso orario dell'Italia" {
    run bash "$BOOT" --prova "$TREE" "$TLS" "$KEYS"
    [ "$status" -eq 0 ]
    [[ "$output" == *"+ timedatectl set-timezone Europe/Rome"* ]]
}

@test "installa il server SSH anche se l'installer non l'ha selezionato" {
    run bash "$BOOT" --prova "$TREE" "$TLS" "$KEYS"
    [ "$status" -eq 0 ]
    [[ "$(grep -F "apt-get install" <<<"$output")" == *"openssh-server"* ]]
}

@test "installa la configurazione di rsyslog e la controlla prima di riavviarlo" {
    run bash "$BOOT" --prova "$TREE" "$TLS" "$KEYS"
    [ "$status" -eq 0 ]
    [[ "$output" == *"10-ads.conf /etc/rsyslog.d/10-ads.conf"* ]]
    check=$(grep -n -F "+ rsyslogd -N1" <<<"$output" | cut -d: -f1)
    restart=$(grep -n -F "+ systemctl restart rsyslog" <<<"$output" | cut -d: -f1)
    [ -n "$check" ] && [ "$check" -lt "$restart" ]
    [[ "$(grep -E "install -d .*/srv/ads$" <<<"$output")" == *"-g ads -m 0750"* ]]
}
