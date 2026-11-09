# Changelog

## 1.0 — 2026-11-06

- Creato progetto modulare per archiviazione, previsione, calcolo ex post, confronto e apprendimento.
- Importato **senza modifiche** il pronostico storico G11 e il benchmark provvisorio G10, più il precedente piano v2.1.
- Aggiunto format strutturato di previsione G11 per confronto automatico (copia derivata, non sostituisce l'originale).
- Aggiunti modelli e protocollo multi-IA; ottimizzatore esatto per dataset completo e test di verifica contro brute force.
- Non creati nuovi pronostici e non corretti retroattivamente i nomi selezionati.

## 1.1 — 2026-11-06 (impostazioni utente)

- Confermati bonus/malus **standard Fantacalcio.it** e +1 portiere imbattuto; elencate le opzioni del preset da verificare se incidono sull'audit.
- Confermato **solo fonti pubbliche** per reperire i voti, senza attesa di export privati.
- Introdotte due strategie **separate e complete**, A=`MASSIMA_MEDIA`, B=`PRIMO_POSTO` (proxy ceiling se manca distribuzione avversari), con KPI e nuovo confronto A/B.
- Aggiunti `CONFIGURAZIONE.md`, guide 08/09, modelli 04/05, tracciato fonti e script CLI dedicato.
- Rispettati hash e contenuti degli originali congelati G10/G11; nessuna nuova previsione retroattiva.

## 1.2 — 2026-11-07 (precisazione sui concorrenti)

- Preso atto che **tutti possono scegliere qualsiasi giocatore** in ogni giornata: non chiedere più il numero di partecipanti.
- A resta **massimo punteggio atteso**; B diventa esplicitamente **alto potenziale / ceiling**, non stima di P(primo).
- Il migliore punteggio della lega rimane confronto ex post facoltativo. Le percentuali di primo posto non sono richieste.
- Lasciati invariati per compatibilità script, test, JSON storici e le chiavi tecniche `PRIMO_POSTO`, `--primo`, `modello_primo`.
- Previsioni congelate G11 e benchmark G10 immutati; nessun dato retroattivamente inventato.
