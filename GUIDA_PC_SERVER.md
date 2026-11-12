# Riassunto giornaliero sul PC-server

Questa guida si segue **una volta sola, sul PC-server** (andrea-pc, Windows), cioè il computer con Ollama sempre acceso.

Alla fine succede questo:
- **Ogni mattina** il PC-server legge la pagina pubblica delle probabili formazioni e la fa riassumere al modello locale.
- **Pubblica il riassunto** nella rete Tailscale, dove è visibile solo ai tuoi dispositivi.
- **Sugli altri computer**, quando qualcuno preme "Cerca la formazione", l'IA parte da quel riassunto e spende meno. Se il riassunto manca, l'IA legge le fonti da sola come prima.

I comandi vanno scritti nel **Prompt dei comandi** di Windows: tasto Windows, scrivi `cmd`, premi Invio.

---

## 1. Cosa serve

| Cosa | Come controllarlo |
|---|---|
| Python 3.11 o successivo | `py -3 --version` |
| Ollama acceso, con il modello | `ollama list` deve mostrare `gpt-oss:20b`. Se manca: `ollama pull gpt-oss:20b` |
| Tailscale collegato | `tailscale status` mostra andrea-pc e gli altri dispositivi |
| Git, oppure lo zip del progetto | `git --version` |

## 2. Scarica il progetto

Scegli una cartella, ad esempio `C:\fantacalcio`:

```
git clone https://github.com/AndreaValenziano/fantacalcio.git C:\fantacalcio
cd /d C:\fantacalcio
```

Se il progetto è già lì, aggiornalo:

```
cd /d C:\fantacalcio
git pull
```

## 3. Prepara il consigliere (una volta)

1. Doppio clic su `C:\fantacalcio\avvia.bat`: si apre la pagina nel browser.
2. Leggi l'avviso e premi **"Ho capito e accetto"**. L'avviso è cambiato: ora parla anche del riassunto automatico. Va accettato di nuovo anche se l'avevi già fatto.
3. Nel riquadro **Listone** premi **"Aggiorna dal sito"**, oppure carica il file Excel. Il listone serve per controllare che i nomi del riassunto esistano davvero.
4. Chiudi la finestra nera del consigliere.

## 4. Prova a mano

```
cd /d C:\fantacalcio
py -3 -m consigliere.riassunto
```

Ci vuole qualche minuto: il modello lavora una partita alla volta. Alla fine compare una riga come:

```
2026-11-13T09:04:12+01:00 scritto 20261113-090000.json: 412 schede, 37 scartate, 0/10 pezzi falliti
```

- Le **schede scartate** sono normali: il programma butta via i nomi che non sono nel listone e le frasi che non compaiono nella pagina.
- Se compare `non scritto: ...`, guarda la tabella "Se qualcosa non va" in fondo.

Il riassunto finisce in `%USERPROFILE%\ConsiglioFormazione\riassunti\`. La copia da condividere è `riassunti\condiviso\ultimo.json`.

## 5. Attiva la routine giornaliera

```
cd /d C:\fantacalcio
py -3 -m consigliere.riassunto --attiva --ora 09:00
```

Controlla che l'attività esista:

```
schtasks /Query /TN ConsiglioFormazioneRiassunto
```

L'attività parte solo se all'ora scelta il PC è **acceso**, con il tuo utente **collegato** e **Ollama avviato**. Se il PC era spento, il riassunto di quel giorno manca e le ricerche funzionano senza.

## 6. Pubblica il riassunto in Tailscale

### Prima volta: attiva HTTPS nella rete

1. Apri la [console di Tailscale](https://login.tailscale.com/admin/dns).
2. Nella pagina **DNS**, controlla che **MagicDNS** sia attivo.
3. Nella sezione **HTTPS Certificates**, premi **Enable HTTPS**.

### Pubblica la cartella

```
tailscale serve --bg "%USERPROFILE%\ConsiglioFormazione\riassunti\condiviso"
tailscale serve status
```

`tailscale serve status` mostra l'indirizzo, del tipo `https://andrea-pc.<nome-rete>.ts.net/`.

**L'indirizzo da dare agli altri** è quello più `ultimo.json`, ad esempio `https://andrea-pc.tail1234.ts.net/ultimo.json`.

La cartella pubblicata contiene **solo** `ultimo.json`. Leghe, listone e registro restano privati.

**Verifica da un altro computer** della rete, nel browser:
- l'indirizzo con `/ultimo.json` mostra il riassunto;
- l'indirizzo con `/registro.txt` dà errore. È giusto così.

**Se `tailscale serve` non accetta una cartella** su Windows, usa questo ripiego: lascia aperta una finestra con il primo comando e, in un'altra finestra, lancia il secondo:

```
py -3 -m http.server 8766 --bind 127.0.0.1 --directory "%USERPROFILE%\ConsiglioFormazione\riassunti\condiviso"
tailscale serve --bg 8766
```

## 7. Sugli altri computer (tuo Mac e fratelli)

1. Installa Tailscale e accedi con lo **stesso account**. In alternativa, dalla console di Tailscale **condividi** andrea-pc con il loro account.
2. Apri nel browser l'indirizzo di `ultimo.json` e controlla che si veda.
3. Aggiorna il consigliere: `git pull` se usi git, altrimenti lo zip nuovo.
4. Avvia il consigliere e accetta di nuovo l'avviso.
5. Apri **"Riassunto giornaliero (facoltativo)"**, incolla l'indirizzo e premi **Salva**.

Da quel momento la pagina del risultato dice **"con il riassunto del modello locale"** oppure **"senza riassunto"**.

## 8. Spegnere tutto

```
cd /d C:\fantacalcio
py -3 -m consigliere.riassunto --disattiva
tailscale serve reset
```

`tailscale serve reset` toglie **tutte** le pubblicazioni di `tailscale serve` di questo PC, non solo il riassunto.

## Se qualcosa non va

Il registro delle esecuzioni è in `%USERPROFILE%\ConsiglioFormazione\riassunti\registro.txt`. Le ultime righe si vedono anche nella pagina del consigliere.

| Messaggio | Cosa fare |
|---|---|
| `manca il listone` | Punto 3: carica il listone nel consigliere di questo PC. |
| `server non raggiungibile` | Ollama è spento o il modello manca: avvia Ollama, poi `ollama list`. |
| `Ollama ha risposto 404` | Il modello non è installato: `ollama pull gpt-oss:20b`, oppure usa `--modello` con un modello che hai. |
| `pagina non leggibile (403...)` | Il sito ha bloccato la lettura. Non va aggirato: per quel giorno niente riassunto. |
| `nessuna scheda valida` | Il modello non ha estratto nulla di controllabile. Riprova a mano; se succede spesso, prova un altro modello con `--modello`. |
| Molti `pezzi falliti` | Il modello ha risposto con JSON rotto: riprova, o prova un altro modello. |
| L'attività non parte | `schtasks /Query /TN ConsiglioFormazioneRiassunto /V` mostra l'ultimo esito; il PC deve essere acceso e con l'utente collegato. |
| Sugli altri PC sempre "senza riassunto" | Apri l'indirizzo di `ultimo.json` nel browser di quel PC. Se non si apre, il problema è Tailscale o `tailscale serve`. Se si apre, il riassunto ha più di 24 ore. |

**Lettura di fantacalcio.it:** la routine legge una sola pagina pubblica, le probabili formazioni, una volta al giorno, senza login e senza entrare nelle leghe. I termini d'uso di Fantacalcio vietano comunque l'accesso automatico senza autorizzazione: è un rischio che hai scelto di accettare. Per toglierlo basta il punto 8.
