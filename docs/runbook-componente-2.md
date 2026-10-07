# Runbook del componente 2: rsyslog ricevente e accessi al collettore

> Procedura eseguita il 2026-10-01, con comandi ed esiti. Riferimenti: sezione 4 dello studio (configurazione rsyslog e formato `AdsLine`), sezione 2 punto 7 dell'handoff (accessi al collettore stesso). I segnaposto tra parentesi angolari rimandano a `config/parametri.yaml`, come nel runbook del componente 1.

## Che cosa fa

La configurazione generata da `config/collettore/etc/rsyslog.d/10-ads.conf.template` riceve su 514/udp e su 6514/tcp in TLS e scrive ogni riga in `/srv/ads/<IP di provenienza>/<AAAA-MM-GG>.log` nel formato `AdsLine`: ora di ricezione, sorgente, ora dichiarata, sistema, messaggio. Instrada nello stesso ruleset anche gli accessi al collettore stesso, cioè i messaggi dei programmi il cui nome comincia con `sshd` e di `sudo`, `su`, `login`, `systemd-logind` e `gdm-password`, che finiscono in `/srv/ads/127.0.0.1/`. File e cartelle sono `root:ads`, 0640 e 0750, così che i job notturni, che girano come `ads`, li leggano senza poterli scrivere. Il template più recente prepara anche il filtro iLO, non ancora installato; il runbook del componente 4 ne descrive la prova.

## Due difetti trovati dalle prove, e corretti

Il primo stava nel modello `AdsLine` dello studio: con `%syslogtag%%msg%` un messaggio RFC 5424, il cui tag non finisce con `:` e il cui testo non comincia con uno spazio, usciva con tag e messaggio fusi. La prova in container `debian:trixie` lo ha mostrato con una riga `prova-udpmessaggio udp`; la forma corretta, `%msg:::sp-if-no-1st-sp%%msg:::drop-last-lf%`, è quella del formato tradizionale di rsyslog, ed è ora anche nello studio.

Il secondo è emerso solo sul collettore vero: da OpenSSH 9.8, e Debian 13 ha la 10.0, i login SSH non li scrive `sshd` ma `sshd-session`, e il filtro sul nome esatto `sshd` li perdeva. La prova in container era verde perché generava il messaggio con `logger -t sshd`, cioè con la stessa ipotesi del codice. Il filtro ora prende ogni nome che comincia con `sshd`, e la prova usa i nomi copiati dal log reale del collettore; rimettendo il filtro vecchio la prova fallisce.

## Installazione sul collettore

Sulla postazione si genera il pacchetto, con l'albero di configurazione, i tre file TLS senza la chiave della CA e le chiavi pubbliche degli amministratori, poi lo si copia e si riesegue il bootstrap, che è rieseguibile: la seconda e la terza esecuzione non hanno installato né rimosso pacchetti.

```powershell
scp -i "$env:USERPROFILE\.ssh\ads-collector_ed25519" -r "D:\log-collector\build\<pacchetto>" "D:\log-collector\bin\ads-bootstrap.sh" asopranzi@<IP_COLLETTORE>:/tmp/
ssh -t -i "$env:USERPROFILE\.ssh\ads-collector_ed25519" asopranzi@<IP_COLLETTORE> "sudo bash /tmp/ads-bootstrap.sh /tmp/<pacchetto>/collettore /tmp/<pacchetto>/tls /tmp/<pacchetto>/chiavi"
```

Il bootstrap controlla la configurazione con `rsyslogd -N1` prima di riavviare rsyslog; l'esito è stato `End of config validation run`.

## Verifiche sul collettore vero

Porte in ascolto, con `sudo ss -lntup`: `rsyslogd` su 514/udp e 6514/tcp.

Accessi al collettore, con `sudo grep -E 'sshd-session.*Accepted' /srv/ads/127.0.0.1/<giorno>.log`: la riga del login con chiave dell'amministratore compare con utente, postazione di provenienza, porta e impronta della chiave personale, seguita dalle righe di `sudo` con il comando eseguito.

Ricezione da una sorgente della LAN, inviando dall'host Proxmox `ssh root@<IP_HOST> "logger -n <IP_COLLETTORE> -P 514 -d -t prova-collettore '...'"`: compare la cartella `/srv/ads/<IP_HOST>/`, `root:ads` 0750, e la riga di prova nel formato a cinque campi, con ora di ricezione e ora dichiarata che differiscono di pochi microsecondi.

## Che cosa resta

Il filtro D7 sulle righe del QNAP, che dipende dall'elenco degli AdS approvato dalla Direzione (handoff, sezione 0). La prova negativa del collaudo punto 2, nessuna scrittura da una sorgente non ammessa, che con la LAN unica richiede un mittente fuori da quella rete. La configurazione delle sorgenti vere, che è il punto 3 dell'ordine di sviluppo.
