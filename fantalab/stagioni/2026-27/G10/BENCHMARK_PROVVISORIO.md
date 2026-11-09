# Benchmark retrospettivo — 10ª giornata Serie A 2026/27

**Data dell'analisi:** 6 novembre 2026.  
**Natura:** formazione ottenuta **dopo** che le partite sono state disputate; NON previsione ex ante.  
**Stato:** ricostruzione motivata da fonti web; **totale 125 punti stimato** secondo i bonus riportati e le regole note. Da riconciliare con i fantavoti esatti esportati dalla lega prima di chiamarlo massimo matematico certificato.

## Undici migliore ricostruito — 4-3-3, Classic

| Ruolo Classic | Giocatore | Squadra | Fantavoto ricostruito |
|---|---|---|---:|
| P | Łukasz Skorupski | Bologna | 9,0 |
| D | Daniele Ghilardi | Roma | 10,0 |
| D | Evan Ndicka | Roma | 9,5 |
| D | Alessandro Bastoni | Inter | 9,5 |
| D | Víctor Valdepeñas | Fiorentina | 9,5 |
| C | Diego Moreira | Milan | 12,5 |
| C | Junior Messias | Genoa | 12,0 |
| C | Giovanni Fabbian | Parma | 11,5 |
| A | Armand Laurienté | Sassuolo | 14,0 |
| A | Farès Ghedjemis | Frosinone | 10,5 |
| A | Donyell Malen | Roma | 10,0 |

**Somma:** 9 + 10 + 9,5 + 9,5 + 9,5 + 12,5 + 12 + 11,5 + 14 + 10,5 + 10 = **118,0**.

**Modificatore difesa:** voto puro P Skorupski **7,0** e migliori tre D tra Ghilardi **7,0**, Ndicka **6,5**, Bastoni **6,5**, Valdepeñas **6,5**: (7+7+6,5+6,5)/4 = **6,75 ⇒ +5**.

**Capitano consigliato ex post:** Diego Moreira, voto puro **8,0 ⇒ +2** (anche altri calciatori potrebbero dare +2).

**Totale:** 118,0 + 5 + 2 = **125,0 punti** (ricostruzione provvisoria, non risultato certificato della piattaforma).

**Portiere imbattuto:** Skorupski ha subito un gol, quindi +1 clean sheet **non** si applica. Fantavoto **9** per rigore parato e gol subito secondo resoconti della 10ª; differisce dal fantavoto 7,5 attribuito in un archivio basato su API-Football, quindi usare quello dei resoconti che citano il fanta redazionale, da validare nell'app. 

### Attenzioni per il benchmarking

1. **Usare tassativamente i ruoli Classic di Fantacalcio.it**: Moreira **C**, Messias **C**, Isaksen **C**, Mora **C**, Wesley **D**, Njie **C**. Alcuni siti di risultati indicano ruoli *differenti* (ad esempio Moreira A e Messias A); questi porterebbero a una formazione non valida nella lega.
2. **Non confondere voti pubblicati da provider diversi**: LEGAF, Gazzetta e API-Football non usano necessariamente i voti redazionali Fantacalcio.it. Esempio Skorupski 9 nei resoconti di Fantacalcio e 7,5 nell'altro archivio.
3. Possono esserci **più undici equivalenti**: alcuni attaccanti hanno fantavoto 10; scegliere Malen non prova l'unicità del massimo.
4. Per affermare la **perfezione matematica**, acquisire la tabella **integrale** della 10ª giornata con voto puro, fantavoto e ruolo Classic, applicare i bonus personalizzati della lega, poi ottimizzare tutte le scelte valide compreso pacchetto P+4D, fattore capitano ed eventuali riserve. Questo documento è un ottimo benchmark verificabile, non ancora la dimostrazione del massimo globale.

### Fonti per la verifica

- Fantacalcio.it (pagella ufficiale redazionale, pagina pubblica, numeri talvolta caricati dinamicamente): https://www.fantacalcio.it/voti-fantacalcio-serie-a/2026-27/10
- Listone Classic snapshot 3 novembre 2026, copia da Fantacalcio.it: https://fantacalcioreale.it/listone
- Fanta Master AI, Top & Flop della giornata (suggerisce ruoli Classic e singoli voti): https://www.fantamasterai.it/top-flop/
- Fantacalcio.dev, archivio di fantavoti; attenzione ai RUOLI e al VOTO del portiere, non usare come unica fonte: https://fantacalcio.dev/giornate/353
- Voti FC redazionali puri riportati da Fantacalcio Online: https://www.fantacalcio-online.com/it/serie-a/2026-2027/voti/10-giornata/
- TuttoMercatoWeb (Skorupski FV 9, rigore parato; Moreira 12,5, Valdepeñas 9,5, Laurienté 14): https://www.tuttomercatoweb.com/fantacalcio/fantacalcio-gli-indizi-della-10a-giornata-i-migliori-della-giornata-2290497
- TuttoFantacalcio: https://www.tuttofantacalcio.it/approfondimenti-fantacalcio/player-of-the-match-giornate-serie-2026-2027-fantacalcio-34502

### Processo consigliato per la prossima settimana

Calcolare i punti REALI della previsione G11 congelata e confrontarli con: (a) la formazione vincente della lega mostrata dall'utente; (b) la formazione perfetta ex post; (c) la formazione alternativa safe. Registrare almeno il gap di punteggio e i calciatori decisivi mancati, mantenendo distinti errore di probabilità, sv/mancato minutaggio, e aleatorietà dei bonus.
