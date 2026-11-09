# 06 — Fonti, qualità dei dati e prevenzione degli errori

## Gerarchia orientativa

1. **Regolamento della lega e schermate ufficiali utente** per modificatori, bonus, moduli, deadline e riserve. L’utente ha confermato `bonus/malus standard Fantacalcio.it`.
2. **Fantacalcio.it redazione e listone Classic della stessa competizione** per ruolo, voti puri e fantavoti.
3. **Lega Serie A, club e comunicati ufficiali** per calendario, indisponibili, convocati, formazioni ufficiali e squalifiche.
4. **Probabili formazioni e news** (Sky, Fantacalcio.it, aggregatori affidabili), dichiarando che sono probabilità/previsioni, non certezze.
5. **Dati statistici** (xG/xA, shot maps, tiri in area, probabilità clean sheet), con provider, definizione e data.
6. **Commenti degli utenti e community** soltanto per contesto; non come fonte unica di fatti quantitativi.

## Collegamenti iniziali utili

- Calendario ufficiale: https://www.legaseriea.it/serie-a/calendario-risultati
- Anticipi/posticipi 2026/27: https://www.legaseriea.it/serie-a/news/quando-si-gioca-anticipi-e-posticipi-fino-alla-12a-giornata
- Voti Fantacalcio.it G10 (controllo sul provider): https://www.fantacalcio.it/voti-fantacalcio-serie-a/2026-27/10
- Listone Classic: accedere al listone effettivo della lega; la copia esterna di riferimento precedente era https://fantacalcioreale.it/listone (può divergere in futuro).
- Dati di terze parti utili per un controllo incrociato, **non sostituiscono** voti della lega: https://www.fantacalcio-online.com/it/serie-a/2026-2027/voti/10-giornata/

## Esempi di errori che dobbiamo impedire

- Confondere un voto puro 7 con un fantavoto 10 dopo gol.
- Usare voto Gazzetta/API-Football per ricostruire una lega con redazione Fantacalcio.it.
- Assegnare a un calciatore il ruolo tattico in campo invece del ruolo Classic nella lega.
- Non includere il +1 clean sheet nel FV della lega oppure includerlo due volte.
- Trattare una notizia successiva al primo anticipo come se fosse stata disponibile pre-deadline.
- Presentare una formazione ricostruita usando solo i migliori 30 giocatori come un **massimo matematico di TUTTA la Serie A**.
- Ricostruire come `ROSA_GIOCATA` una previsione che è soltanto un consiglio storico dell'IA.

## Dati di 10ª e 11ª

- Calendario G11 (6–8 novembre 2026) confermato da fonte Lega/Sky; il pronostico preesistente è nel file G11 congelato e non verrà corretto a posteriori.
- Il documento G10 da 125 punti ha una **ricostruzione plausibile, ma non certificata**. Riconciliare l'archivio con il dataset redazionale completo prima di fare rivendicazioni di massimo assoluto.

## Gestione correzioni

Se un sito corregge i voti, archivia la versione precedente o la data/ora della verifica, aggiungi una nuova versione del calcolo e annota cosa cambia. Se una fonte è paywall o non accessibile, scrivi `FONTE_NON_ACCESSIBILE` e non inventare un dato corrispondente.

## Vincolo nuovo: solo siti pubblici per i voti

Non pianificare né richiedere esportazioni da account/leghe private. Per ogni voto usare la **Redazione Fantacalcio.it** in una pagina pubblicamente consultabile; verificare Classic su listone ufficiale accessibile, e ogni FV, clean sheet e status SV. Se l'accesso è limitato, segnalare `FONTE_NON_ACCESSIBILE` e dichiarare non certificabile la formazione perfetta. Non aggirare blocchi o condizioni d'uso. Consultare il workflow eseguibile in `guide/09_VOTI_SOLO_PUBBLICI.md`.
