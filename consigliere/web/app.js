"use strict";

// Tutti i dati arrivano dal server e, per i risultati, da pagine web lette dall'IA:
// si inseriscono solo con textContent, e i link solo se http o https.

const RUOLI = ["P", "D", "C", "A"];
const TUTTI_I_MODULI = ["3-4-3", "3-5-2", "4-3-3", "4-4-2", "4-5-1", "5-3-2", "5-4-1", "3-6-1"];
const NOMI_BONUS = {
  gol: "Gol", rigore_segnato: "Rigore segnato", rigore_parato: "Rigore parato", rigore_sbagliato: "Rigore sbagliato",
  assist: "Assist", porta_inviolata: "Porta inviolata", gol_subito: "Gol subito", autogol: "Autogol",
  ammonizione: "Ammonizione", espulsione: "Espulsione", player_of_the_match: "Player of the match",
};
const FASCE_MODIFICATORE = ["< 6", "6 – 6,25", "6,25 – 6,5", "6,5 – 6,75", "6,75 – 7", "7 – 7,25", "≥ 7,25"];
const FASCE_CAPITANO = [["<=5.5", 0], ["6", 0.5], ["6.5", 1], ["7", 1.5], [">=7.5", 2]];
const DISPONIBILITA = {
  disponibile: "disponibile", infortunio_dubbio: "infortunio in dubbio", infortunato: "infortunato",
  squalificato: "squalificato", sconosciuta: "non trovata",
};
const LISTONE_PUBBLICO = "https://www.fantacalcio.it/quotazioni-fantacalcio";
const AVVISO = "Questo strumento legge pagine pubbliche di fantacalcio.it quando premi \"Cerca la formazione\". " +
  "I termini d'uso di Fantacalcio vietano l'accesso automatico alle pagine senza autorizzazione scritta e " +
  "prevedono sanzioni fino alla cancellazione di account e leghe. Lo strumento non entra mai in una lega e non " +
  "usa le tue credenziali, ma questo riduce il rischio senza eliminarlo. La decisione di usarlo è tua.";

const stato = {
  dati: null,          // risposta di /api/stato
  lega: null,          // id della lega scelta
  ia: null,
  stile: "sicuri",
  vista: "leghe",
  ricerca: null,       // {lega, id}
  scheda: "campo",
  abbinamento: null,
  timer: null,
};

// ---------- strumenti ----------

function el(tag, attributi, ...figli) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attributi || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (k === "testo") e.textContent = v;
    else if (v === true) e.setAttribute(k, "");
    else e.setAttribute(k, String(v));
  }
  for (const f of figli.flat(Infinity)) {
    if (f === null || f === undefined || f === false) continue;
    e.append(f instanceof Node ? f : document.createTextNode(String(f)));
  }
  return e;
}

function link(url, testo) {
  if (typeof url !== "string" || !/^https?:\/\//i.test(url)) return el("span", { testo: testo || String(url) });
  return el("a", { href: url, target: "_blank", rel: "noopener noreferrer", testo: testo || url });
}

function chiave(nome, squadra) {
  const n = (t) => String(t || "").normalize("NFKD").replace(/[^\x00-\x7f]/g, "").toLowerCase()
    .replace(/[^a-z0-9]+/g, " ").trim();
  return `${n(nome)}|${n(squadra)}`;
}

let idProgressivo = 0;
const nuovoId = (p) => `${p}-${++idProgressivo}`;

function campo(etichetta, controllo) {
  const id = controllo.id || nuovoId("campo");
  controllo.id = id;
  return [el("label", { for: id, testo: etichetta }), controllo];
}

function messaggio(testo, errore) {
  const m = document.getElementById("messaggio");
  m.textContent = testo;
  m.className = errore ? "errore" : "";
  m.hidden = false;
  clearTimeout(messaggio.t);
  messaggio.t = setTimeout(() => { m.hidden = true; }, errore ? 8000 : 3500);
}

async function api(metodo, percorso, corpo, grezzo) {
  const opzioni = { method: metodo, headers: {} };
  if (grezzo) {
    opzioni.body = corpo;
    opzioni.headers["Content-Type"] = "application/octet-stream";
  } else if (corpo !== undefined) {
    opzioni.body = JSON.stringify(corpo);
    opzioni.headers["Content-Type"] = "application/json";
  }
  let r;
  try {
    r = await fetch(percorso, opzioni);
  } catch (e) {
    throw new Error("Il programma non risponde: controlla che la finestra del consigliere sia ancora aperta.");
  }
  const dati = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(dati.errore || `Errore ${r.status}`);
  return dati;
}

function data(iso) {
  const d = new Date(iso);
  return isNaN(d) ? null : d;
}

function quando(iso) {
  const d = data(iso);
  if (!d) return "data sconosciuta";
  const oggi = new Date();
  const ora = d.toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" });
  if (d.toDateString() === oggi.toDateString()) return `oggi alle ${ora}`;
  return `${d.toLocaleDateString("it-IT", { weekday: "short", day: "numeric", month: "short" })} alle ${ora}`;
}

function mancano(iso) {
  const d = data(iso);
  if (!d) return null;
  const minuti = Math.round((d - new Date()) / 60000);
  if (minuti <= 0) return "scadenza passata";
  if (minuti < 90) return `mancano ${minuti} minuti`;
  const ore = Math.round(minuti / 60);
  return ore < 48 ? `mancano ${ore} ore` : `mancano ${Math.round(ore / 24)} giorni`;
}

const legaScelta = () => stato.dati.leghe.find((l) => l.id === stato.lega) || null;

function vai(vista, extra) {
  Object.assign(stato, extra || {}, { vista });
  if (stato.timer && vista !== "corso") { clearInterval(stato.timer); stato.timer = null; }
  disegna();
  window.scrollTo(0, 0);
}

async function aggiorna() {
  stato.dati = await api("GET", "/api/stato");
  const leghe = stato.dati.leghe;
  if (stato.lega === null) {
    try { stato.lega = localStorage.getItem("lega"); } catch (e) { /* memoria del browser non disponibile */ }
  }
  if (!leghe.some((l) => l.id === stato.lega)) stato.lega = leghe.length ? leghe[0].id : null;
  const ia = stato.dati.ia;
  if (!ia.some((x) => x.id === stato.ia)) stato.ia = (ia.find((x) => x.disponibile) || ia[0] || {}).id || null;
}

function ricordaLega() {
  try { if (stato.lega) localStorage.setItem("lega", stato.lega); } catch (e) { /* facoltativo */ }
}

function disegna() {
  ricordaLega();
  const app = document.getElementById("app");
  const viste = { leghe: vistaLeghe, regole: vistaRegole, rosa: vistaRosa, corso: vistaCorso, risultato: vistaRisultato };
  app.replaceChildren(...[viste[stato.vista]()].flat(Infinity).filter(Boolean));
  if (!stato.dati.avviso_accettato) app.append(velo());
}

// ---------- avviso ----------

function velo() {
  const bottone = el("button", {
    class: "primario",
    onclick: async () => {
      try { await api("POST", "/api/avviso"); await aggiorna(); disegna(); } catch (e) { messaggio(e.message, true); }
    },
    testo: "Ho capito e accetto",
  });
  const v = el("div", { class: "velo", role: "dialog", "aria-modal": "true", "aria-labelledby": "titolo-avviso" },
    el("div", { class: "carta" },
      el("h2", { id: "titolo-avviso", testo: "Prima di iniziare" }),
      el("p", { testo: AVVISO }),
      el("div", { class: "riga-pulsanti" }, bottone)));
  setTimeout(() => bottone.focus(), 0);
  return v;
}

// ---------- Le mie leghe ----------

function riassuntoLega(l) {
  const parti = [];
  if (l.tipo === "libera") parti.push("Tutti i giocatori");
  else parti.push("Classic", `${(l.rosa || []).length} giocatori`);
  const moduli = l.moduli || [];
  parti.push(moduli.length === 1 ? `${moduli[0]} fisso` : `${moduli.length} moduli`);
  if (l.capitano && l.capitano.attivo) parti.push("capitano");
  if (l.modificatore_difesa && l.modificatore_difesa.attivo) parti.push("modificatore difesa");
  if (l.switch && l.switch !== "no") parti.push("Switch");
  return parti.join(" · ");
}

const NOMI_CAMPI = {
  moduli: "moduli", panchina: "panchina", sostituzioni: "sostituzioni", switch: "Switch",
  capitano: "capitano", modificatore_difesa: "modificatore difesa", bonus: "bonus",
};

function cartaLega(l) {
  const scelta = l.id === stato.lega;
  const avvisi = [];
  if (l.mancanti.length) {
    avvisi.push(el("div", { class: "avviso" },
      `Da completare nelle regole: ${l.mancanti.map((c) => NOMI_CAMPI[c] || c).join(", ")}.`));
  }
  if (l.avvisi_rosa.length) {
    avvisi.push(el("div", { class: "avviso" }, "Dopo l'ultimo listone, controlla questi giocatori:",
      el("ul", {}, l.avvisi_rosa.map((a) => el("li", {
        testo: a.problema === "cambio_squadra"
          ? `${a.nome}: ora risulta alla ${a.nuova_squadra} (prima ${a.squadra})`
          : `${a.nome} (${a.squadra}): non è più nel listone`,
      })))));
  }
  const fermo = (f) => (ev) => { ev.stopPropagation(); f(); };
  return el("section", {
    class: `carta cliccabile${scelta ? " scelta" : ""}`,
    "aria-current": scelta ? "true" : null,
    onclick: () => { stato.lega = l.id; disegna(); },
  },
  el("h2", {}, el("button", {
    class: "indietro", "aria-pressed": String(scelta), testo: l.nome,
    onclick: fermo(() => { stato.lega = l.id; disegna(); }),
  })),
  el("p", { class: "tenue", testo: riassuntoLega(l) }),
  avvisi,
  el("div", { class: "riga-pulsanti" },
    l.tipo === "rosa" && el("button", { onclick: fermo(() => vai("rosa", { lega: l.id, abbinamento: null })), testo: "Modifica rosa" }),
    el("button", { onclick: fermo(() => vai("regole", { lega: l.id })), testo: "Regole" })));
}

function cartaListone() {
  const l = stato.dati.listone;
  const input = el("input", {
    type: "file", accept: ".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    onchange: async (ev) => {
      const f = ev.target.files[0];
      if (!f) return;
      try {
        const r = await api("POST", "/api/listone", await f.arrayBuffer(), true);
        await aggiorna();
        disegna();
        messaggio(`Listone caricato: ${r.numero} giocatori.`);
      } catch (e) { messaggio(e.message, true); ev.target.value = ""; }
    },
  });
  return el("section", { class: "carta" },
    el("h2", { testo: "Listone" }),
    l ? el("p", { testo: `${l.numero} giocatori, caricato ${quando(l.importato_il)}.` })
      : el("div", { class: "avviso", testo: "Nessun listone: serve per abbinare la rosa e per cercare la formazione." }),
    el("p", { class: "tenue piccolo" }, "Scaricalo tu dal browser, senza accedere, dalla ",
      link(LISTONE_PUBBLICO, "pagina pubblica delle quotazioni"), " (pulsante \"Scarica\"), oppure usa la lista calciatori della tua lega."),
    campo(l ? "Carica un listone nuovo" : "Carica il listone (.xlsx)", input));
}

function cartaNuovaLega() {
  const modello = el("select", {}, stato.dati.modelli.map((m) => el("option", { value: m.id, testo: m.nome })));
  const nome = el("input", { type: "text", placeholder: "Es. Lega degli amici", maxlength: "60" });
  return el("details", { class: "carta" },
    el("summary", { testo: "Aggiungi una lega" }),
    campo("Parti dalle regole di", modello),
    campo("Nome della lega", nome),
    el("div", { class: "riga-pulsanti" }, el("button", {
      onclick: async () => {
        try {
          const l = await api("POST", "/api/leghe", { modello: modello.value, nome: nome.value });
          await aggiorna();
          vai("regole", { lega: l.id });
          messaggio("Lega creata: controlla le regole.");
        } catch (e) { messaggio(e.message, true); }
      },
      testo: "Crea la lega",
    })));
}

function motivoBlocco(l, ia) {
  if (!stato.dati.avviso_accettato) return "Accetta prima l'avviso.";
  if (!stato.dati.listone) return "Carica prima il listone.";
  if (!l) return "Crea prima una lega.";
  if (l.mancanti.length) return "Completa prima le regole della lega.";
  if (l.tipo === "rosa" && !(l.rosa || []).length) return "Inserisci prima la rosa.";
  if (!ia) return "Scegli un'IA.";
  if (!ia.disponibile) return `${ia.nome} non è installato su questo computer (comando "${ia.comando}").`;
  return null;
}

function vistaLeghe() {
  const d = stato.dati;
  const l = legaScelta();
  const ia = d.ia.find((x) => x.id === stato.ia);
  const sceltaIa = el("select", {
    onchange: (ev) => { stato.ia = ev.target.value; disegna(); },
  }, d.ia.map((x) => el("option", {
    value: x.id, selected: x.id === stato.ia,
    testo: x.nome + (x.disponibile ? "" : " (non installato)") + (x.garantita ? "" : " – non garantito"),
  })));
  const nomeStile = nuovoId("stile");
  const opzioneStile = (valore, testo) => {
    const id = nuovoId("stile");
    return [el("input", {
      type: "radio", name: nomeStile, id, value: valore, checked: stato.stile === valore,
      onchange: () => { stato.stile = valore; },
    }), el("label", { for: id, testo })];
  };
  const blocco = motivoBlocco(l, ia);
  return [
    el("h1", { testo: "Le mie leghe" }),
    el("p", { class: "sotto", testo: "Tutto resta salvato sul tuo computer." }),
    d.leghe.length ? d.leghe.map(cartaLega) : el("p", { class: "tenue", testo: "Nessuna lega: aggiungine una qui sotto." }),
    cartaNuovaLega(),
    cartaListone(),
    campo("Quale IA usare", sceltaIa),
    ia && ia.avviso && el("div", { class: "avviso", testo: ia.avviso }),
    el("fieldset", { class: "interruttore" }, el("legend", { class: "tenue", testo: "Stile" }),
      opzioneStile("sicuri", "Punti sicuri"), opzioneStile("rischio", "Più rischio")),
    el("button", {
      class: "primario", disabled: Boolean(blocco), "aria-describedby": blocco ? "motivo-blocco" : null,
      onclick: avviaRicerca, testo: "Cerca la formazione",
    }),
    blocco && el("p", { id: "motivo-blocco", class: "tenue piccolo", testo: blocco }),
    l && cartaRicerche(l),
  ];
}

async function avviaRicerca(ev) {
  ev.target.disabled = true;
  try {
    const r = await api("POST", "/api/ricerche", { lega: stato.lega, ia: stato.ia, stile: stato.stile });
    vai("corso", { ricerca: { lega: stato.lega, id: r.id, partita: Date.now() } });
  } catch (e) {
    messaggio(e.message, true);
    ev.target.disabled = false;
  }
}

function cartaRicerche(l) {
  const sezione = el("section", { class: "carta" }, el("h2", { testo: "Ricerche precedenti" }),
    el("p", { class: "tenue", testo: "Caricamento…" }));
  api("GET", `/api/ricerche/${encodeURIComponent(l.id)}`).then((elenco) => {
    const nomi = { in_corso: "in corso", pronto: "pronta", errore: "non riuscita" };
    sezione.replaceChildren(el("h2", { testo: "Ricerche precedenti" }), elenco.length
      ? el("ul", { class: "elenco" }, elenco.map((r) => el("li", {},
        el("button", {
          class: "indietro",
          onclick: () => vai(r.stato === "in_corso" ? "corso" : "risultato",
            { ricerca: { lega: l.id, id: r.id, partita: data(r.avviata_il)?.getTime() || Date.now() }, scheda: "campo" }),
          testo: `${quando(r.avviata_il)} · ${r.stile === "rischio" ? "più rischio" : "punti sicuri"} · ${nomi[r.stato] || r.stato}`,
        }))))
      : el("p", { class: "tenue", testo: "Nessuna ricerca per questa lega." }));
  }).catch((e) => sezione.append(el("div", { class: "errore-box", testo: e.message })));
  return sezione;
}

// ---------- Regole ----------

function numero(valore, opzioni) {
  return el("input", Object.assign({ type: "number", value: valore ?? "", step: "any" }, opzioni || {}));
}

function vistaRegole() {
  const l = structuredClone(legaScelta());
  const nome = el("input", { type: "text", value: l.nome, maxlength: "60" });

  const moduli = el("div", {}, TUTTI_I_MODULI.map((m) => {
    const id = nuovoId("modulo");
    return el("label", { class: "in-linea", for: id },
      el("input", { type: "checkbox", id, value: m, checked: (l.moduli || []).includes(m) }), m);
  }));

  const pan = l.panchina || { tipo: "fissa", P: 1, D: 2, C: 2, A: 2 };
  const tipoPanchina = el("select", {}, [["fissa", "Numero fisso per ruolo"], ["minimi", "Minimi per ruolo e massimo"],
    ["libera", "Libera"]].map(([v, t]) => el("option", { value: v, selected: pan.tipo === v, testo: t })));
  const numeriPanchina = el("div");
  const valoriPanchina = {};
  const disegnaPanchina = () => {
    const t = tipoPanchina.value;
    const base = t === "minimi" ? (pan.min || {}) : pan;
    const voci = t === "libera" ? [] : RUOLI.map((r) => [r, base[r] ?? (r === "P" ? 1 : 2)]);
    if (t === "minimi") voci.push(["max", pan.max ?? 14]);
    numeriPanchina.replaceChildren(el("div", { class: "griglia-numeri" }, voci.map(([k, v]) => {
      valoriPanchina[k] = numero(v, { min: "0", step: "1" });
      return el("div", {}, campo(k === "max" ? "Massimo" : (t === "minimi" ? `Minimo ${k}` : k), valoriPanchina[k]));
    })));
  };
  tipoPanchina.addEventListener("change", disegnaPanchina);
  disegnaPanchina();

  const sost = l.sostituzioni || { numero: null, tipo: "traditional" };
  const numSost = numero(sost.numero, { min: "0", step: "1", placeholder: "illimitate" });
  const tipoSost = el("select", {}, [["traditional", "Solo stesso ruolo (Traditional)"],
    ["hybrid", "Anche ruolo diverso se il modulo resta ammesso (Hybrid)"]]
    .map(([v, t]) => el("option", { value: v, selected: sost.tipo === v, testo: t })));

  const scelta = (valore, opzioni) => el("select", { required: true },
    el("option", { value: "", selected: valore === null || valore === undefined, testo: "— da scegliere —" }),
    opzioni.map(([v, t]) => el("option", { value: v, selected: valore === v, testo: t })));
  const sw = scelta(l.switch, [["no", "No"], ["si", "Sì, stesso ruolo"], ["plus", "Sì, Plus (anche ruolo diverso)"]]);
  const cap = scelta(l.capitano === null || l.capitano === undefined ? null : (l.capitano.attivo ? "si" : "no"),
    [["no", "No"], ["si", "Sì: voto ≤5,5 +0; 6 +0,5; 6,5 +1; 7 +1,5; ≥7,5 +2"]]);

  const mod = l.modificatore_difesa || { attivo: false };
  const modAttivo = el("input", { type: "checkbox", checked: Boolean(mod.attivo) });
  const fasce = (mod.fasce || [1, 2, 3, 4, 5, 6, 6]).map((v) => numero(v));

  const bonus = Object.fromEntries(Object.keys(NOMI_BONUS).map((k) => [k, numero((l.bonus || {})[k] ?? 0)]));
  const ammonito = el("input", { type: "checkbox", checked: Boolean(l.ammonito_senza_voto) });
  const anticipo = numero(l.anticipo_minuti ?? 0, { min: "0", step: "1" });
  const preferenze = el("textarea", { placeholder: "Es. Thuram gioca sempre se disponibile." });
  preferenze.value = l.preferenze || "";

  const leggiNumero = (input) => {
    const v = parseFloat(String(input.value).replace(",", "."));
    return Number.isFinite(v) ? v : 0;
  };

  async function salva() {
    l.nome = nome.value.trim() || l.nome;
    l.moduli = [...moduli.querySelectorAll("input:checked")].map((x) => x.value);
    const t = tipoPanchina.value;
    if (t === "libera") l.panchina = { tipo: "libera" };
    else if (t === "fissa") l.panchina = Object.assign({ tipo: "fissa" }, ...RUOLI.map((r) => ({ [r]: leggiNumero(valoriPanchina[r]) })));
    else l.panchina = { tipo: "minimi", min: Object.assign({}, ...RUOLI.map((r) => ({ [r]: leggiNumero(valoriPanchina[r]) }))), max: leggiNumero(valoriPanchina.max) };
    l.sostituzioni = { numero: numSost.value === "" ? null : leggiNumero(numSost), tipo: tipoSost.value };
    l.switch = sw.value || null;
    l.capitano = cap.value === "" ? null : (cap.value === "si" ? { attivo: true, fasce: FASCE_CAPITANO } : { attivo: false });
    l.modificatore_difesa = modAttivo.checked ? { attivo: true, fasce: fasce.map(leggiNumero) } : { attivo: false };
    l.bonus = Object.fromEntries(Object.entries(bonus).map(([k, v]) => [k, leggiNumero(v)]));
    l.ammonito_senza_voto = ammonito.checked;
    l.anticipo_minuti = leggiNumero(anticipo);
    l.preferenze = preferenze.value;
    if (!l.moduli.length) { messaggio("Scegli almeno un modulo.", true); return; }
    delete l.mancanti;
    delete l.avvisi_rosa;
    try {
      await api("PUT", `/api/leghe/${encodeURIComponent(l.id)}`, l);
      await aggiorna();
      vai("leghe");
      messaggio("Regole salvate.");
    } catch (e) { messaggio(e.message, true); }
  }

  return [
    el("button", { class: "indietro", onclick: () => vai("leghe"), testo: "← Le mie leghe" }),
    el("h1", { testo: "Regole" }),
    el("p", { class: "sotto", testo: "Copiale dalle impostazioni della lega nell'app. I campi \"da scegliere\" vanno compilati prima di cercare." }),
    el("section", { class: "carta" }, campo("Nome", nome)),
    el("section", { class: "carta" }, el("h2", { testo: "Moduli ammessi" }), moduli),
    el("section", { class: "carta" }, el("h2", { testo: "Panchina e sostituzioni" }),
      campo("Panchina", tipoPanchina), numeriPanchina,
      campo("Numero di sostituzioni (vuoto = illimitate)", numSost),
      campo("Tipo di sostituzioni", tipoSost)),
    el("section", { class: "carta" }, el("h2", { testo: "Capitano e Switch" }),
      campo("Fattore capitano", cap), campo("Switch", sw)),
    el("section", { class: "carta" }, el("h2", { testo: "Modificatore difesa" }),
      el("label", { class: "in-linea" }, modAttivo, "Attivo (portiere e 3 migliori difensori, almeno 4 difensori schierati)"),
      el("div", { class: "griglia-numeri" }, fasce.map((f, i) => el("div", {}, campo(`Media ${FASCE_MODIFICATORE[i]}`, f))))),
    el("section", { class: "carta" }, el("h2", { testo: "Bonus e malus" }),
      el("div", { class: "griglia-numeri" }, Object.entries(bonus).map(([k, v]) => el("div", {}, campo(NOMI_BONUS[k], v)))),
      el("label", { class: "in-linea" }, ammonito, "L'ammonito senza voto conta 5,5"),
      campo("Minuti di anticipo sulla scadenza", anticipo)),
    el("section", { class: "carta" }, el("h2", { testo: "Preferenze" }), campo("Indicazioni per l'IA", preferenze)),
    el("button", { class: "primario", onclick: salva, testo: "Salva le regole" }),
  ];
}

// ---------- Rosa ----------

function vistaRosa() {
  const l = structuredClone(legaScelta());
  l.rosa = l.rosa || [];
  l.ruoli = l.ruoli || {};
  const testo = el("textarea", { placeholder: "Un giocatore per riga, ad esempio:\nThuram\nDimarco INT\nA Martinez L." });

  async function salvaLega(msg) {
    delete l.mancanti;
    delete l.avvisi_rosa;
    try {
      await api("PUT", `/api/leghe/${encodeURIComponent(l.id)}`, l);
      await aggiorna();
      disegna();
      if (msg) messaggio(msg);
    } catch (e) { messaggio(e.message, true); }
  }

  function aggiungi(giocatori, sostituisci) {
    if (sostituisci) l.rosa = [];
    const presenti = new Set(l.rosa.map((g) => chiave(g.nome, g.squadra)));
    for (const g of giocatori) {
      const k = chiave(g.nome, g.squadra);
      if (presenti.has(k)) continue;
      presenti.add(k);
      l.rosa.push({ nome: g.nome, squadra: g.squadra, ruolo: l.ruoli[k] || g.ruolo });
    }
    stato.abbinamento = null;
    return salvaLega(`Rosa salvata: ${l.rosa.length} giocatori.`);
  }

  const esito = stato.abbinamento;
  let sceltiAmbigui = [];
  const cartaEsito = esito && el("section", { class: "carta" },
    el("h2", { testo: "Esito dell'abbinamento" }),
    el("p", { testo: `Trovati: ${esito.trovati.length}.` }),
    esito.ambigui.length > 0 && el("div", {}, el("p", { testo: "Più giocatori possibili: scegli tu quello giusto." }),
      esito.ambigui.map((a, i) => {
        const s = el("select", { onchange: (ev) => { sceltiAmbigui[i] = a.opzioni[ev.target.value] || null; } },
          el("option", { value: "", testo: "— ignora —" }),
          a.opzioni.map((o, j) => el("option", { value: j, testo: `${o.nome} (${o.squadra}, ${o.ruolo})` })));
        return el("div", {}, campo(`"${a.testo}"`, s));
      })),
    esito.non_trovati.length > 0 && el("div", { class: "avviso" }, "Non trovati nel listone (controlla come sono scritti):",
      el("ul", {}, esito.non_trovati.map((n) => el("li", { testo: n })))),
    el("div", { class: "riga-pulsanti" },
      el("button", { onclick: () => aggiungi(esito.trovati.concat(sceltiAmbigui.filter(Boolean)), false), testo: "Aggiungi alla rosa" }),
      el("button", { onclick: () => aggiungi(esito.trovati.concat(sceltiAmbigui.filter(Boolean)), true), testo: "Sostituisci la rosa" })));

  const conteggio = Object.fromEntries(RUOLI.map((r) => [r, l.rosa.filter((g) => g.ruolo === r).length]));
  const attesa = l.composizione || {};
  const tabella = el("table", {},
    el("thead", {}, el("tr", {}, el("th", { testo: "Ruolo" }), el("th", { testo: "Giocatore" }),
      el("th", { testo: "Squadra" }), el("th", {}, el("span", { class: "tenue", testo: "" })))),
    el("tbody", {}, RUOLI.flatMap((r) => l.rosa.filter((g) => g.ruolo === r)).map((g) => {
      const k = chiave(g.nome, g.squadra);
      const ruolo = el("select", {
        "aria-label": `Ruolo di ${g.nome}`,
        onchange: (ev) => { g.ruolo = ev.target.value; l.ruoli[k] = ev.target.value; salvaLega(`Ruolo di ${g.nome} corretto per questa lega.`); },
      }, RUOLI.map((x) => el("option", { value: x, selected: g.ruolo === x, testo: x })));
      return el("tr", {}, el("td", {}, ruolo), el("td", { testo: g.nome }), el("td", { testo: g.squadra }),
        el("td", {}, el("button", {
          class: "rimuovi", "aria-label": `Togli ${g.nome}`, testo: "Togli",
          onclick: () => { l.rosa = l.rosa.filter((x) => x !== g); salvaLega(`${g.nome} tolto dalla rosa.`); },
        })));
    })));

  return [
    el("button", { class: "indietro", onclick: () => vai("leghe"), testo: "← Le mie leghe" }),
    el("h1", { testo: `Rosa · ${l.nome}` }),
    el("p", { class: "sotto", testo: "Incolla i nomi: vengono abbinati al listone caricato, senza tirare a indovinare." }),
    !stato.dati.listone && el("div", { class: "avviso", testo: "Carica prima il listone dalla pagina delle leghe." }),
    el("section", { class: "carta" },
      campo("Giocatori da aggiungere", testo),
      el("div", { class: "riga-pulsanti" }, el("button", {
        disabled: !stato.dati.listone,
        onclick: async () => {
          try {
            stato.abbinamento = await api("POST", `/api/leghe/${encodeURIComponent(l.id)}/abbina`, { testo: testo.value });
            disegna();
          } catch (e) { messaggio(e.message, true); }
        },
        testo: "Abbina al listone",
      }))),
    cartaEsito,
    el("section", { class: "carta" },
      el("h2", { testo: `La rosa (${l.rosa.length})` }),
      el("div", { class: "conteggio" }, RUOLI.map((r) => el("span", {
        class: attesa[r] !== undefined && attesa[r] !== conteggio[r] ? "fuori" : "",
        testo: `${r} ${conteggio[r]}${attesa[r] !== undefined ? `/${attesa[r]}` : ""}`,
      }))),
      RUOLI.some((r) => attesa[r] !== undefined && attesa[r] !== conteggio[r]) &&
        el("div", { class: "avviso", testo: `Il numero per ruolo è diverso dalla composizione della lega (${RUOLI.map((r) => `${attesa[r]}${r}`).join(" ")}).` }),
      legaScelta().avvisi_rosa.length > 0 && el("div", { class: "avviso" }, "Dopo l'ultimo listone, controlla:",
        el("ul", {}, legaScelta().avvisi_rosa.map((a) => el("li", {
          testo: a.problema === "cambio_squadra" ? `${a.nome}: ora alla ${a.nuova_squadra}` : `${a.nome}: non è più nel listone`,
        })))),
      l.rosa.length ? tabella : el("p", { class: "tenue", testo: "Ancora vuota." })),
  ];
}

// ---------- Ricerca in corso ----------

function vistaCorso() {
  const r = stato.ricerca;
  const l = stato.dati.leghe.find((x) => x.id === r.lega);
  const ia = stato.dati.ia.find((x) => x.id === stato.ia);
  const tempo = el("span", { testo: "" });
  const scrivi = () => {
    const s = Math.max(0, Math.round((Date.now() - r.partita) / 1000));
    tempo.textContent = `${Math.floor(s / 60)} min ${String(s % 60).padStart(2, "0")} s`;
  };
  scrivi();
  const controlla = async () => {
    scrivi();
    try {
      const s = await api("GET", `/api/ricerche/${encodeURIComponent(r.lega)}/${encodeURIComponent(r.id)}`);
      if (s.stato !== "in_corso") vai("risultato", { scheda: "campo" });
    } catch (e) { messaggio(e.message, true); }
  };
  if (stato.timer) clearInterval(stato.timer);
  stato.timer = setInterval(controlla, 3000);
  return [
    el("h1", { testo: "Ricerca in corso" }),
    el("p", { class: "sotto", testo: "Si è aperto un terminale: lì vedi cosa sta facendo l'IA." }),
    el("section", { class: "terminale" },
      el("div", { class: "grigio", testo: l ? l.nome : r.lega }),
      el("div", {}, "Tempo trascorso: ", tempo),
      el("div", { testo: "Quando l'IA ha finito, il risultato compare qui da solo." })),
    ia && ia.avviso && el("div", { class: "avviso", testo: ia.avviso }),
    el("section", { class: "carta" },
      el("h2", { testo: "Non entra mai in una lega" }),
      el("p", { class: "tenue", testo: "Nessun login e nessun invio: la formazione la inserisci tu nell'app." })),
    el("section", { class: "carta" },
      el("p", { class: "tenue", testo: "Hai chiuso il terminale o l'IA si è fermata? Premi qui: se il risultato non c'è, la pagina te lo dice." }),
      el("div", { class: "riga-pulsanti" }, el("button", {
        onclick: async () => {
          try {
            await api("POST", `/api/ricerche/${encodeURIComponent(r.lega)}/${encodeURIComponent(r.id)}/chiudi`);
            vai("risultato", { scheda: "campo" });
          } catch (e) { messaggio(e.message, true); }
        },
        testo: "Ho chiuso il terminale",
      }))),
  ];
}

// ---------- Risultato ----------

function vistaRisultato() {
  const r = stato.ricerca;
  const contenitore = el("div", {}, el("p", { class: "tenue", testo: "Caricamento…" }));
  api("GET", `/api/ricerche/${encodeURIComponent(r.lega)}/${encodeURIComponent(r.id)}`)
    .then((s) => contenitore.replaceChildren(...[s.stato === "pronto" ? risultatoPronto(s) : risultatoNonPronto(s)].flat(Infinity).filter(Boolean)))
    .catch((e) => contenitore.replaceChildren(el("div", { class: "errore-box", testo: e.message })));
  return [el("button", { class: "indietro", onclick: () => vai("leghe"), testo: "← Le mie leghe" }), contenitore];
}

function risultatoNonPronto(s) {
  if (s.stato === "in_corso") {
    return [el("h1", { testo: "Ricerca ancora in corso" }),
      el("button", { onclick: () => vai("corso"), testo: "Segui la ricerca" })];
  }
  return [
    el("h1", { testo: "La ricerca non è andata a buon fine" }),
    el("p", { class: "sotto", testo: "Nessuna formazione da mostrare: il risultato non ha superato il controllo." }),
    el("div", { class: "errore-box" }, "Cosa non va:", el("ul", {}, (s.errori || []).map((e) => el("li", { testo: e })))),
    el("p", { class: "tenue", testo: "Puoi avviare una nuova ricerca dalla pagina delle leghe." }),
  ];
}

const perNome = (giocatori, nome) => (giocatori || []).find((g) => g.nome === nome);

function schedaDi(ris, g) {
  return (ris.schede || []).find((s) => chiave(s.nome, s.squadra) === chiave(g.nome, g.squadra)) || null;
}

function risultatoPronto(s) {
  const ris = s.risultato;
  const f = ris.formazioni.rosa || ris.formazioni.assoluta;
  const haConfronto = Boolean(ris.formazioni.rosa && ris.formazioni.assoluta);
  const testa = [`Dati controllati ${quando(ris.controllato_il)}`];
  const m = mancano(s.scadenza);
  if (m) testa.push(m);
  const schede = [["campo", "Campo"], ["motivi", "Motivi"]].concat(haConfronto ? [["confronto", "Confronto"]] : []);
  if (!schede.some(([k]) => k === stato.scheda)) stato.scheda = "campo";
  const corpo = el("div", { role: "tabpanel", id: "pannello" });
  const pannelli = { campo: () => pannelloCampo(ris, f), motivi: () => pannelloMotivi(ris, f), confronto: () => pannelloConfronto(ris) };
  const mostra = () => {
    corpo.replaceChildren(...[pannelli[stato.scheda]()].flat(Infinity).filter(Boolean));
    for (const b of barra.children) b.setAttribute("aria-selected", String(b.dataset.scheda === stato.scheda));
  };
  const barra = el("div", { class: "interruttore", role: "tablist" }, schede.map(([k, t]) => el("button", {
    role: "tab", "data-scheda": k, "aria-controls": "pannello",
    onclick: () => { stato.scheda = k; mostra(); },
    testo: t,
  })));
  mostra();
  return [
    el("h1", { testo: `Giornata ${ris.giornata}` }),
    el("p", { class: "sotto", testo: `${testa.join(" · ")} · ${s.stile === "rischio" ? "più rischio" : "punti sicuri"}` }),
    s.scadenza && el("p", { class: "tenue piccolo", testo: `Scadenza stimata: ${quando(s.scadenza)} (prima partita meno l'anticipo della lega). La formazione la inserisci tu nell'app.` }),
    barra,
    corpo,
  ];
}

function pannelloCampo(ris, f) {
  const linee = ["A", "C", "D", "P"].map((r) => el("div", { class: "linea" },
    f.titolari.filter((g) => g.ruolo === r).map((g) => {
      const cap = g.nome === f.capitano;
      const vice = g.nome === f.vice;
      return el("div", { class: `giocatore${cap ? " capitano" : ""}${g.stato === "dubbio" ? " dubbio" : ""}` },
        el("div", { class: "nome", testo: g.nome + (cap ? " (C)" : vice ? " (VC)" : "") }),
        el("div", { class: "ruolo", testo: g.ruolo + (g.stato === "dubbio" ? " ⚠ dubbio" : "") }));
    })));
  const capitano = f.capitano && perNome(f.titolari, f.capitano);
  const schedaCap = capitano && schedaDi(ris, capitano);
  return [
    el("p", { class: "tenue", testo: `Modulo ${f.modulo}${ris.formazioni.rosa ? " · la tua rosa" : ""}` }),
    el("div", { class: "campo", "aria-label": `Formazione ${f.modulo}` }, linee),
    capitano && el("section", { class: "carta" },
      el("h3", { testo: `${capitano.nome}, capitano` + (f.vice ? ` · vice ${f.vice}` : "") }),
      el("p", { class: "tenue", testo: capitano.motivo || "" }),
      schedaCap && el("p", { class: "tenue piccolo", testo: (schedaCap.link || []).length === 1 ? "1 fonte letta, con link." : `${(schedaCap.link || []).length} fonti lette, con link.` })),
    f.switch && el("section", { class: "carta" },
      el("h3", { testo: "Switch consigliato" }),
      el("p", { testo: `Esce ${f.switch.titolare}, entra ${f.switch.riserva}.` })),
    el("section", { class: "carta" },
      el("p", { class: "tenue", testo: "Panchina, in ordine di ingresso" }),
      el("p", { testo: f.panchina.map((g) => g.nome).join(" · ") })),
  ];
}

function dettagliScheda(sc) {
  if (!sc) return null;
  const voci = [["Disponibilità", DISPONIBILITA[sc.disponibilita] || sc.disponibilita], ["Titolarità", sc.titolarita],
    ["Forma", sc.forma], ["Rigori e piazzati", sc.rigori_piazzati], ["Avversario", sc.avversario],
    ["Riassunto", sc.riassunto], ["Affidabilità", `${sc.confidenza}/3${sc.confidenza === 0 ? " (non ho trovato nulla)" : ""}`]]
    .filter(([, v]) => v !== undefined && v !== null && v !== "");
  return el("details", {}, el("summary", { testo: "Scheda e fonti" }),
    el("dl", {}, voci.flatMap(([k, v]) => [el("dt", { testo: k }), el("dd", { testo: String(v) })])),
    sc.fonti_in_disaccordo && el("p", { class: "avviso", testo: "Le fonti non concordano su questo giocatore." }),
    (sc.link || []).length > 0 && el("ul", {}, sc.link.map((u) => el("li", {}, link(u)))));
}

function pannelloMotivi(ris, f) {
  const ordinati = RUOLI.flatMap((r) => f.titolari.filter((g) => g.ruolo === r));
  return [
    el("section", { class: "carta" }, el("ul", { class: "elenco" }, ordinati.map((g) => el("li", {},
      el("div", { class: `motivo${g.stato === "dubbio" ? " dubbio" : ""}` },
        el("span", { class: "r", testo: g.ruolo }),
        el("span", { testo: g.nome + (g.nome === f.capitano ? " (C)" : g.nome === f.vice ? " (VC)" : "") }),
        el("span", { class: "stato", testo: g.stato }),
        el("span", { class: "testo", testo: g.motivo || "" }),
        dettagliScheda(schedaDi(ris, g))))))),
    (ris.esclusi || []).length > 0 && el("section", { class: "carta" }, el("h2", { testo: "Perché fuori" }),
      el("ul", {}, ris.esclusi.map((x) => el("li", {}, el("strong", { testo: `${x.nome}: ` }), x.motivo || "")))),
    (ris.fonti_non_lette || []).length > 0 && el("section", { class: "carta" }, el("h2", { testo: "Fonti che l'IA non è riuscita a leggere" }),
      el("ul", {}, ris.fonti_non_lette.map((x) => el("li", {}, typeof x === "string" ? link(x) : String(x))))),
  ];
}

function pannelloConfronto(ris) {
  const a = ris.formazioni.rosa;
  const b = ris.formazioni.assoluta;
  const nomeCon = (f, g) => (g ? g.nome + (g.nome === f.capitano ? " (C)" : "") : "—");
  const righe = RUOLI.flatMap((r) => {
    const x = a.titolari.filter((g) => g.ruolo === r);
    const y = b.titolari.filter((g) => g.ruolo === r);
    return Array.from({ length: Math.max(x.length, y.length) }, (_, i) => [r, x[i], y[i]]);
  });
  return [
    el("p", { class: "tenue", testo: `La tua rosa (${a.modulo}) e la migliore tra tutti i giocatori (${b.modulo}).` }),
    el("section", { class: "carta" }, el("table", {},
      el("thead", {}, el("tr", {}, el("th", { testo: "" }), el("th", { testo: "La mia rosa" }), el("th", { testo: "Migliore assoluta" }))),
      el("tbody", {}, righe.map(([r, x, y]) => {
        const uguali = x && y && chiave(x.nome, x.squadra) === chiave(y.nome, y.squadra);
        return el("tr", {}, el("td", { class: "r", testo: r }), el("td", { testo: nomeCon(a, x) }),
          el("td", { class: uguali ? "" : "diverso", testo: nomeCon(b, y) }));
      })))),
    ris.differenza_piu_grande && el("section", { class: "carta" },
      el("h2", { testo: "La differenza più grande" }), el("p", { class: "tenue", testo: ris.differenza_piu_grande })),
    el("p", { class: "tenue piccolo", testo: "La migliore assoluta non tiene conto dei crediti: può contenere giocatori che non puoi permetterti." }),
  ];
}

// ---------- avvio ----------

(async function avvio() {
  try {
    await aggiorna();
    disegna();
  } catch (e) {
    document.getElementById("app").replaceChildren(el("div", { class: "errore-box", testo: e.message }),
      el("button", { onclick: () => location.reload(), testo: "Riprova" }));
  }
})();
