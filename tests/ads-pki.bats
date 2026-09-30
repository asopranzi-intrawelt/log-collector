#!/usr/bin/env bats
# PKI minima del collettore: CA, certificato server con SAN, nessuna sovrascrittura.

bats_require_minimum_version 1.5.0

setup() {
    PKI="$BATS_TEST_DIRNAME/../bin/ads-pki.sh"
    DIR="$BATS_TEST_TMPDIR/pki"
}

@test "crea la CA con vincoli di CA e chiave non leggibile da altri" {
    run bash "$PKI" ca "$DIR"
    [ "$status" -eq 0 ]
    [ -f "$DIR/ca.key" ] && [ -f "$DIR/ca.pem" ]
    run openssl x509 -in "$DIR/ca.pem" -noout -ext basicConstraints
    [[ "$output" == *"CA:TRUE"* ]]
    # Su un filesystem che non conserva i permessi POSIX (NTFS da Git Bash) il controllo non dice nulla.
    if [ "$(stat -c %a "$DIR/ca.key")" != "644" ] || [ "$(uname -s)" = Linux ]; then
        [ "$(stat -c %a "$DIR/ca.key")" = "600" ]
    fi
}

@test "il certificato server porta FQDN e IP nel SAN, uso serverAuth e scadenza a 2 anni" {
    bash "$PKI" ca "$DIR"
    run bash "$PKI" server "$DIR" ads-collector.example.com 192.0.2.50
    [ "$status" -eq 0 ]
    run openssl x509 -in "$DIR/collector.pem" -noout -ext subjectAltName,extendedKeyUsage
    [[ "$output" == *"DNS:ads-collector.example.com"* ]]
    [[ "$output" == *"IP Address:192.0.2.50"* ]]
    [[ "$output" == *"TLS Web Server Authentication"* ]]
    run openssl verify -CAfile "$DIR/ca.pem" "$DIR/collector.pem"
    [ "$status" -eq 0 ]
    # Scade fra 729 e 731 giorni: 730 giorni dichiarati, con un giorno di tolleranza.
    openssl x509 -in "$DIR/collector.pem" -noout -checkend $((729 * 86400))
    run ! openssl x509 -in "$DIR/collector.pem" -noout -checkend $((731 * 86400))
    [ ! -e "$DIR/collector.csr" ]
}

@test "non sovrascrive una CA esistente" {
    bash "$PKI" ca "$DIR"
    before=$(openssl x509 -in "$DIR/ca.pem" -noout -fingerprint -sha256)
    run bash "$PKI" ca "$DIR"
    [ "$status" -eq 1 ]
    [[ "$output" == *"esiste gia'"* ]]
    [ "$(openssl x509 -in "$DIR/ca.pem" -noout -fingerprint -sha256)" = "$before" ]
}

@test "non sovrascrive un certificato server esistente" {
    bash "$PKI" ca "$DIR"
    bash "$PKI" server "$DIR" ads-collector.example.com 192.0.2.50
    run bash "$PKI" server "$DIR" ads-collector.example.com 192.0.2.51
    [ "$status" -eq 1 ]
    [[ "$output" == *"collector.key esiste gia'"* ]]
}

@test "rifiuta il certificato server senza CA" {
    run bash "$PKI" server "$DIR" ads-collector.example.com 192.0.2.50
    [ "$status" -eq 1 ]
    [[ "$output" == *"CA assente"* ]]
}

@test "rifiuta FQDN e IP non validi" {
    bash "$PKI" ca "$DIR"
    run bash "$PKI" server "$DIR" "non valido" 192.0.2.50
    [ "$status" -eq 1 ]
    [[ "$output" == *"FQDN non valido"* ]]
    run bash "$PKI" server "$DIR" ads-collector.example.com 192.0.2.256
    [ "$status" -eq 1 ]
    [[ "$output" == *"IPv4 non valido"* ]]
}

@test "senza argomenti mostra l'uso ed esce con 2" {
    run bash "$PKI"
    [ "$status" -eq 2 ]
    [[ "$output" == *"ads-pki.sh ca"* ]]
    [[ "$output" == *"ads-pki.sh server"* ]]
}
