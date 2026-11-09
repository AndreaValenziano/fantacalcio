# Verifica della giornata: dati pubblici, punteggio e formazione perfetta

**Data:** 9 novembre 2026 (Europa/Roma)
**Stato:** design approvato in conversazione, da rivedere per iscritto
**Origine:** `ANALISI_PER_CLAUDE_FANTALAB_2.md` (revisione esterna, P0 "verifica e motore della formazione perfetta") e la sezione "Confronto a fine giornata (seconda fase)" della spec `2026-11-09-formazione-fantacalcio-design.md`.

## Obiettivo

Dopo ogni giornata il consigliere deve dire, con numeri riproducibili, quanto valeva la formazione consigliata, quanto quella schierata davvero e quanto la migliore possibile, per **tutte le leghe** configurate. Il punto di partenza è un modo affidabile di leggere voti e listone dalle pagine pubbliche di fantacalcio.it, senza mai entrare in una lega.

Criteri di successo:

1. I voti di una giornata e il listone Classic si ottengono con un pulsante, oppure caricando la pagina salvata dal browser, e ogni copia è archiviata con orario e SHA-256.
2. Per ogni lega il report riporta perfetta assoluta, perfetta della rosa (leghe a rosa), migliore tra i 18 scelti, punteggio ottenuto e regret scomposto.
3. Il motore della formazione perfetta coincide con l'enumerazione completa sui casi piccoli e con `fantalab/strumenti/ottimizza.py` sulla 4-3-3 libera.
4. Dati mancanti o regole incerte producono `PROVVISORIO` o `DATI_INCOMPLETI`, mai "perfetto".
5. G10 e G11 di FantaLab vengono verificate senza modificare alcun file in `fantalab/`.

## Cosa abbiamo verificato (9 novembre 2026)

Prove fatte con `curl` e con `urllib` della libreria standard, User-Agent dichiarato, nessun login:

| Pagina | Esito | Contenuto utile |
|---|---|---|
| `https://www.fantacalcio.it/voti-fantacalcio-serie-a/2026-27/11` | 200, HTML server-side | 20 squadre, 333 giocatori; id, ruolo Classic, voto e FV per tre fonti (prima: Redazione Fantacalcio); SV = `55`; cartellini come classe CSS; eventi (gol, gol subiti, autoreti, rigori segnati/sbagliati/parati, assist, Player of the match) |
| `.../2026-27/10` | 200 | come sopra |
| `https://www.fantacalcio.it/quotazioni-fantacalcio` | 200 | 603 righe, id, nome, squadra, ruolo Classic (oltre a prezzi e Mantra, da ignorare) |
| `https://www.fantacalcio.it/probabili-formazioni-serie-a` | 200 | giornata 12, percentuali di impiego |

`robots.txt` non esclude queste pagine. Non esiste un blocco tecnico: il limite incontrato finora è che i numeri stanno negli attributi `data-value`, che lo strumento web dell'IA perde quando converte la pagina in testo (da cui la frase in `consigliere/skill/SKILL.md` "i voti numerici non sono nel testo delle pagine").

**Rischio contrattuale invariato.** I termini d'uso di fantacalcio.it vietano l'accesso automatico senza autorizzazione scritta. È il rischio già accettato da Andrea nella spec principale, con l'avviso al primo avvio; ora riguarda anche il programma oltre all'IA. L'avviso va aggiornato per dirlo.

**Cosa non si fa:** nessuna elusione di misure anti-bot (browser "stealth", CAPTCHA, rotazione di IP o di User-Agent), nessun login, nessun indirizzo `leghe.fantacalcio.it` o `apileague.fantacalcio.it`. Se un giorno il download viene bloccato, la fonte è `FONTE_NON_ACCESSIBILE` e resta la riserva manuale.

## Decisioni prese

| Decisione | Scelta |
|---|---|
| Recupero dei dati | Download automatico su pulsante, con caricamento manuale della pagina salvata come riserva |
| Perimetro | Recupero dati + verifica della giornata |
| Leghe | Tutte (libera, rosa con moduli multipli, Switch, Hybrid) |
| Formazioni confrontate | Consigliata (sempre) + schierata davvero (facoltativa) |
| Motore | Generalizzazione esatta di `ottimizza.py`; enumerazione completa sulle rose |

Queste scelte cambiano due vincoli scritti in `CLAUDE.md` e nella spec principale ("il programma non scarica nulla da fantacalcio.it", "il listone si carica a mano", "scaricare in massa pagine… fuori dallo scopo"): vanno aggiornati nel primo task dell'implementazione. Il download resta di poche pagine per giornata, mai in massa.

## Architettura

Nuovi moduli in `consigliere/`, tutti con la sola libreria standard:

| Modulo | Compito | Dipende da |
|---|---|---|
| `fonti.py` | elenco chiuso di URL, download, archivio delle copie | `archivio.py` |
| `pagine.py` | lettura dell'HTML di voti e listone | nulla (solo `html.parser`) |
| `punteggio.py` | FV della lega, sostituzioni, capitano, modificatore, Switch | nulla |
| `ottimo.py` | formazione perfetta esatta | `punteggio.py` |
| `verifica.py` | sceglie la consigliata, calcola misure e regret, scrive le versioni | i moduli sopra, `archivio.py` |

`server.py` aggiunge le API; `web/` aggiunge la vista Verifica; `ricerca.py` (o il punto in cui il server rileva `FATTO`) aggiunge il sigillo.

`fantalab/` resta invariato: `ottimizza.py` viene usato solo nei test come riferimento.

## 1. Recupero e archivio delle pagine (`fonti.py`, `pagine.py`)

**URL ammessi**, costruiti dal programma e mai presi da testo esterno:

- `https://www.fantacalcio.it/voti-fantacalcio-serie-a/<stagione>/<giornata>` con stagione `AAAA-AA` e giornata 1–38;
- `https://www.fantacalcio.it/quotazioni-fantacalcio`;
- `https://www.fantacalcio.it/probabili-formazioni-serie-a` (archiviata ora, usata in una fase successiva).

Ogni altro URL è rifiutato prima della richiesta.

**Download:** solo su azione della persona; una richiesta alla volta, almeno 3 secondi tra due richieste, timeout 30 secondi, User-Agent `ConsiglioFormazione/<versione>`, un solo tentativo. Errore di rete, HTTP diverso da 200 o pagina senza la tabella attesa: messaggio che spiega il motivo e propone di salvare la pagina dal browser e caricarla.

**Archivio:** `~/ConsiglioFormazione/fonti/<tipo>/<chiave>/<AAAAMMGG-HHMMSS>.html` più `.json` con URL, orario ISO con fuso, origine (`scaricata` / `caricata_a_mano`), SHA-256 dell'HTML, versione del lettore, riepilogo dei dati letti. Scritture atomiche, nessuna sovrascrittura; `<chiave>` è `<stagione>-G<nn>` per i voti, `listone` per le quotazioni.

**Lettura dei voti** (solo colonna Redazione Fantacalcio): per giocatore `id`, `nome`, `squadra`, `ruolo` (`P/D/C/A`), `voto` (numero o `null` per SV), `fv_pubblicato`, `ammonito`, `espulso`, eventi `gol`, `gol_subiti`, `autogol`, `rigori_segnati`, `rigori_sbagliati`, `rigori_parati`, `assist`, `player_of_the_match`. Voti con virgola decimale. Per partita: squadre e data.

**Lettura del listone:** `id`, `nome`, `squadra`, `ruolo` Classic. Le colonne con prezzi e ruoli Mantra vengono saltate di proposito. Il listone salvato in `listone.json` acquista il campo `id`; quello caricato da xlsx resta valido senza `id`, e in quel caso i voti si collegano per nome e squadra con le regole di `listone.py` (mai scelte tra omonimi).

**Completezza dei voti:** 10 partite, 20 squadre, almeno 11 giocatori con voto o SV per squadra. Altrimenti `DATI_INCOMPLETI` con l'elenco delle mancanze; una partita assente è indicata come possibile rinvio.

**Confronto tra versioni:** se per la stessa giornata esiste già una copia, la verifica elenca i giocatori con voto o eventi cambiati.

## 2. Punteggio di una formazione (`punteggio.py`)

Funzione pura: (regole della lega, voti della giornata, formazione) → totale, dettaglio, stato.

- **FV della lega** = voto + Σ eventi × `lega.bonus`, compreso `player_of_the_match` e `porta_inviolata` al portiere con voto e zero gol subiti.
- **Controllo incrociato:** voto + eventi con i bonus standard (senza Player of the match e porta inviolata) deve dare `fv_pubblicato`. Se no, il giocatore è "da verificare" e il risultato `PROVVISORIO`.
- **SV:** non è 6 né 0. Con `ammonito_senza_voto`, un SV ammonito vale 5,5 (FV 5,5 − 0,5) e non viene sostituito.
- **Sostituzioni** dei titolari SV, nell'ordine della panchina:
  - `traditional`: prima riserva con voto dello stesso ruolo, fino a `sostituzioni.numero` (`null` = illimitate);
  - `hybrid`: se manca il pari ruolo, anche un ruolo diverso purché il modulo risultante sia tra quelli ammessi; quando un cambio di ruolo diverso decide il punteggio, `PROVVISORIO`.
  - Con cambi insufficienti l'ordine di applicazione è P→D→C→A, poi l'ordine dei titolari: è un'ipotesi, quindi `PROVVISORIO` solo se un ordine diverso cambierebbe il totale.
- **Capitano** (se attivo): bonus sul voto puro con le fasce della lega. Capitano SV: subentra il vice, regola "da verificare" → `PROVVISORIO` e report con entrambe le ipotesi.
- **Modificatore difesa** (se attivo): dopo le sostituzioni, solo con almeno 4 difensori con voto; media del voto puro del portiere e dei 3 migliori difensori; 7 fasce `<6, [6,6.25), [6.25,6.5), [6.5,6.75), [6.75,7), [7,7.25), ≥7.25` lette da `modificatore_difesa.fasce`.
- **Switch:** la consigliata si valuta senza Switch; se l'IA ne aveva proposto uno, si calcola anche la variante con lo scambio. La schierata si inserisce già con lo Switch applicato.
- **Uscita:** totale, dettaglio per giocatore (voto, eventi, FV della lega, entrato/uscito), cambi, modificatore con media, capitano con bonus, stato `ESATTO` / `PROVVISORIO` (con motivi) / `DATI_INCOMPLETI`.

## 3. Formazione perfetta (`ottimo.py`)

Funzione pura: (regole della lega, giocatori con voto e ruolo, insieme ammesso) → undici, modulo, capitano, totale. Usa le funzioni di `punteggio.py` per FV, modificatore e capitano.

**Misure per giornata e lega:**

| Misura | Insieme |
|---|---|
| Perfetta assoluta | tutti i giocatori con voto della giornata |
| Perfetta della rosa | i giocatori della rosa della lega (solo `tipo: rosa`) |
| Migliore tra i 18 | titolari + panchina della consigliata; e della schierata, se c'è |
| Ottenuto | `punteggio.py` sulla formazione |

**Regret:** totale = perfetta assoluta − ottenuto, scomposto in:

- limite della rosa = perfetta assoluta − perfetta della rosa (0 nelle leghe libere);
- errore di selezione = perfetta della rosa (o assoluta se libera) − migliore tra i 18;
- errore di schieramento = migliore tra i 18 − ottenuto.

**Algoritmo**, per ogni modulo ammesso:

- portiere e difesa: per ogni livello di voto puro si tengono i migliori n_D difensori per FV (riduzione esatta di FantaLab, estesa a 3/4/5 difensori), si enumerano le combinazioni con ogni portiere, si calcolano modificatore e miglior bonus capitano del pacchetto;
- centrocampo e attacco: migliori per FV con il vincolo "almeno uno con bonus capitano ≥ soglia" (`group_best_k`);
- si provano tutte le soglie capitano della lega (solo 0 se il capitano non è attivo) e si tiene il massimo.

Su insiemi piccoli (rosa, 18 scelti) si usa l'enumerazione completa. Parità: si riporta l'undici con gli id più bassi e il report scrive "uno degli ottimi". Obiettivo di tempo: perfetta assoluta di una lega a 7 moduli sotto 10 secondi; eventuali riduzioni aggiuntive devono essere esatte e coperte dal test contro l'enumerazione.

**Ruoli:** per i giocatori della rosa vale il ruolo della lega (correzioni in `lega.ruoli`); per gli altri il ruolo Classic della pagina dei voti.

## 4. Verifica, sigillo, archivio, interfaccia (`verifica.py`)

**Consigliata:** ultima ricerca della lega con `FATTO` e controllo superato, conclusa prima della scadenza (prima partita della giornata − `anticipo_minuti`). Si valuta la formazione `rosa` (o `assoluta` nelle leghe libere); per le leghe a rosa si valuta anche `assoluta` contro la perfetta assoluta. Le ricerche successive alla scadenza compaiono come "dopo la scadenza" e non contano.

**Sigillo:** quando una ricerca arriva a `FATTO`, il server aggiunge a `~/ConsiglioFormazione/registro.jsonl` una riga `{ricerca, lega, ora, sha256_risultato, sha256_richiesta}`. Il file si apre solo in aggiunta. In verifica l'impronta viene ricalcolata; se non coincide, il report lo segnala e lo stato non può essere `CERTIFICATO`. Ricerche precedenti a questa funzione: "senza sigillo".

**Schierata:** inserita nella vista Verifica con l'abbinamento nomi di `listone.py` (omonimi segnalati, mai scelti), modulo, panchina in ordine, capitano, vice, Switch; controllata con `controllo.py` per le regole della lega; ogni modifica è una nuova versione.

**Archivio:** `~/ConsiglioFormazione/verifiche/<lega>/<stagione>/G<nn>/v<k>/verifica.json` e `report.md`. Contenuto: misure, regret scomposto, dettaglio, cambi, modificatore, capitano, stato con motivi, impronte delle pagine e del risultato usati, versione del codice. Nuova versione quando cambiano i voti o la schierata; le precedenti restano.

**Stato della verifica:**

- `CERTIFICATO`: voti completi, nessun giocatore "da verificare", nessuna regola incerta che cambi il totale, sigillo integro;
- `PROVVISORIO`: con l'elenco dei motivi;
- `DATI_INCOMPLETI`: voti incompleti; si calcola comunque, ma la perfetta è "sul sottoinsieme".

**Errori diagnosticati** (solo misurabili): titolari consigliati SV e punti recuperati o persi con i cambi; capitano scelto contro il migliore nel proprio undici; modificatore ottenuto contro quello possibile con gli stessi 18; giocatori della perfetta assenti dai 18, con la differenza di punti.

**Interfaccia:** vista **Verifica** per lega con scelta della giornata, "Scarica i voti" e "Carica la pagina salvata", campo per la schierata, report (misure, regret, tabelle, stato in evidenza), elenco delle versioni. Nella vista listone, "Aggiorna dal sito". Testo dal web solo con `textContent`, link solo `http`/`https`. L'avviso iniziale viene aggiornato: il programma ora scarica anche lui le pagine pubbliche.

**API** (stessi controlli su `Host` e `Origin`):

- `POST /api/fonti/voti` — `{stagione, giornata}` per scaricare, oppure il file HTML caricato;
- `POST /api/fonti/listone` — idem;
- `GET /api/verifica/<lega>/<giornata>` — ultima versione e elenco versioni;
- `POST /api/verifica/<lega>/<giornata>` — calcola una nuova versione;
- `POST /api/verifica/<lega>/<giornata>/schierata` — salva la schierata.

## 5. G10 e G11 di FantaLab

Comando una tantum `python3 -m consigliere.verifica --fantalab <percorso fantalab> --giornata <n>`, che legge senza scrivere in `fantalab/`:

- **G11:** abbina gli id di `previsione_macchina.json` (abbreviazioni come `wesley_roma`) ai giocatori della pagina dei voti; i casi ambigui vengono chiesti alla persona; l'abbinamento si salva in `~/ConsiglioFormazione/fantalab/abbinamenti.json`. Poi verifica la previsione sulle regole della lega libera (capitano `malen`, vice `calo`).
- **G10:** perfetta assoluta con i voti completi, confrontata con i 125 punti di `BENCHMARK_PROVVISORIO.md`; il report dice se il benchmark è confermato o corretto e perché.

I report vanno in `~/ConsiglioFormazione/verifiche/fantalab/…`; aggiungerli al registro di FantaLab è una scelta manuale della persona.

## Test

Tutti senza rete, con `unittest`:

- **pagine:** copie ridotte delle pagine vere in `tests/dati/` (voti G11 con alcune squadre, listone con poche righe): ogni campo, SV, cartellini, eventi, colonne di prezzo ignorate, squadra mancante → `DATI_INCOMPLETI`, pagina senza tabella → errore;
- **fonti:** URL fuori elenco rifiutato; pausa tra richieste (con orologio finto); archivio con impronta corretta e nessuna sovrascrittura; download simulato con un server locale di test;
- **punteggio:** un caso a mano per ogni regola, confini delle fasce del modificatore e del capitano, portiere imbattuto SV, limite di cambi, Hybrid con modulo non ammesso, capitano SV, ammonito senza voto, FV pubblicato diverso dal ricalcolo;
- **ottimo:** confronto con l'enumerazione completa su insiemi sintetici casuali (semi fissati) per ogni modulo, con e senza modificatore e capitano; confronto con `fantalab/strumenti/ottimizza.py` sulla 4-3-3; casi in cui il miglior FV non è la scelta giusta; ruoli insufficienti;
- **verifica:** scelta della consigliata rispetto alla scadenza, ricerca dopo la scadenza esclusa, sigillo integro e alterato, nuova versione senza sovrascrittura, regret scomposto che somma al totale;
- **server:** nuove API con controlli `Host`/`Origin`; nessun URL arbitrario accettato.

Il download reale si prova a mano una volta e va dichiarato come tale.

## Fuori da questa spec

Strategie A e B nell'app e relativo archivio, modello quantitativo prepartita, dati passati all'IA (probabili formazioni, forma recente dai voti archiviati), andamento su più giornate e baseline, esportazioni CSV/Markdown per altre IA, cause interpretative degli errori e ipotesi da testare.

## Questioni aperte

1. Regola del vice capitano con capitano SV e riserve d'ufficio: finché non chiarita, `PROVVISORIO` con le due ipotesi.
2. Ordine di applicazione dei cambi quando sono limitati (Grossa, F1) e dettagli dell'Hybrid.
3. Assist da fermo e altre voci opzionali: emergono dal controllo incrociato sul FV pubblicato.
4. Numero di Switch ammessi nella lega dei Pensionati (già aperto nella spec principale).
