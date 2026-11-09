"""Dati di prova condivisi dai test: listone, leghe, richieste e risultati validi."""
import io
import json
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

MODELLI = Path(__file__).resolve().parent.parent / "consigliere" / "modelli"
SQUADRE = ["ATA", "BOL", "CAG", "COM", "CRE", "FIO", "GEN", "INT", "JUV", "LAZ",
           "LEC", "MIL", "NAP", "PAR", "PIS", "ROM", "SAS", "TOR", "UDI", "VER"]
COMPOSIZIONE = {"P": 3, "D": 8, "C": 8, "A": 6}
MODULO_PREDEFINITO = {"pensionati": "3-4-3", "f1": "3-4-3", "grossa": "4-3-3", "libera": "4-3-3"}
LINK = "https://www.fantacalcio.it/probabili-formazioni-serie-a"


def listone_prova() -> list[dict]:
    out = []
    for ruolo, n in (("P", 12), ("D", 36), ("C", 36), ("A", 24)):
        for i in range(n):
            out.append({"nome": f"{ruolo}{i + 1:02d} Rossi", "squadra": SQUADRE[i % 20], "ruolo": ruolo})
    return out


def _per_ruolo(giocatori):
    d = {"P": [], "D": [], "C": [], "A": []}
    for g in giocatori:
        d[g["ruolo"]].append(g)
    return d


def lega_prova(modello: str) -> dict:
    lega = json.loads((MODELLI / f"{modello}.json").read_text(encoding="utf-8"))
    if lega["tipo"] == "rosa":
        pr = _per_ruolo(listone_prova())
        lega["rosa"] = [dict(g) for r, n in COMPOSIZIONE.items() for g in pr[r][:n]]
    return lega


def richiesta_prova(modello: str) -> dict:
    return {"lega": lega_prova(modello), "listone": listone_prova(), "stile": "sicuri",
            "creata_il": "2026-11-13T18:00:00+01:00",
            "comando_controllo": "python3 controlla.py richiesta.json risultato.json"}


def _formazione(giocatori, lega, modulo):
    pr = _per_ruolo(giocatori)
    d, c, a = (int(x) for x in modulo.split("-"))
    quanti = {"P": 1, "D": d, "C": c, "A": a}
    tit = {r: pr[r][:n] for r, n in quanti.items()}
    resto = {r: pr[r][quanti[r]:] for r in pr}
    pan = lega["panchina"]
    if pan["tipo"] == "fissa":
        panca = [g for r in "PDCA" for g in resto[r][:pan[r]]]
    elif pan["tipo"] == "minimi":
        panca = [g for r in "PDCA" for g in resto[r][:pan["min"][r]]]
        extra = [g for r in "PDCA" for g in resto[r][pan["min"][r]:]]
        panca += extra[:max(0, pan["max"] - len(panca))]
    else:
        panca = [g for r, n in (("P", 1), ("D", 2), ("C", 2), ("A", 2)) for g in resto[r][:n]]
    titolari = [dict(g, motivo="Titolare annunciato", stato="sicuro") for r in "PDCA" for g in tit[r]]
    f = {"modulo": modulo, "titolari": titolari, "panchina": [dict(g) for g in panca],
         "capitano": None, "vice": None, "switch": None}
    if (lega.get("capitano") or {}).get("attivo"):
        f["capitano"], f["vice"] = titolari[-1]["nome"], titolari[-2]["nome"]
    return f


def _scheda(g):
    return {"nome": g["nome"], "squadra": g["squadra"], "disponibilita": "disponibile",
            "titolarita": "titolare", "forma": "buona", "rigori_piazzati": "", "avversario": "",
            "riassunto": "Titolare nelle probabili.", "link": [LINK], "confidenza": 2,
            "fonti_in_disaccordo": False}


def risultato_valido(modello: str, modulo: str | None = None) -> dict:
    lega = lega_prova(modello)
    modulo = modulo or MODULO_PREDEFINITO[modello]
    listone = listone_prova()
    chiavi_rosa = {(g["nome"], g["squadra"]) for g in lega["rosa"]}
    formazioni = {"assoluta": _formazione([g for g in listone if (g["nome"], g["squadra"]) not in chiavi_rosa], lega, modulo)}
    if lega["tipo"] == "rosa":
        formazioni["rosa"] = _formazione(lega["rosa"], lega, modulo)
        if lega.get("switch") == "plus":
            r = formazioni["rosa"]
            cc_tit = [g for g in r["titolari"] if g["ruolo"] == "C"]
            cc_pan = [g for g in r["panchina"] if g["ruolo"] == "C"]
            r["switch"] = {"titolare": cc_tit[-1]["nome"], "riserva": cc_pan[0]["nome"]}
    schede, visti = [], set()
    for f in formazioni.values():
        for g in f["titolari"]:
            if (g["nome"], g["squadra"]) not in visti:
                visti.add((g["nome"], g["squadra"]))
                schede.append(_scheda(g))
    return {"giornata": 12, "controllato_il": "2026-11-13T18:40:00+01:00",
            "prima_partita": "2026-11-14T15:00:00+01:00", "formazioni": formazioni,
            "schede": schede, "esclusi": [{"nome": "P12 Rossi", "motivo": "Riserva"}],
            "differenza_piu_grande": "In attacco.", "fonti_non_lette": []}


def crea_xlsx(fogli: dict[str, list[list]]) -> bytes:
    """xlsx minimo con stringhe condivise, un foglio per voce."""
    stringhe, indice = [], {}

    def cella(rif, v):
        if isinstance(v, (int, float)):
            return f'<c r="{rif}"><v>{v}</v></c>'
        if v not in indice:
            indice[v] = len(stringhe)
            stringhe.append(v)
        return f'<c r="{rif}" t="s"><v>{indice[v]}</v></c>'

    def col(i):
        s = ""
        i += 1
        while i:
            i, r = divmod(i - 1, 26)
            s = chr(65 + r) + s
        return s

    fogli_xml = []
    for righe in fogli.values():
        rows = "".join(f'<row r="{n + 1}">' + "".join(cella(f"{col(i)}{n + 1}", v) for i, v in enumerate(r)) + "</row>"
                       for n, r in enumerate(righe))
        fogli_xml.append('<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                         f"<sheetData>{rows}</sheetData></worksheet>")
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    sheets = "".join(f'<sheet name="{escape(n)}" sheetId="{i + 1}" r:id="rId{i + 1}"/>' for i, n in enumerate(fogli))
    rels = "".join(f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i + 1}.xml"/>'
                   for i in range(len(fogli)))
    sst = "".join(f"<si><t>{escape(s)}</t></si>" for s in stringhe)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/workbook.xml", f'<?xml version="1.0" encoding="UTF-8"?><workbook {ns}><sheets>{sheets}</sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   f"{rels}</Relationships>")
        z.writestr("xl/sharedStrings.xml", f'<?xml version="1.0" encoding="UTF-8"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">{sst}</sst>')
        for i, x in enumerate(fogli_xml):
            z.writestr(f"xl/worksheets/sheet{i + 1}.xml", x)
    return buf.getvalue()
