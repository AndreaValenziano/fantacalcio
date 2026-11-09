"""Server locale: API JSON e pagina statica, solo su 127.0.0.1."""
import json
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from consigliere import fonti, pagine, verifica
from consigliere.archivio import Archivio, ArchivioDanneggiato, campi_mancanti, controlla_id
from consigliere.controllo import controlla_formazione
from consigliere.listone import ListoneNonValido, abbina, leggi_xlsx, verifica_rosa
from consigliere.ricerca import (avvia_terminale, carica_ia, cartella_lega, chiudi_ricerca, controlla_id_ricerca,
                                 crea_ricerca, elenco_ricerche, esiste_ricerca, ricerca_in_corso, stato_ricerca)

WEB = Path(__file__).parent / "web"
STATICI = {"/": ("index.html", "text/html; charset=utf-8"),
           "/app.js": ("app.js", "text/javascript; charset=utf-8"),
           "/style.css": ("style.css", "text/css; charset=utf-8")}
MAX_LISTONE = 10 * 1024 * 1024
MAX_JSON = 2 * 1024 * 1024
MAX_PAGINA = fonti.MAX_BYTE
STILI = ("sicuri", "rischio")


class Errore(Exception):
    def __init__(self, stato: int, messaggio: str):
        super().__init__(messaggio)
        self.stato, self.messaggio = stato, messaggio


def _script(cartella: Path) -> Path:
    return cartella / ("avvia.bat" if sys.platform == "win32" else "avvia.command")


def crea_server(base: Path, porta: int = 8765, avvia=avvia_terminale, scaricatore=None) -> ThreadingHTTPServer:
    base = Path(base)
    scaricatore = scaricatore or fonti.Scaricatore()  # uno solo: rispetta la pausa tra pagine aperte
    archivio = Archivio(base)
    blocco = threading.Lock()

    def lega_o_404(id_):
        try:
            return archivio.lega(id_)
        except KeyError:
            raise Errore(404, "Lega non trovata")

    def giocatori():
        l = archivio.listone()
        return l["giocatori"] if l else None

    def stato():
        l = archivio.listone()
        leghe = []
        for lega in archivio.leghe():
            avvisi = verifica_rosa(lega.get("rosa") or [], l["giocatori"]) if l else []
            leghe.append(lega | {"mancanti": campi_mancanti(lega), "avvisi_rosa": avvisi})
        return {"avviso_accettato": archivio.avviso_accettato(),
                "listone": {"numero": len(l["giocatori"]), "importato_il": l["importato_il"]} if l else None,
                "ia": carica_ia(), "modelli": archivio.modelli(), "leghe": leghe}

    def nuova_ricerca(corpo):
        with blocco:
            if not archivio.avviso_accettato():
                raise Errore(409, "Prima leggi e accetta l'avviso sull'uso delle pagine di fantacalcio.it.")
            g = giocatori()
            if not g:
                raise Errore(409, "Carica prima il listone (file Excel scaricato da fantacalcio.it).")
            lega = lega_o_404(corpo.get("lega"))
            mancanti = campi_mancanti(lega)
            if mancanti:
                raise Errore(409, f"Completa le regole della lega: {', '.join(mancanti)}.")
            if lega.get("tipo") == "rosa" and not lega.get("rosa"):
                raise Errore(409, "La rosa della lega è vuota: inserisci prima i tuoi giocatori.")
            ia = next((x for x in carica_ia() if x["id"] == corpo.get("ia")), None)
            if ia is None:
                raise Errore(409, "Scegli un'IA dall'elenco.")
            if not ia["disponibile"]:
                raise Errore(409, f"{ia['nome']} non risulta installato: il comando '{ia['comando']}' non si trova. "
                                  "Installalo seguendo la guida, poi riavvia il consigliere.")
            if corpo.get("stile") not in STILI:
                raise Errore(409, "Scegli lo stile: punti sicuri o più rischio.")
            if ricerca_in_corso(base, lega["id"]):
                raise Errore(409, "C'è già una ricerca in corso per questa lega.")
            cartella = crea_ricerca(base, lega, g, ia, corpo["stile"], datetime.now().astimezone())
            try:
                avvia(_script(cartella), sys.platform)
            except (OSError, RuntimeError) as e:
                chiudi_ricerca(cartella)
                raise Errore(500, f"Non riesco ad aprire il terminale: {e}")
            return {"id": cartella.name}

    def stagione_giornata(stagione, giornata):
        try:
            g = int(giornata)
            verifica.cartella_giornata(base, "x", stagione, g)  # stessi controlli dell'archivio
        except (TypeError, ValueError):
            raise Errore(400, "Stagione (AAAA-AA) o giornata (1-38) non valida.")
        return stagione, g

    def acquisisci(funzione, *args):
        try:
            return funzione(*args)
        except fonti.FonteNonAccessibile as e:
            raise Errore(502, str(e))
        except pagine.PaginaNonValida as e:
            raise Errore(400, str(e))

    def richiedi_avviso():
        if not archivio.avviso_accettato():
            raise Errore(409, "Prima leggi e accetta l'avviso sull'uso delle pagine di fantacalcio.it.")

    def fonte_voti(corpo_html, corpo_json, query):
        if corpo_html is not None:
            stagione, giornata = query.get("stagione", [None])[0], query.get("giornata", [None])[0]
        else:
            richiedi_avviso()  # il download automatico richiede l'avviso; il caricamento a mano no
            stagione, giornata = corpo_json.get("stagione"), corpo_json.get("giornata")
        stagione, giornata = stagione_giornata(stagione, giornata)
        r = acquisisci(fonti.acquisisci_voti, base, stagione, giornata, corpo_html, scaricatore)
        out = {"meta": r["meta"], "giocatori": len(r["voti"]["giocatori"]),
               "mancanze": pagine.completezza(r["voti"]), "differenze": r["differenze"]}
        if r.get("nota"):
            out["nota"] = r["nota"]
        return out

    def fonte_listone(corpo_html):
        if corpo_html is None:
            richiedi_avviso()
        r = acquisisci(fonti.acquisisci_listone, base, corpo_html, scaricatore)
        with blocco:
            archivio.salva_listone(r["giocatori"], r["meta"].get("origine", "scaricata"))
        return {"numero": len(r["giocatori"]), "meta": r["meta"]}

    def voti_giornata(stagione, giornata):
        ultima = fonti.ultima(base, "voti", f"{stagione}-{giornata}")
        if ultima is None:
            return None, None
        try:
            return ultima[0], pagine.leggi_voti(ultima[1])
        except pagine.PaginaNonValida as e:
            raise Errore(409, f"L'ultima copia dei voti non è leggibile ({e}): scaricala di nuovo.")

    def leggi_verifica(lega_id, stagione, giornata):
        lega_o_404(lega_id)
        stagione, giornata = stagione_giornata(stagione, giornata)
        elenco = verifica.versioni(base, lega_id, stagione, giornata)
        ultima, illeggibile = None, None
        if elenco:  # solo l'ultima versione: se è illeggibile lo si dice, senza mostrarne una più vecchia
            k = elenco[-1]["k"]
            try:
                ultima = json.loads((verifica.cartella_giornata(base, lega_id, stagione, giornata) / f"v{k}"
                                     / "verifica.json").read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                illeggibile = k
        meta, _ = voti_giornata(stagione, giornata)
        return {"versioni": elenco, "ultima": ultima, "versione_illeggibile": illeggibile, "schierata": verifica.schierata(base, lega_id, stagione, giornata),
                "voti": meta}

    def nuova_verifica(lega_id, stagione, giornata):
        with blocco:
            lega = lega_o_404(lega_id)
            stagione, giornata = stagione_giornata(stagione, giornata)
            meta, voti = voti_giornata(stagione, giornata)
            if voti is None:
                raise Errore(409, "Scarica prima i voti della giornata.")
            g = giocatori()
            if not g:
                raise Errore(409, "Carica prima il listone.")
            cons = verifica.consigliata(base, lega_id, giornata, verifica.scadenza(voti, lega))
            dati = verifica.calcola(lega, voti, g, cons, verifica.schierata(base, lega_id, stagione, giornata),
                                    meta_voti=meta)
            cartella = verifica.salva(base, lega_id, stagione, giornata, dati)
            return {"versione": int(cartella.name[1:]), "dati": json.loads((cartella / "verifica.json").read_text("utf-8"))}

    def nuova_schierata(lega_id, stagione, giornata, corpo):
        lega = lega_o_404(lega_id)
        stagione, giornata = stagione_giornata(stagione, giornata)
        g = giocatori()
        if not g:
            raise Errore(409, "Carica prima il listone.")
        panchina_testo = corpo.get("panchina") or []
        if not isinstance(panchina_testo, list) or not all(isinstance(x, str) for x in panchina_testo):
            raise Errore(400, "La panchina deve essere un elenco di testi.")
        tit = abbina(str(corpo.get("testo") or ""), g)
        pan = abbina("\n".join(panchina_testo), g)
        ambigui, non_trovati = tit["ambigui"] + pan["ambigui"], tit["non_trovati"] + pan["non_trovati"]
        if ambigui or non_trovati:
            e = Errore(409, "Alcuni nomi non sono stati riconosciuti con certezza: correggili.")
            e.dettagli = {"ambigui": ambigui, "non_trovati": non_trovati}
            raise e
        f = {"modulo": corpo.get("modulo"), "titolari": tit["trovati"], "panchina": pan["trovati"],
             "capitano": corpo.get("capitano") or None, "vice": corpo.get("vice") or None, "switch": None}
        errori = controlla_formazione(f, lega, g)
        if errori:
            e = Errore(409, "La formazione schierata non rispetta le regole della lega: " + "; ".join(errori))
            e.dettagli = {"errori": errori}
            raise e
        return {"versione": verifica.salva_schierata(base, lega_id, stagione, giornata, f)}

    class Gestore(BaseHTTPRequestHandler):
        server_version = "Consigliere"
        sys_version = ""

        def log_message(self, formato, *args):
            pass

        def _risposta(self, codice, corpo: bytes, tipo):
            self.send_response(codice)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(corpo)

        def _json(self, codice, dati):
            self._risposta(codice, json.dumps(dati, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _ammessa(self):
            p = self.server.server_address[1]
            locali = {f"127.0.0.1:{p}", f"localhost:{p}"}
            if self.headers.get("Host") not in locali:
                return False
            origine = self.headers.get("Origin")
            return origine is None or origine in {f"http://{h}" for h in locali}

        def _corpo(self, limite):
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                raise Errore(400, "Richiesta non valida.")
            if n < 0:
                raise Errore(400, "Richiesta non valida.")
            if n > limite:
                if n <= 5 * limite:
                    while n > 0:
                        pezzo = self.rfile.read(min(n, 65536))
                        if not pezzo:
                            break
                        n -= len(pezzo)
                raise Errore(413, "File troppo grande.")
            return self.rfile.read(n) if n else b""

        def _corpo_json(self):
            try:
                dati = json.loads(self._corpo(MAX_JSON) or b"{}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise Errore(400, "Richiesta non valida.")
            if not isinstance(dati, dict):
                raise Errore(400, "Richiesta non valida.")
            return dati

        def _gestisci(self, metodo):
            if not self._ammessa():
                self.close_connection = True
                return self._json(403, {"errore": "Richiesta non ammessa."})
            percorso = urlsplit(self.path).path
            try:
                if metodo == "GET" and percorso in STATICI:
                    nome, tipo = STATICI[percorso]
                    return self._risposta(200, (WEB / nome).read_bytes(), tipo)
                if not percorso.startswith("/api/"):
                    raise Errore(404, "Non trovato.")
                parti = [unquote(x) for x in percorso[len("/api/"):].split("/")]
                return self._json(200, self._api(metodo, parti))
            except Errore as e:
                if e.stato == 413:
                    self.close_connection = True
                return self._json(e.stato, {"errore": e.messaggio} | getattr(e, "dettagli", {}))
            except ValueError:
                return self._json(404, {"errore": "Non trovato."})
            except ArchivioDanneggiato as e:
                return self._json(500, {"errore": f"Il file {e.percorso} è danneggiato: correggilo o spostalo, poi ricarica la pagina."})

        def _api(self, metodo, parti):
            match metodo, parti:
                case "GET", ["stato"]:
                    return stato()
                case "POST", ["avviso"]:
                    archivio.accetta_avviso()
                    return {"ok": True}
                case "POST", ["listone"]:
                    try:
                        g = leggi_xlsx(self._corpo(MAX_LISTONE))
                    except ListoneNonValido as e:
                        raise Errore(400, str(e))
                    archivio.salva_listone(g)
                    return {"numero": len(g)}
                case "POST", ["fonti", "voti"]:
                    query = parse_qs(urlsplit(self.path).query)
                    if "stagione" in query or "giornata" in query:
                        return fonte_voti(self._corpo(MAX_PAGINA), None, query)
                    grezzo = self._corpo(MAX_PAGINA)
                    try:
                        dati = json.loads(grezzo or b"{}")
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        dati = None
                    if not isinstance(dati, dict):
                        raise Errore(400, "Per caricare una pagina a mano indica nell'indirizzo ?stagione=AAAA-AA&giornata=N "
                                          "(il corpo deve essere l'HTML); per scaricarla invia JSON con stagione e giornata.")
                    return fonte_voti(None, dati, query)
                case "POST", ["fonti", "listone"]:
                    return fonte_listone(self._corpo(MAX_PAGINA) or None)
                case "GET", ["verifica", lega_id, stagione, giornata]:
                    return leggi_verifica(lega_id, stagione, giornata)
                case "POST", ["verifica", lega_id, stagione, giornata]:
                    return nuova_verifica(lega_id, stagione, giornata)
                case "POST", ["verifica", lega_id, stagione, giornata, "schierata"]:
                    return nuova_schierata(lega_id, stagione, giornata, self._corpo_json())
                case "POST", ["leghe"]:
                    corpo = self._corpo_json()
                    try:
                        return archivio.crea_da_modello(corpo.get("modello"), str(corpo.get("nome") or ""))
                    except (KeyError, ValueError):
                        raise Errore(400, "Modello di lega sconosciuto.")
                case "PUT", ["leghe", id_]:
                    lega_o_404(id_)
                    lega = self._corpo_json()
                    if lega.get("id") != id_:
                        raise Errore(400, "La lega inviata non corrisponde all'indirizzo.")
                    archivio.salva_lega(lega)
                    return lega
                case "POST", ["leghe", id_, "abbina"]:
                    lega = lega_o_404(id_)
                    g = giocatori()
                    if not g:
                        raise Errore(409, "Carica prima il listone.")
                    return abbina(str(self._corpo_json().get("testo") or ""), g)
                case "POST", ["ricerche"]:
                    return nuova_ricerca(self._corpo_json())
                case "GET", ["ricerche", lega_id]:
                    return elenco_ricerche(base, lega_id)
                case "GET", ["ricerche", lega_id, rid]:
                    return stato_ricerca(self._cartella(lega_id, rid))
                case "POST", ["ricerche", lega_id, rid, "chiudi"]:
                    c = self._cartella(lega_id, rid)
                    chiudi_ricerca(c)
                    return stato_ricerca(c)
            raise Errore(404, "Non trovato.")

        def _cartella(self, lega_id, rid):
            c = cartella_lega(base, lega_id) / controlla_id_ricerca(rid)
            if not esiste_ricerca(c):
                raise Errore(404, "Ricerca non trovata.")
            return c

        def do_GET(self):
            self._gestisci("GET")

        def do_POST(self):
            self._gestisci("POST")

        def do_PUT(self):
            self._gestisci("PUT")

    return ThreadingHTTPServer(("127.0.0.1", porta), Gestore)
