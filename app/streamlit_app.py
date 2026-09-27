"""OLAT-Test erstellen — Streamlit-App: aus PDF (OpenAI) oder aus eingefügtem YAML (eigene KI).

    cd dev/olat-qti/app && .venv/Scripts/python -m streamlit run streamlit_app.py
"""
from __future__ import annotations

import html
import importlib
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

# olatqti.py liegt ausserhalb von app/ — Streamlit lädt es nach einem Push nicht selbst neu, die Cloud
# baute sonst mit dem alten Konverter weiter (23.09.2026: Formatierung als rohe ** in OLAT)
olatqti = importlib.reload(olatqti)

import auth  # noqa: E402
import zaehler  # noqa: E402
import umwandeln  # noqa: E402
import formelcheck  # noqa: E402

# Versionsmarke oben auf jeder Seite: zeigt, welche Fassung online läuft. «v_experimental» = mit SRF-Links → mp3
# (Commit «SRF-Links …»); nimmt git revert dieses Commits zurück, verschwindet die Marke mit.
VERSION = "v_experimental"
st.set_page_config(page_title=f"OLAT-Test erstellen ({VERSION})", page_icon="📝", layout="wide")
st.caption(f"🧪 **{VERSION}**")

# Der Konverter liegt ausserhalb des app-Ordners. Läuft eine alte Fassung im Speicher, entstehen still
# falsche Pakete (22.09.2026: Formeln blieben als $…$ stehen, Bilder fehlten). Lieber hart stoppen.
KONVERTER_BRAUCHT = ("inline", "js_escape", "anhaengen", "mit_bildern", "steuerzeichen", "bloecke", "pro_antwort",
                     "formel_um_stellen", "srg_mp3")
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
            g1, g2, g3, g4 = st.columns(4)
            g1.metric("Umwandlungen total", sum(z["umwandlungen"] for z in zeilen))
            g2.metric("davon PDF / YAML", f"{sum(z['pdf'] for z in zeilen)} / {sum(z['yaml'] for z in zeilen)}")
            g3.metric("Kosten total", f"${sum(float(z['kosten_usd']) for z in zeilen):.2f}")
            g4.metric("Lehrpersonen", len(zeilen))
            st.dataframe([{"Lehrperson": z["nutzer"], "Umwandlungen": z["umwandlungen"],
                           "PDF": z["pdf"], "YAML": z["yaml"],
                           "Kosten": f"${float(z['kosten_usd']):.2f}",
                           "Tokens": f"{z['eingabe'] + z['ausgabe']:,}".replace(",", "'"),
                           "zuletzt": (z["letzte"] or "")[:16].replace("T", " ")} for z in zeilen],
                         width="stretch", hide_index=True)
            st.caption("Gezählt werden nur Zahlen: wer, wann, Modell, Tokens, Kosten, Anzahl Fragen, "
                       "Seiten und Bilder, sowie ob per PDF (OpenAI) oder YAML (eigene KI) umgewandelt "
                       "wurde. Keine Fragetexte, keine PDFs.")

MODELL = "gpt-5.6-luna"          # im Vergleich vom 22.09.2026 zuverlässig und am günstigsten
PROMPT = (Path(__file__).parent / "prompt_extern.md").read_text(encoding="utf-8")
BEISPIEL_PDF = Path(__file__).parent.parent / "beispiele" / "Ideale_Gase_Videotest_mit_Loesungen.pdf"


with st.container(border=True):
    st.markdown(
        "**Was diese Seite macht:** Aus Ihrem PDF mit Fragen **und Lösungen** entsteht ein **Zip-Paket**, "
        "das Sie in OLAT im **Autorenbereich → Importieren** hochladen und als **Test** anlegen. "
        "Fragetypen, Punkte, Lösungen, Musterlösungen und Formeln kommen mit.\n\n"
        "- 🖼 **Bilder aus dem PDF** (Diagramme, Schemas, Fotos) landen bei der Frage, bei der sie stehen. "
        "Logos auf jeder Seite und kleine Symbole werden weggelassen.\n"
        "- 🎬 **Video- und Audio-Links im PDF** (YouTube, nanoo.tv, mp3) werden erkannt — auch solche, die "
        "hinter einem Wort verlinkt sind — und erscheinen in OLAT als Player.\n"
        "- ✅ Vor dem Herunterladen sehen Sie jede Frage mit ihrer Lösung und können den Fragensatz ändern.")
    if BEISPIEL_PDF.is_file():
        b1, b2 = st.columns([1, 3])
        b1.download_button("Beispiel-PDF herunterladen", BEISPIEL_PDF.read_bytes(),
                           BEISPIEL_PDF.name, "application/pdf")
        b2.caption("«Ideale Gase» — 15 Fragen mit Video, drei Bildern, Formeln und offenen Aufgaben. "
                   "Laden Sie es unten hoch, um den ganzen Weg bis zum OLAT-Import auszuprobieren. "
                   "[Im Repo ansehen](https://github.com/aburossi/olat-qti-app/blob/main/beispiele/"
                   "Ideale_Gase_Videotest_mit_Loesungen.pdf)")


def neuer_satz(text: str, name: str, verbrauch=None, fehlende_seiten=None,
               bilder: dict[str, bytes] | None = None, ohne_frage: list[str] | None = None) -> None:
    st.session_state["yaml"] = text
    st.session_state["pdf_name"] = name
    st.session_state["verbrauch"] = verbrauch
    st.session_state["fehlende_seiten"] = fehlende_seiten or []
    st.session_state["bilder"] = bilder or {}          # Dateiname -> Bytes, liegt im Zip unter bilder/
    st.session_state["bilder_ohne_frage"] = ohne_frage or []
    st.session_state["formeln"] = None  # Ergebnis der Formelprüfung nach einer PDF-Umwandlung
    st.session_state["nicht_uebernommen"] = []  # Sätze aus dem PDF, die im Fragensatz fehlen
    st.session_state.pop("zip", None)


def tabelle_mit_umbruch(zeilen: list[dict], breite_spalten: set[str] = frozenset()) -> str:
    """Fragenübersicht als HTML-Tabelle mit Zeilenumbruch in den Zellen — st.dataframe schneidet lange
    Titel und Lösungen ab, statt sie umzubrechen (25.09.2026)."""
    if not zeilen:
        return "<p><em>Keine Fragen.</em></p>"
    spalten = list(zeilen[0].keys())
    kopf = "".join(f"<th>{html.escape(s)}</th>" for s in spalten)
    zeilen_html = "".join(
        "<tr>" + "".join(
            f'<td class="breit">{html.escape(str(z.get(s) or ""))}</td>' if s in breite_spalten
            else f"<td>{html.escape(str(z.get(s) or ''))}</td>"
            for s in spalten) + "</tr>"
        for z in zeilen)
    return (
        "<style>.olat-fragen table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }"
        ".olat-fragen th, .olat-fragen td { border: 1px solid rgba(128, 128, 128, 0.3); padding: 6px 10px; "
        "text-align: left; vertical-align: top; white-space: pre-wrap; word-break: break-word; }"
        ".olat-fragen td.breit { min-width: 240px; } .olat-fragen th { font-weight: 600; }</style>"
        f'<div class="olat-fragen"><table><thead><tr>{kopf}</tr></thead><tbody>{zeilen_html}</tbody></table></div>')


VORLAGE_PDF = Path(__file__).parent.parent / "beispiele" / "Vorlage_Fragetypen_mit_Loesungen.pdf"

# Erprobt am 23.09.2026 (beispiele/pdf_typangaben.py, Prüfungssimulation 4PR26b) — bei Änderungen an
# umwandeln.SYSTEM hier nachziehen
TIPPS_PDF = """
**1. Fragetyp in die Überschrift der Aufgabe schreiben** — der zuverlässigste Weg zum gewünschten Typ:
`Aufgabe 3 – Lückentext (2 Punkte)`. Die Angabe geht vor, auch wenn die Form mehrdeutig ist
(Multiple Choice mit nur einer richtigen Antwort, «Richtig/Falsch» mit genau 4 Aussagen).

| Schreiben Sie | ergibt in OLAT |
|---|---|
| Single Choice · Multiple Choice | Einfach- / Mehrfachauswahl |
| Kprim · Richtig/Falsch | 4 Aussagen mit Teilpunkten · beliebig viele Aussagen |
| Zuordnung (Matrix) · Drag and Drop | Tabelle zum Ankreuzen · Begriffe in Gruppen ziehen |
| Reihenfolge | Elemente sortieren |
| Lückentext · Zahl · Dropdown | Texteingabe · Zahl mit Toleranz · Auswahl in der Lücke |
| Hottext | Wörter im Text anklicken |
| Freitext · Upload | offene Antwort mit Musterlösung · Datei abgeben |

**2. Punkte** in Klammern in die Überschrift: `(2 Punkte)`. Fehlen sie, gilt 1 Punkt (Freitext 2).

**3. Lösungen rot** schreiben — die App erkennt Rot als Lösung:
- Auswahl: die richtige Option ankreuzen (☒) und rot färben.
- Lückentext: das Lösungswort rot **direkt in die Lücke**, im ganzen Satz. Varianten mit «/»: `Bern / Berne`.
- Dropdown: Optionen in Klammern, die richtige rot: `dauert höchstens (1 / 3 / 6) Monate`.
- Zahl: Ergebnis rot, Toleranz dazu: `42,5 (±0,5)`. Ohne Toleranz gilt ±1 %.
- Hottext: die richtigen Wörter rot. Reihenfolge: `Lösung: A → B → C`.
- Freitext: die Musterlösung rot unter die Frage.
- Anderen Text **nicht** rot färben — sonst hält die App ihn für eine Lösung.

**4. Teile als Überschriften** (`Teil A – Grundlagen`) werden Sektionen in OLAT. Ein Fallbeispiel, das für
mehrere Fragen gilt, steht in jeder dieser Fragen.

**5. Formatierung:** Fett, kursiv und Aufzählungen kommen mit. Schriftgrösse und Farben nicht.
Texte **mit Zeilennummern** (Nummer am Zeilenanfang), **Tabellen mit Werten** und **Zwischentitel**:
unten das Häkchen «Besondere Formatierung übernehmen» setzen.

**6. Bilder und Medien:** Bilder direkt bei der Frage platzieren. Video/Audio als Link (YouTube, nanoo.tv,
mp3) in die Frage — ausgeschrieben oder hinter einem Wort.

**7. Das PDF selbst:** Aus Word/PowerPoint mit «Als PDF speichern», nicht gescannt — Scans gehen, sind aber
unsicherer und teurer. Fragen, bei denen man **im Bild** klickt oder zeichnet, werden übersprungen.

**Nie im PDF:** Antworten, Namen oder Noten von Lernenden — der Text geht an OpenAI.
"""


def tipps_pdf() -> None:
    with st.expander("📋 So formatieren Sie Ihr PDF — Tipps für ein gutes Ergebnis"):
        st.markdown(TIPPS_PDF)
        if VORLAGE_PDF.is_file():
            v1, v2 = st.columns([1, 3])
            v1.download_button("Vorlage herunterladen", VORLAGE_PDF.read_bytes(), VORLAGE_PDF.name,
                               "application/pdf", key="vorlage_pdf")
            v2.caption("14 Aufgaben, je mit Fragetyp in der Überschrift und roter Lösung — alle 13 Typen der "
                       "App. Als Muster für eigene Prüfungen oder zum Ausprobieren.")


def openai_zugaenge(email: str) -> list[tuple[str | None, str]]:
    """[(Schlüssel, Abrechnung), …] in der Reihenfolge, in der sie versucht werden: eigener Schlüssel einer
    anderen Schule, wenn das Konto dort aufgeführt ist — mit `rueckfall = true` danach der bbw-Schlüssel
    (BMS hatte am 23.09.2026 kein Guthaben); sonst nur der bbw-Schlüssel. In den Secrets:
        [schluessel.bms]
        name = "BMS"
        api_key = "sk-…"
        konten = ["testuser@bms-w.ch"]
        rueckfall = true"""
    email = (email or "").strip().lower()
    bbw = (st.secrets.get("openai", {}).get("api_key") or None, "bbw")
    for kuerzel, eintrag in (st.secrets.get("schluessel", {}) or {}).items():
        if email in {str(k).strip().lower() for k in eintrag.get("konten", [])}:
            eigen = (eintrag.get("api_key") or None, str(eintrag.get("name", kuerzel)))
            return [eigen, bbw] if eintrag.get("rueckfall") else [eigen]
    return [bbw]


def schluessel_problem(e: Exception) -> bool:
    """Liegt es am Schlüssel (kein Guthaben, ungültig) statt am PDF oder am Netz? Nur dann auf den nächsten."""
    text = f"{getattr(e, 'code', '')} {getattr(e, 'status_code', '')} {e}".lower()
    return any(w in text for w in ("insufficient_quota", "billing", "invalid_api_key", "401", "quota"))


def aus_pdf() -> None:
    modell = MODELL
    st.info("Nur Tests mit Fragen und Lösungen hochladen — **keine Antworten von Lernenden, keine Namen, "
            "keine Noten**. Der Text des PDFs wird zur Umwandlung an OpenAI geschickt.")
    st.caption("🎬 **Video oder Audio einbetten:** Bei der Frage im PDF einen Link auf YouTube, nanoo.tv oder "
               "eine mp3-Datei hinschreiben — ausgeschrieben oder hinter einem Wort verlinkt. In OLAT erscheint "
               "er als Player unter dem Fragetext. Der Link muss für Lernende ohne Anmeldung erreichbar sein.")
    st.caption("🖼 **Bilder** (Diagramme, Schemas, Fotos) werden aus dem PDF übernommen und der Frage zugeordnet, "
               "bei der sie stehen. Logos auf jeder Seite und kleine Symbole werden ausgelassen.")
    tipps_pdf()
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

    erweitert = st.checkbox(
        "Besondere Formatierung übernehmen — Texte mit Zeilennummern, Tabellen, Zwischentitel",
        help="Ohne Haken: Fett, Kursiv und Aufzählungen werden übernommen, Zeilen zu Fliesstext verbunden, "
             "Tabellen als Aufzählung. Mit Haken: Jede Zeile eines nummerierten Texts bleibt eine eigene Zeile "
             "(z. B. für Fragen wie «Geben Sie die Zeile an»), Tabellen bleiben Tabellen, Zwischentitel werden "
             "Überschriften. Schriftgrösse und Farbe gehen in beiden Fällen nicht mit.")
    zugaenge = openai_zugaenge(nutzer["email"])
    if zugaenge[0][1] != "bbw":
        rueck = " — ohne Guthaben dort über den Schlüssel der bbw" if len(zugaenge) > 1 else ""
        st.caption(f"Die Umwandlung läuft über den OpenAI-Schlüssel der {zugaenge[0][1]}{rueck}.")
    if not st.button("In Fragen umwandeln", type="primary"):
        return
    if not any(s for s, _ in zugaenge):
        st.error(f"In den Secrets fehlt der OpenAI-Schlüssel ({zugaenge[0][1]}). Ergänzen:\n\n"
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
        kandidaten = [(s, n) for s, n in zugaenge if s]
        for i, (schluessel, abrechnung) in enumerate(kandidaten):
            try:
                roh, verbrauch = umwandeln.frage_openai(
                    OpenAI(api_key=schluessel), modell, text, bilder, erweitert=erweitert)
                break
            except Exception as e:  # Netz, Schlüssel, Kontingent, Abbruch — alles dem Menschen zeigen
                if i + 1 < len(kandidaten) and schluessel_problem(e):
                    st.info(f"Der OpenAI-Schlüssel der {abrechnung} ist nicht nutzbar (kein Guthaben oder "
                            f"ungültig) — die Umwandlung läuft über den Schlüssel der {kandidaten[i + 1][1]}.")
                    continue
                st.error(f"Umwandlung fehlgeschlagen: {e}")
                return
    if zugaenge[0][1] != "bbw" and abrechnung != zugaenge[0][1] and not zugaenge[0][0]:
        st.info(f"Für die {zugaenge[0][1]} ist kein OpenAI-Schlüssel hinterlegt — umgewandelt über die {abrechnung}.")
    satz = umwandeln.zu_fragensatz(roh, erweitert=erweitert)
    umwandeln.pruefe_medien(satz, text)
    umwandeln.medien_verteilen(satz)
    # Formelprüfung: sicher reparieren, Rest einmal gezielt an das Modell, was bleibt als ⚠ markieren
    formeln = {"repariert": formelcheck.reparieren(satz), "nachgebessert": 0, "offen": 0, "fehler": None}
    if (rest := formelcheck.pruefen(satz)):
        with st.spinner(f"{len(rest)} Text(e) mit Formelfehlern — {modell} bessert nach …"):
            try:
                formeln["nachgebessert"], v2 = formelcheck.nachbessern(OpenAI(api_key=schluessel), modell, rest)
                verbrauch = {k: verbrauch[k] + v2[k] for k in ("eingabe", "ausgabe")}
            except Exception as e:  # Nachbessern ist ein Zusatz — scheitert es, bleibt die Umwandlung gültig
                formeln["fehler"] = str(e)
        formeln["offen"] = formelcheck.markieren(formelcheck.pruefen(satz))
    ohne_frage = umwandeln.pruefe_bilder(satz, {f["name"] for f in funde})
    neuer_satz(umwandeln.als_yaml(satz), Path(pdf.name).stem,
               {**verbrauch, "modell": modell}, [s["nr"] for s in problemseiten] if not bildseiten else [],
               {f["name"]: f["daten"] for f in funde}, ohne_frage)
    st.session_state["formeln"] = formeln
    st.session_state["nicht_uebernommen"] = umwandeln.nicht_uebernommen(text, satz)
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
teile_im_yaml = isinstance(satz, dict) and "teile" in satz  # Aufbau selbst geschrieben → App gliedert nicht um
sektionen = [] if teile_im_yaml or not isinstance(satz, dict) else umwandeln.sektionen_von(satz)
anzahl_sektionen = (sum(len(umwandeln.sektionen_von(t)) for t in satz["teile"] or []) if teile_im_yaml
                    else len(sektionen) or 1)
v = st.session_state.get("verbrauch")
st.subheader(f"«{satz.get('titel', '?')}» — {len(fragen)} Fragen in {anzahl_sektionen} "
             f"Sektion{'en' if anzahl_sektionen > 1 else ''}, "
             f"{sum(umwandeln.punkte_von(f) for f in fragen):g} Punkte")
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
        if (preis := umwandeln.PREISE.get(modell)):
            st.caption(f"Modell: **{modell}** — ${preis[0]:.2f} pro Million Eingabe-Tokens, "
                       f"${preis[1]:.2f} pro Million Ausgabe-Tokens.")
        if fehler := st.session_state.get("zaehler_fehler"):
            st.caption(f"⚠ {fehler} — das Zip ist davon nicht betroffen.")
if fehlend := st.session_state.get("fehlende_seiten"):
    st.warning(f"Seite {', '.join(map(str, fehlend))} ging nicht mit (kein Text, nicht als Bild geschickt) — "
               "Fragen von dort fehlen im Test.")
for s in satz.get("uebersprungen") or []:
    st.warning(f"Nicht übertragen: {s}")
if (fm := st.session_state.get("formeln")) and (fm["repariert"] or fm["nachgebessert"] or fm["offen"] or fm["fehler"]):
    teile_fm = [f"{fm['repariert']} Text(e) automatisch repariert" if fm["repariert"] else "",
                f"{fm['nachgebessert']} vom Modell nachgebessert" if fm["nachgebessert"] else "",
                f"{fm['offen']} Frage(n) bitte prüfen (⚠ in der Tabelle)" if fm["offen"] else ""]
    (st.warning if fm["offen"] else st.info)("🧮 Formeln: " + ", ".join(t for t in teile_fm if t) + "."
                                             + (f" Nachbessern fehlgeschlagen: {fm['fehler']}" if fm["fehler"] else ""))
if isinstance(satz, dict) and (fm_rest := formelcheck.pruefen(satz)):
    # Stand des aktuellen YAML (auch nach Bearbeiten oder eingefügt): nur melden, nichts ändern
    with st.expander(f"🧮 {len(fm_rest)} Text(e) mit Formelfehlern — in OLAT erscheint dort LaTeX-Code"):
        for f in fm_rest:
            st.markdown(f"- **{f['ort']}**: " + "; ".join(f"`{b}`" for b in f["befunde"]))
if fehlt := st.session_state.get("nicht_uebernommen"):
    with st.expander(f"⚠ {len(fehlt)} Satz/Sätze aus dem PDF fehlen im Test — bitte prüfen", expanded=True):
        st.caption("Das Modell hat diese Stellen nicht übernommen (z. B. einen Lesetext für einzelne Aufgaben). "
                   "Gehören sie dazu, im YAML bei der Frage (`frage:`) oder als Einleitung der Sektion (`text:`) ergänzen.")
        for x in fehlt:
            st.markdown(f"- {x}")
if ohne := st.session_state.get("bilder_ohne_frage"):
    st.info(f"🖼 Keiner Frage zugeordnet und deshalb nicht im Test: {', '.join(ohne)}. "
            "Gehört eines zu einer Frage, im YAML bei `bilder:` ergänzen (Pfad `bilder/<name>`).")
unsicher = [f for f in fragen if f.get("unsicher")]
if unsicher:
    st.warning(f"{len(unsicher)} Frage(n) mit Unsicherheit — in der Tabelle markiert, bitte prüfen.")

def _medien(x: dict) -> str:
    return "🎬 " * len(x.get("medien") or []) + "🖼 " * len(x.get("bilder") or [])


zeilen = []
for titel_sek, sek_ in (umwandeln.alle_sektionen(satz) if isinstance(satz, dict) else []):
    if sek_.get("text") or sek_.get("medien") or sek_.get("bilder"):
        # Einleitung: steht in OLAT über jeder Frage dieser Sektion
        zeilen.append({"⚠": "⚠" if sek_.get("unsicher") else "", "Sektion": titel_sek,
                       "Titel": "Einleitung — über jeder Frage: " + umwandeln.kurz(sek_.get("text"), 300),
                       "Typ": "Einleitung", "Punkte": "", "Medien": _medien(sek_), "Lösung": "", "Quelle": "",
                       "Unsicher": sek_.get("unsicher", "")})
    for f in sek_.get("fragen") or []:
        zeilen.append({"⚠": "⚠" if f.get("unsicher") else "", "Sektion": titel_sek, "Titel": f.get("titel"),
                       "Typ": f.get("typ"), "Punkte": f"{umwandeln.punkte_von(f):g}", "Medien": _medien(f),
                       "Lösung": umwandeln.loesung_kurz(f),
                       "Quelle": f.get("quelle", ""), "Unsicher": f.get("unsicher", "")})
st.markdown(tabelle_mit_umbruch(zeilen, breite_spalten={"Titel", "Lösung", "Unsicher"}), unsafe_allow_html=True)

# Sektionen (Einleitung) und Fragen, die Bilder tragen — für Vorschau und Gegenprobe im Zip
bildtraeger = [(f"{t} — Einleitung", s) for t, s in (umwandeln.alle_sektionen(satz) if isinstance(satz, dict) else [])
               if s.get("bilder")] + [(f.get("titel"), f) for _, f in paare]

if st.session_state.get("bilder"):
    with st.expander("Bilder je Frage ansehen"):
        for titel_b, f in bildtraeger:
            for b in f.get("bilder") or []:
                name = (b["datei"] if isinstance(b, dict) else b).removeprefix("bilder/")
                if name in st.session_state["bilder"]:
                    st.image(st.session_state["bilder"][name], width=320,
                             caption=f"{titel_b} — {b.get('alt', '') if isinstance(b, dict) else ''}")

YAML_HILFE = """
Jede Frage ist ein Block, der mit `- typ:` beginnt und unter `fragen:` eingerückt ist (oder unter
`sektionen:` → `fragen:`, wenn es mehrere Teile gibt). **Einrücken nur mit Leerzeichen, nie mit Tab**
— zwei Leerzeichen pro Ebene reichen, und alle Zeilen eines Blocks müssen gleich weit eingerückt sein.

**Text ändern:** den Wert hinter dem Doppelpunkt ersetzen, z. B. `titel: Hauptstadt` →
`titel: Hauptstadt der Schweiz`. Enthält der Text selbst einen Doppelpunkt oder ein Komma, ihn in
Anführungszeichen setzen: `titel: "Bern: die Hauptstadt"` — sonst meldet die App ungültiges YAML.

**Punkte ändern:** `punkte: 1` auf die gewünschte Zahl setzen (auch mit Punkt statt Komma: `punkte: 1.5`).

**Richtige Antwort ändern** — bei Single/Multiple Choice, Kprim, Richtig/Falsch: `richtig: true` auf
die neue richtige Option setzen, bei den bisherigen auf `false` (oder ganz weglassen; bei Multiple
Choice dürfen mehrere `true` sein):
```yaml
antworten:
  - {text: Bern, richtig: true}
  - Zürich
```

**Antwortoption hinzufügen/entfernen:** eine Zeile mit `- ` dazu- oder wegnehmen, gleich eingerückt
wie die anderen in derselben Liste (`antworten`, `aussagen`, `elemente`, …).

**Frage hinzufügen:** einen ganzen Frageblock kopieren (von `- typ:` bis zur Zeile vor dem nächsten
`- typ:`), einfügen und Titel/Text/Antworten anpassen. **Frage löschen:** denselben Block ganz entfernen.

Nach jeder Änderung unten **«Übernehmen»** klicken — bei ungültigem YAML meldet die App sofort, wo
es hakt (meist eine fehlende Einrückung oder ein fehlendes Anführungszeichen), ohne etwas zu verwerfen.

**Felder je Fragetyp (Kurzübersicht):**

| Typ | Felder |
|---|---|
| Single / Multiple Choice (`sc` / `mc`) | `antworten: [{text, richtig}]` |
| Kprim | genau 4 `aussagen: [{text, richtig}]` |
| Richtig/Falsch (`matchtruefalse`) | `aussagen: [{text, richtig}]` |
| Matrix / Drag and Drop (`match` / `matchdraganddrop`) | `zeilen`, `spalten`, `loesung: {Zeile: Spalte}` |
| Reihenfolge (`order`) | `elemente` in der richtigen Reihenfolge |
| Lückentext (`fib`) | `text` mit `{{Lösung}}`, mehrere Varianten mit `\\|`: `{{Bern\\|Berne}}` |
| Zahl (`numerical`) | `text` mit `{{#100}}` oder mit Toleranz `{{#100±0.5}}` |
| Dropdown (`inlinechoice`) | `text` mit `{{*richtig\\|falsch}}` — `*` markiert die richtige Option |
| Hottext | `text` mit `[[Wort]]`, richtige als `[[*Wort]]` |
| Freitext (`essay`) | `frage`, dazu `musterloesung`; `einfuegen: false` sperrt Kopieren/Einfügen |
| Gemischt (`gapmixed`) | alle Lückenarten; Punkte je Lückenart mit `punkte_dropdown: 1`, `punkte_text: 2` (dann `punkte` weglassen), `laenge: 150` für eine Begründungslücke |
| Upload | `frage` |

Bilder: `bilder: [{datei, alt}]` (Datei liegt im Zip unter `bilder/`). Medien (Video/Audio):
`medien: ["https://…"]`.

**Einleitung einer Sektion:** `text:`, `medien:` und `bilder:` direkt bei der Sektion (neben `titel:`) —
OLAT zeigt sie über jeder Frage dieser Sektion. Teile, Zeitlimit, Bestehensgrenze und Konfiguration wählen
Sie unten in «Testaufbau und Einstellungen», nicht im YAML. Ausführliche Beschreibung mit allen Feldern, Beispielen und Sonderfällen:
README von olat-qti (`https://github.com/aburossi/olat-qti-app`).
"""


with st.expander("Fragensatz bearbeiten (YAML)"):
    with st.expander("📖 Wie ändere ich das YAML?"):
        st.markdown(YAML_HILFE)
    st.caption("Nach dem Ändern «Übernehmen», dann neu bauen.")
    neu = st.text_area("YAML", st.session_state["yaml"], height=500, label_visibility="collapsed")
    if st.button("Übernehmen") and neu != st.session_state["yaml"]:
        st.session_state["yaml"] = neu
        st.session_state.pop("zip", None)
        st.rerun()

# ------------------------------------------------------------------ bewerten
def _zip_veraltet() -> None:
    st.session_state.pop("zip", None)


with st.container(border=True):
    st.markdown("**Bewertung**")
    pro_antwort = st.radio(
        "Bewertung", ["Punkte pro richtige Antwort", "Punkte nur, wenn alles richtig ist"],
        key="bewertung", on_change=_zip_veraltet, label_visibility="collapsed",
        help="Pro richtige Antwort: Die Punkte einer Frage werden auf ihre richtigen Antworten, Zuordnungen, "
             "Aussagen und Lücken verteilt (Teilpunkte). Alles richtig: volle Punkte nur bei ganz richtiger "
             "Antwort, sonst 0.") == "Punkte pro richtige Antwort"
    abzug = st.checkbox(
        "Falsche Antworten geben Abzug (die Hälfte einer richtigen)", value=True, key="abzug",
        on_change=_zip_veraltet, disabled=not pro_antwort,
        help="Ohne Abzug bringt «alles ankreuzen» bei Multiple Choice die volle Punktzahl. "
             "Unter 0 fällt eine Frage nie. Bei Lücken gibt es nie Abzug.")
    st.caption("Gilt für Multiple Choice, Matrix, Drag and Drop, Richtig/Falsch, Hottext und alle Lückentexte "
               "(auch gemischte). Vergibt das PDF je Lückenart eigene Punkte (z. B. Wahl 1 P., Begründung 2 P.), "
               "gelten diese. Single Choice, Kprim, Hotspot und Reihenfolge haben eigene, feste Regeln. "
               "Nennt das PDF bei einer Frage etwas anderes, gilt dort das PDF.")
KONFIG_TEXT = {
    "neutral": "Neutral — pausieren möglich, kein Feedback, keine Resultate für Lernende",
    "formativ": "Formativ — Feedback und Punktestand, nach Abschluss Resultate mit Lösungen",
    "summativ": "Summativ — ein Versuch, nicht pausierbar, nach Abschluss nur die Punktzahl",
}
gesamtpunkte = sum(umwandeln.punkte_von(f) for f in fragen)

with st.container(border=True):
    st.markdown("**Testaufbau und Einstellungen**")
    neue_teile_ab, eine_sektion = [], False
    if teile_im_yaml:
        st.caption(f"Teile und Sektionen stehen im YAML ({len(satz['teile'] or [])} Teile) und werden so übernommen.")
    elif len(sektionen) > 1:
        eine_sektion = not st.checkbox(
            f"Mehrere Sektionen ({len(sektionen)}, wie erkannt)", value=True, key="mehrere_sektionen",
            on_change=_zip_veraltet,
            help="Aus: alle Fragen in einer einzigen Sektion. Sektionen erscheinen in OLAT als Gliederung links.")
        mehrere_teile = st.checkbox(
            "Mehrere Teile", value=False, key="mehrere_teile", on_change=_zip_veraltet, disabled=eine_sektion,
            help="Ein Teil wird in OLAT abgeschlossen, bevor der nächste beginnt — zurück geht es dann nicht mehr.")
        if mehrere_teile and not eine_sektion:
            namen = [f"{i + 1}. {s.get('titel') or 'Sektion'}" for i, s in enumerate(sektionen)]
            ab = st.multiselect("Neuer Teil beginnt bei Sektion", namen[1:], key="teile_ab", on_change=_zip_veraltet,
                                placeholder="Sektion wählen, mit der Teil 2 (3, …) beginnt")
            neue_teile_ab = [namen.index(n) for n in ab]
            if not ab:
                st.caption("Noch keine Sektion gewählt — der Test bleibt ein Teil.")
            else:
                st.caption(f"→ {len(ab) + 1} Teile")
    konfig = st.selectbox("Konfiguration", list(KONFIG_TEXT), format_func=KONFIG_TEXT.get, key="konfig",
                          on_change=_zip_veraltet,
                          help="Testeinstellungen in OLAT; lassen sich dort nach dem Import noch ändern.")
    einfuegen = not st.checkbox(
        "Einfügen in Freitexten sperren (kein Copy-Paste)", value=False, key="einfuegen_sperren",
        on_change=_zip_veraltet, disabled=not any(str(f.get("typ")) in ("essay", "freitext") for f in fragen),
        help="Lernende können in Freitext-Antworten nichts einfügen — sie müssen selbst schreiben. "
             "Eine Frage mit «einfuegen: true» im YAML bleibt offen.")
    srg_aufloesen = st.checkbox(
        "SRF-Links in abspielbare mp3 umwandeln", value=True, key="srg_mp3", on_change=_zip_veraltet,
        help="Der OLAT-Player spielt SRF-Play- und SRF-Audio-Seiten nicht, nur die mp3 dahinter. Die App holt sie "
             "über die SRG-Schnittstelle. Ausschalten, wenn das stört — dann bleiben die Links, wie sie sind.")
    z1, z2 = st.columns(2)
    zeitlimit = bestehen = None
    if z1.checkbox("Zeitlimit", value=False, key="mit_zeitlimit", on_change=_zip_veraltet):
        zeitlimit = z1.number_input("Minuten", min_value=1, max_value=600, value=45, step=5, key="zeitlimit",
                                    on_change=_zip_veraltet)
    if z2.checkbox("Bestehensgrenze", value=False, key="mit_bestehen", on_change=_zip_veraltet,
                   disabled=not gesamtpunkte):
        bestehen = z2.number_input(f"Bestanden ab … Punkten (von {gesamtpunkte:g})", min_value=0.0,
                                   max_value=float(gesamtpunkte), value=round(gesamtpunkte * 0.6 * 2) / 2,
                                   step=0.5, key="bestehen", on_change=_zip_veraltet)

yaml_gebaut = umwandeln.mit_aufbau(st.session_state["yaml"], eine_sektion, neue_teile_ab)
yaml_gebaut = umwandeln.mit_bewertung(yaml_gebaut, pro_antwort, abzug)
yaml_gebaut = umwandeln.mit_einstellungen(yaml_gebaut, konfig, zeitlimit, bestehen, einfuegen)


@st.cache_data(ttl=24 * 3600, show_spinner="SRF-Audio wird aufgelöst …")
def _srg_mp3(link: str) -> dict:
    return olatqti.srg_mp3(link)  # Fehler werden nicht gecacht, ein neuer Versuch fragt wieder an


if srg_aufloesen:
    yaml_gebaut, srg_ersetzt, srg_fehler = umwandeln.srg_links_aufloesen(yaml_gebaut, _srg_mp3)
    if srg_ersetzt:
        st.info("🎧 SRF-Links durch die mp3 ersetzt (sonst spielt OLAT sie nicht): "
                + "; ".join(f"«{e['titel']}» ({e['minuten']:g} Min.)" for e in srg_ersetzt))
    for f in srg_fehler:
        st.warning(f"🎧 SRF-Link nicht aufgelöst, bleibt so — in OLAT spielt er vermutlich nicht: {f}")

# ------------------------------------------------------------------ bauen
if st.button("Zip für OLAT bauen", type="primary"):
    with tempfile.TemporaryDirectory() as tmp:
        quelle = Path(tmp) / "fragen.yaml"
        quelle.write_text(yaml_gebaut, encoding="utf-8")
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
                   for _, f in bildtraeger for b in f.get("bilder") or []}
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
    extra = "".join([f", Zeitlimit {zeitlimit:g} Min." if zeitlimit else "",
                     f", bestanden ab {bestehen:g} Punkten" if bestehen is not None else ""])
    st.success(f"Bereit: {info['fragen']} Fragen, {info['punkte']:g} Punkte ({typen}) — "
               f"{info['teile']} Teil{'e' if info['teile'] > 1 else ''}, {info['sektionen']} "
               f"Sektion{'en' if info['sektionen'] > 1 else ''}, Konfiguration {info['konfig']}{extra}. "
               "Import: OLAT → Autorenbereich → Importieren → Zip wählen → «Test».")
    a, b = st.columns(2)
    a.download_button("Zip herunterladen", st.session_state["zip"], f"{name}.zip", "application/zip", type="primary")
    if st.session_state.get("bilder"):
        puffer = io.BytesIO()
        with zipfile.ZipFile(puffer, "w", zipfile.ZIP_DEFLATED) as zq:
            zq.writestr(f"{name}.yaml", yaml_gebaut)
            for bn, daten in st.session_state["bilder"].items():
                zq.writestr(f"bilder/{bn}", daten)
        b.download_button("YAML + Bilder herunterladen", puffer.getvalue(), f"{name}_quelle.zip", "application/zip")
    else:
        b.download_button("YAML herunterladen", yaml_gebaut.encode("utf-8"), f"{name}.yaml", "text/yaml")
