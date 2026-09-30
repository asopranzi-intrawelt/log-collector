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
}

@test "in prova elenca i comandi e non ne esegue nessuno" {
    run bash "$BOOT" --prova "$TREE" "$TLS"
    [ "$status" -eq 0 ]
    [[ "$output" == *"+ apt-get update"* ]]
    [[ "$output" == *"rsyslog-gnutls"* ]]
    [[ "$output" == *"+ nft -c -f /etc/nftables.conf"* ]]
    [[ "$output" == *"+ sshd -t"* ]]
    [[ "$output" == *"/etc/rsyslog.d/tls/collector.key"* ]]
}

@test "la chiave TLS si installa in 0600 e la verifica nft precede il caricamento" {
    run bash "$BOOT" --prova "$TREE" "$TLS"
    [ "$status" -eq 0 ]
    key_line=$(grep -F "collector.key /etc/rsyslog.d/tls/collector.key" <<<"$output")
    [[ "$key_line" == *"-m 0600"* ]]
    check=$(grep -n -F "+ nft -c -f" <<<"$output" | cut -d: -f1)
    enable=$(grep -n -F "enable --now nftables" <<<"$output" | cut -d: -f1)
    [ "$check" -lt "$enable" ]
}

@test "rifiuta una cartella TLS che contiene la chiave della CA" {
    touch "$TLS/ca.key"
    run bash "$BOOT" --prova "$TREE" "$TLS"
    [ "$status" -eq 1 ]
    [[ "$output" == *"la chiave della CA non va sul collettore"* ]]
}

@test "rifiuta un albero con segnaposto non sostituiti" {
    echo "ip saddr {{ rete.subnet_lan }}" >>"$TREE/etc/nftables.conf"
    run bash "$BOOT" --prova "$TREE" "$TLS"
    [ "$status" -eq 1 ]
    [[ "$output" == *"segnaposto non sostituiti"* ]]
}

@test "rifiuta un albero incompleto" {
    rm "$TREE/etc/qemu/qemu-ga.conf"
    run bash "$BOOT" --prova "$TREE" "$TLS"
    [ "$status" -eq 1 ]
    [[ "$output" == *"manca etc/qemu/qemu-ga.conf"* ]]
}

@test "rifiuta un file TLS mancante" {
    rm "$TLS/collector.pem"
    run bash "$BOOT" --prova "$TREE" "$TLS"
    [ "$status" -eq 1 ]
    [[ "$output" == *"manca collector.pem"* ]]
}

@test "senza --prova e senza root si ferma prima di toccare qualcosa" {
    [ "$(id -u)" -ne 0 ] || skip "eseguito come root"
    run bash "$BOOT" "$TREE" "$TLS"
    [ "$status" -eq 1 ]
    [[ "$output" == *"va eseguito come root"* ]]
    [[ "$output" != *"apt-get"* ]]
}
