"""OLAT-Test erstellen — Streamlit-App: aus PDF (OpenAI) oder aus eingefügtem YAML (eigene KI).

    cd dev/olat-qti/app && .venv/Scripts/python -m streamlit run streamlit_app.py
"""
from __future__ import annotations

import io
import sys
import tempfile
import zipfile
from pathlib import Path

import streamlit as st
import yaml
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import olatqti  # noqa: E402

import auth  # noqa: E402
import zaehler  # noqa: E402
import umwandeln  # noqa: E402

st.set_page_config(page_title="OLAT-Test erstellen", page_icon="📝", layout="wide")

# Der Konverter liegt ausserhalb des app-Ordners. Läuft eine alte Fassung im Speicher, entstehen still
# falsche Pakete (22.09.2026: Formeln blieben als $…$ stehen, Bilder fehlten). Lieber hart stoppen.
KONVERTER_BRAUCHT = ("inline", "js_escape", "anhaengen", "mit_bildern", "steuerzeichen")
if fehlt := [n for n in KONVERTER_BRAUCHT if not hasattr(olatqti, n)]:
    st.error(f"Die App läuft mit einer veralteten Fassung des Konverters (fehlt: {', '.join(fehlt)}). "
             "Bitte im Terminal mit Strg+C beenden und neu starten:\n\n"
             "`cd D:\\OS\\dev\\olat-qti\\app` und `.venv\\Scripts\\python -m streamlit run streamlit_app.py`")
    st.stop()

nutzer = auth.anmeldung()

kopf, knopf = st.columns([5, 1])
kopf.title("OLAT-Test erstellen")
eigene = zaehler.meine(nutzer)
zusatz = f" · {eigene['anzahl']} Umwandlungen, ${eigene['kosten']:.2f}" if eigene else ""
kopf.caption(f"Angemeldet: {nutzer['name']} ({nutzer['rolle']}){zusatz}")
if knopf.button("Abmelden"):
    auth.abmelden()

if nutzer["rolle"] in zaehler.ADMIN_ROLLEN:
    with st.expander("Nutzung aller Lehrpersonen (nur kt1/reviewer)"):
        tage = st.selectbox("Zeitraum", [30, 90, 365, 3650],
                            format_func=lambda t: {30: "letzte 30 Tage", 90: "letzte 90 Tage",
                                                   365: "letztes Jahr", 3650: "alles"}[t], index=2)
        zeilen = zaehler.alle(nutzer, tage)
        if zeilen is None:
            st.caption("Nutzungszahlen nicht abrufbar (Supabase nicht erreichbar oder Rolle nicht berechtigt).")
        elif not zeilen:
            st.caption("In diesem Zeitraum wurde noch nichts umgewandelt.")
        else:
            g1, g2, g3 = st.columns(3)
            g1.metric("Umwandlungen total", sum(z["umwandlungen"] for z in zeilen))
            g2.metric("Kosten total", f"${sum(float(z['kosten_usd']) for z in zeilen):.2f}")
            g3.metric("Lehrpersonen", len(zeilen))
            st.dataframe([{"Lehrperson": z["nutzer"], "Umwandlungen": z["umwandlungen"],
                           "Kosten": f"${float(z['kosten_usd']):.2f}",
                           "Tokens": f"{z['eingabe'] + z['ausgabe']:,}".replace(",", "'"),
                           "zuletzt": (z["letzte"] or "")[:16].replace("T", " ")} for z in zeilen],
                         width="stretch", hide_index=True)
            st.caption("Gezählt werden nur Zahlen: wer, wann, Modell, Tokens, Kosten, Anzahl Fragen, "
                       "Seiten und Bilder. Keine Fragetexte, keine PDFs.")

# Modellvergleich 22.09.2026: Pruefung_Werkstoffe_mit_Loesungen.pdf, je 3 Läufe (README «App»)
MODELLE = {
    "gpt-5.6-luna": "gpt-5.6-luna — günstiger (Standard)",
    "gpt-4.1": "gpt-4.1 — teurer, sehr gleichmässig",
}
PROMPT = (Path(__file__).parent / "prompt_extern.md").read_text(encoding="utf-8")


def neuer_satz(text: str, name: str, verbrauch=None, fehlende_seiten=None,
               bilder: dict[str, bytes] | None = None, ohne_frage: list[str] | None = None) -> None:
    st.session_state["yaml"] = text
    st.session_state["pdf_name"] = name
    st.session_state["verbrauch"] = verbrauch
    st.session_state["fehlende_seiten"] = fehlende_seiten or []
    st.session_state["bilder"] = bilder or {}          # Dateiname -> Bytes, liegt im Zip unter bilder/
    st.session_state["bilder_ohne_frage"] = ohne_frage or []
    st.session_state.pop("zip", None)


def aus_pdf() -> None:
    st.info("Nur Tests mit Fragen und Lösungen hochladen — **keine Antworten von Lernenden, keine Namen, "
            "keine Noten**. Der Text des PDFs wird zur Umwandlung an OpenAI geschickt.")
    # Standard ist bewusst das günstigere Modell (erstes in MODELLE), unabhängig von secrets.toml
    modell = st.radio("Modell", list(MODELLE), format_func=MODELLE.get, horizontal=True, index=0)
    with st.container(border=True):
        st.markdown(
            "**Welches Modell?** Im Test (Werkstoff-Prüfung, 20 Fragen, je 3 Durchläufe) waren beide gleich "
            "zuverlässig: alle Lösungen, Punkte und Teile korrekt übertragen.\n"
            "- **gpt-5.6-luna** — *günstiger*. Übernimmt den Punkteschlüssel der offenen Fragen meist in die "
            "Musterlösung (praktisch für die Korrektur). Aufgaben mit Unterpunkten (a–d) werden mal als eine, "
            "mal als mehrere Fragen übertragen — beides funktioniert, aber das Ergebnis schwankt von Lauf zu Lauf.\n"
            "- **gpt-4.1** — *teurer*. Liefert bei jedem Lauf dieselbe Struktur. Lässt den Punkteschlüssel der "
            "offenen Fragen meist weg.\n\n"
            "Bei beiden noch nicht an echten Scans geprüft — Fragen von Bildseiten mit ⚠ besonders kontrollieren. "
            "gpt-4.1-mini ist bewusst nicht wählbar: Im Test falsche Punkte und verstümmelte Umlaute.")

    st.caption("🎬 **Video oder Audio einbetten:** Bei der Frage im PDF einen Link auf YouTube, nanoo.tv oder "
               "eine mp3-Datei hinschreiben — ausgeschrieben oder hinter einem Wort verlinkt. In OLAT erscheint "
               "er als Player unter dem Fragetext. Der Link muss für Lernende ohne Anmeldung erreichbar sein.")
    st.caption("🖼 **Bilder** (Diagramme, Schemas, Fotos) werden aus dem PDF übernommen und der Frage zugeordnet, "
               "bei der sie stehen. Logos auf jeder Seite und kleine Symbole werden ausgelassen.")
    pdf = st.file_uploader("PDF mit Fragen und Lösungen", type=["pdf"])
    if not pdf:
        return
    try:
        seiten = umwandeln.analysiere_pdf(pdf.getvalue())
    except Exception as e:  # kaputtes oder verschlüsseltes PDF
        st.error(f"PDF nicht lesbar: {e}")
        return
    problemseiten = [s for s in seiten if s["art"] != "text"]
    bilder_mitschicken = True
    if problemseiten:
        ohne = [str(s["nr"]) for s in problemseiten if s["art"] == "ohne_text"]
        bild = [str(s["nr"]) for s in problemseiten if s["art"] == "bild_mit_wenig_text"]
        zeilen = []
        if ohne:
            zeilen.append(f"**ohne Text** (Scan/Foto): Seite {', '.join(ohne)}")
        if bild:
            zeilen.append(f"**grosses Bild, wenig Text**: Seite {', '.join(bild)}")
        st.warning(f"{len(problemseiten)} von {len(seiten)} Seiten sind ganz oder teilweise Bild — "
                   + "; ".join(zeilen) + ". Fragen dort fehlen, wenn diese Seiten nicht als Bild mitgehen.")
        bilder_mitschicken = st.checkbox(
            f"Diese {len(problemseiten)} Seite(n) als Bild an OpenAI schicken (Texterkennung durch das Modell)",
            value=True, help="Kostet mehr als Text. Handschrift und schlechte Scans werden unsicherer gelesen — "
                             "betroffene Fragen erscheinen in der Tabelle mit ⚠.")
        if bilder_mitschicken and len(problemseiten) > umwandeln.MAX_BILDSEITEN:
            st.error(f"Mehr als {umwandeln.MAX_BILDSEITEN} Bildseiten — bitte das PDF aufteilen.")
            return
    else:
        st.caption(f"{len(seiten)} Seiten, alle mit Text.")
    funde = umwandeln.bilder_aus_pdf(pdf.getvalue())
    if funde:
        st.caption(f"🖼 {len(funde)} Bild(er) gefunden — werden den Fragen zugeordnet.")

    if not st.button("In Fragen umwandeln", type="primary"):
        return
    if not st.secrets.get("openai", {}).get("api_key"):
        st.error("In den Secrets fehlt der OpenAI-Schlüssel. Ergänzen:\n\n"
                 '```toml\n[openai]\napi_key = "sk-…"\n```\n\n'
                 "Ohne Schlüssel funktioniert der Weg «YAML einfügen» trotzdem.")
        return
    text, anzahl = umwandeln.pdf_text(pdf.getvalue())
    if funde:
        text = umwandeln.pdf_text_mit_bildern(pdf.getvalue(), funde)
    bildseiten = [s["nr"] for s in problemseiten] if bilder_mitschicken else []
    if len(problemseiten) == anzahl and not bildseiten:
        st.error("Keine Seite enthält Text. Ohne Bildübermittlung gibt es nichts umzuwandeln.")
        return
    bilder = umwandeln.seiten_als_bild(pdf.getvalue(), bildseiten) if bildseiten else []
    zusatz = f", davon {len(bilder)} als Bild" if bilder else ""
    with st.spinner(f"{anzahl} Seiten werden umgewandelt{zusatz} ({modell}) …"):
        try:
            roh, verbrauch = umwandeln.frage_openai(
                OpenAI(api_key=st.secrets["openai"]["api_key"]), modell, text, bilder)
        except Exception as e:  # Netz, Schlüssel, Kontingent, Abbruch — alles dem Menschen zeigen
            st.error(f"Umwandlung fehlgeschlagen: {e}")
            return
    satz = umwandeln.zu_fragensatz(roh)
    umwandeln.pruefe_medien(satz, text)
    ohne_frage = umwandeln.pruefe_bilder(satz, {f["name"] for f in funde})
    neuer_satz(yaml.safe_dump(satz, allow_unicode=True, sort_keys=False, width=100), Path(pdf.name).stem,
               {**verbrauch, "modell": modell}, [s["nr"] for s in problemseiten] if not bildseiten else [],
               {f["name"]: f["daten"] for f in funde}, ohne_frage)
    zaehler.protokolliere(nutzer, "pdf", {**verbrauch, "modell": modell}, umwandeln.kosten(verbrauch, modell),
                          fragen=len(umwandeln.alle_fragen(satz)), seiten=anzahl, bilder=len(funde))


def aus_yaml() -> None:
    st.markdown(
        "Ohne OpenAI-Schlüssel der Schule: Fragen mit **der eigenen KI** vorbereiten "
        "(z. B. Copilot mit bbw-Konto) und das Ergebnis hier einfügen.\n\n"
        "1. **Prompt kopieren** — Symbol oben rechts im Kasten.\n"
        "2. In der KI einfügen und darunter die eigenen Fragen mit Lösungen anhängen (Text oder Datei) — "
        "oder Material und den Wunsch, daraus Fragen zu erstellen.\n"
        "3. Die Antwort der KI (YAML) unten einfügen und **Übernehmen**.")
    st.caption("Auch hier gilt: keine Antworten von Lernenden, keine Namen, keine Noten in die KI.")
    st.caption("🎬 **Video oder Audio einbetten:** Links auf YouTube, nanoo.tv oder mp3 bei der Frage angeben — die KI "
               "übernimmt sie nach `medien:`. Direkt im YAML: `medien: [\"https://www.youtube.com/watch?v=…\"]`. "
               "In OLAT erscheint der Link als Player unter dem Fragetext.")
    with st.expander("Prompt anzeigen und kopieren", expanded=False):
        st.code(PROMPT, language="markdown", wrap_lines=True)
    st.download_button("Prompt als Datei", PROMPT.encode("utf-8"), "olat-test-prompt.md", "text/markdown")

    eingefuegt = st.text_area("Antwort der KI (YAML)", height=300,
                              placeholder="titel: …\nsektionen:\n  - titel: …\n    fragen:\n      - typ: sc\n        …")
    if not st.button("Übernehmen", type="primary", key="yaml_uebernehmen"):
        return
    text = umwandeln.yaml_aus_antwort(eingefuegt)
    try:
        satz = yaml.safe_load(text)
    except yaml.YAMLError as e:
        st.error(f"Das ist kein gültiges YAML: {e}. Meist fehlen Anführungszeichen um einen Text mit Komma "
                 "oder Doppelpunkt — die KI bitten, das zu korrigieren.")
        return
    if not isinstance(satz, dict) or not (satz.get("fragen") or satz.get("sektionen")):
        st.error("Kein Fragensatz erkannt: es fehlt `titel` mit `sektionen` oder `fragen`.")
        return
    neuer_satz(text, umwandeln.dateiname(satz.get("titel", "test")))
    zaehler.protokolliere(nutzer, "yaml", fragen=len(umwandeln.alle_fragen(satz)))


pdf_tab, yaml_tab = st.tabs(["Aus PDF (OpenAI)", "YAML einfügen (eigene KI)"])
with pdf_tab:
    aus_pdf()
with yaml_tab:
    aus_yaml()

if "yaml" not in st.session_state:
    st.stop()
st.divider()

# ------------------------------------------------------------------ prüfen und bearbeiten
try:
    satz = yaml.safe_load(st.session_state["yaml"]) or {}
except yaml.YAMLError as e:
    st.error(f"YAML nicht lesbar: {e}")
    satz = {}

paare = umwandeln.alle_fragen(satz)
fragen = [f for _, f in paare]
anzahl_sektionen = len(satz.get("sektionen") or []) or 1
v = st.session_state.get("verbrauch")
st.subheader(f"«{satz.get('titel', '?')}» — {len(fragen)} Fragen in {anzahl_sektionen} "
             f"Sektion{'en' if anzahl_sektionen > 1 else ''}, "
             f"{sum(float(f.get('punkte', 1)) for f in fragen):g} Punkte")
if v:
    modell = v.get("modell", "?")
    betrag = umwandeln.kosten(v, modell)
    with st.container(border=True):
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Kosten dieser Umwandlung", f"${betrag:.4f}" if betrag is not None else "–",
                  help="Eingabe- und Ausgabe-Tokens × Preis pro Million Tokens. Bildseiten zählen als Eingabe.")
        k2.metric("Tokens", f"{v['eingabe']:,} ein / {v['ausgabe']:,} aus".replace(",", "'"))
        if betrag is not None:
            k3.metric("100 solche Umwandlungen", f"${betrag * 100:.2f}")
        if (m := zaehler.meine(nutzer)):
            seit = f", seit {m['seit']}" if m["seit"] else ""
            k4.metric("Ihre Umwandlungen", f"{m['anzahl']} · ${m['kosten']:.2f}",
                      help=f"Alle Ihre Umwandlungen in dieser App{seit} — in Supabase gezählt, "
                           "nur Zahlen, keine Inhalte.")
        andere = [(m2, umwandeln.kosten(v, m2)) for m2 in umwandeln.PREISE if m2 != modell]
        preise = " · ".join(f"{m2}: ${e:.2f} ein / ${a:.2f} aus" for m2, (e, a) in umwandeln.PREISE.items())
        vergleich = " · ".join(f"mit {m2} wären es ${k:.4f}" for m2, k in andere if k is not None)
        st.caption(f"Modell: **{modell}**. {vergleich} (bei gleich vielen Tokens — ein anderes Modell "
                   f"braucht meist etwas mehr oder weniger). Preise pro Million Tokens: {preise}.")
        if fehler := st.session_state.get("zaehler_fehler"):
            st.caption(f"⚠ {fehler} — das Zip ist davon nicht betroffen.")
if fehlend := st.session_state.get("fehlende_seiten"):
    st.warning(f"Seite {', '.join(map(str, fehlend))} ging nicht mit (kein Text, nicht als Bild geschickt) — "
               "Fragen von dort fehlen im Test.")
for s in satz.get("uebersprungen") or []:
    st.warning(f"Nicht übertragen: {s}")
if ohne := st.session_state.get("bilder_ohne_frage"):
    st.info(f"🖼 Keiner Frage zugeordnet und deshalb nicht im Test: {', '.join(ohne)}. "
            "Gehört eines zu einer Frage, im YAML bei `bilder:` ergänzen (Pfad `bilder/<name>`).")
unsicher = [f for f in fragen if f.get("unsicher")]
if unsicher:
    st.warning(f"{len(unsicher)} Frage(n) mit Unsicherheit — in der Tabelle markiert, bitte prüfen.")

st.dataframe(
    [{"⚠": "⚠" if f.get("unsicher") else "", "Sektion": sek, "Titel": f.get("titel"), "Typ": f.get("typ"),
      "Punkte": f.get("punkte"), "Medien": "🎬 " * len(f.get("medien") or [])
      + "🖼 " * len(f.get("bilder") or []),
      "Lösung": umwandeln.loesung_kurz(f),
      "Quelle": f.get("quelle", ""), "Unsicher": f.get("unsicher", "")} for sek, f in paare],
    width="stretch", hide_index=True)

if st.session_state.get("bilder"):
    with st.expander("Bilder je Frage ansehen"):
        for sek, f in paare:
            for b in f.get("bilder") or []:
                name = (b["datei"] if isinstance(b, dict) else b).removeprefix("bilder/")
                if name in st.session_state["bilder"]:
                    st.image(st.session_state["bilder"][name], width=320,
                             caption=f"{f.get('titel')} — {b.get('alt', '') if isinstance(b, dict) else ''}")

with st.expander("Fragensatz bearbeiten (YAML)"):
    st.caption("Format: siehe README von olat-qti. Nach dem Ändern «Übernehmen», dann neu bauen.")
    neu = st.text_area("YAML", st.session_state["yaml"], height=500, label_visibility="collapsed")
    if st.button("Übernehmen") and neu != st.session_state["yaml"]:
        st.session_state["yaml"] = neu
        st.session_state.pop("zip", None)
        st.rerun()

# ------------------------------------------------------------------ bauen
if st.button("Zip für OLAT bauen", type="primary"):
    with tempfile.TemporaryDirectory() as tmp:
        quelle = Path(tmp) / "fragen.yaml"
        quelle.write_text(st.session_state["yaml"], encoding="utf-8")
        if st.session_state.get("bilder"):
            (Path(tmp) / "bilder").mkdir()
            for name, daten in st.session_state["bilder"].items():
                (Path(tmp) / "bilder" / name).write_bytes(daten)
        ziel = Path(tmp) / "test.zip"
        try:
            info = olatqti.baue_paket(quelle, ziel)
            befunde = olatqti.pruefe_paket(ziel)
        except (olatqti.FehlerImFragensatz, KeyError, TypeError, ValueError) as e:
            st.error(f"Fragensatz fehlerhaft: {e} — im YAML korrigieren und neu bauen.")
            st.stop()
        if befunde:
            st.error("Paketprüfung: " + " · ".join(befunde))
            st.stop()
        # Gegenprobe: jedes Bild des Fragensatzes muss im Zip stecken. Fehlte am 22.09.2026 unbemerkt,
        # weil der laufende Server einen alten Konverter ohne Bildunterstützung im Speicher hatte.
        gewollt = {(b["datei"] if isinstance(b, dict) else b).rsplit("/", 1)[-1]
                   for _, f in paare for b in f.get("bilder") or []}
        with zipfile.ZipFile(ziel) as zz:
            fehlend = gewollt - set(zz.namelist())
        if fehlend:
            st.error(f"Bilder fehlen im Zip: {', '.join(sorted(fehlend))}. Die App muss neu gestartet werden "
                     "(der Konverter wurde geändert, während sie lief).")
            st.stop()
        st.session_state["zip"] = ziel.read_bytes()
        st.session_state["zip_info"] = info

if "zip" in st.session_state:
    info = st.session_state["zip_info"]
    name = st.session_state.get("pdf_name", "test")
    typen = ", ".join(f"{k} {n}" for k, n in info["typen"].items())
    st.success(f"Bereit: {info['fragen']} Fragen, {info['punkte']:g} Punkte ({typen}). "
               "Import: OLAT → Autorenbereich → Importieren → Zip wählen → «Test».")
    a, b = st.columns(2)
    a.download_button("Zip herunterladen", st.session_state["zip"], f"{name}.zip", "application/zip", type="primary")
    if st.session_state.get("bilder"):
        puffer = io.BytesIO()
        with zipfile.ZipFile(puffer, "w", zipfile.ZIP_DEFLATED) as zq:
            zq.writestr(f"{name}.yaml", st.session_state["yaml"])
            for bn, daten in st.session_state["bilder"].items():
                zq.writestr(f"bilder/{bn}", daten)
        b.download_button("YAML + Bilder herunterladen", puffer.getvalue(), f"{name}_quelle.zip", "application/zip")
    else:
        b.download_button("YAML herunterladen", st.session_state["yaml"].encode("utf-8"), f"{name}.yaml", "text/yaml")
