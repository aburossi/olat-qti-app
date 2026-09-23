"""Klickt die Streamlit-App ohne Browser und ohne echten Login durch (streamlit.testing.AppTest).

Angemeldete Lehrperson wird in session_state gesetzt; keine echten Schlüssel, kein OpenAI-Aufruf.
Prüft: beide Tabs, Modellwahl mit Hinweis, und den Weg «YAML einfügen» bis zum Zip —
mit dem Beispiel aus dem Prompt, eingebettet in eine KI-Antwort mit Codeblock.

    app/.venv/Scripts/python tests/test_app.py
"""
import io
import re
import sys
import zipfile
from pathlib import Path

import yaml
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "app"
sys.path[:0] = [str(APP), str(APP.parent)]
import umwandeln  # noqa: E402
FENCE = "`" * 3


def neu() -> AppTest:
    at = AppTest.from_file(str(APP / "streamlit_app.py"), default_timeout=30)
    at.secrets["app"] = {"url": "http://localhost:8501"}
    at.secrets["supabase"] = {"url": "https://example.supabase.co", "anon_key": "test"}
    at.secrets["openai"] = {"api_key": "test", "model": "gpt-5.6-luna"}
    at.session_state["nutzer"] = {"id": "1", "email": "lp@bbw.ch", "name": "Test LP", "rolle": "lp"}
    return at


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    fehler = []
    at = neu().run()
    if at.exception:
        fehler.append(f"Absturz beim Start: {at.exception[0].value}")
    tabs = [t.label for t in at.tabs]
    if tabs != ["Aus PDF (OpenAI)", "YAML einfügen (eigene KI)"]:
        fehler.append(f"Tabs: {tabs}")
    if at.radio:
        fehler.append("Modellwahl sollte es nicht mehr geben (nur noch gpt-5.6-luna)")
    if not any("So formatieren Sie Ihr PDF" in e.label for e in at.expander) \
            or not any("Fragetyp in die Überschrift" in m.value for m in at.markdown):
        fehler.append("Tipps zum PDF fehlen")
    # Gastkonten ausserhalb der bbw: nur mit Freigabe in den Secrets, Lernendenkonten nie
    for email, rolle, soll in [("test@olat.ch", "gast", True), ("gast@bbw.ch", "gast", False),
                               ("x@lernende.bbw.ch", "lp", False), ("lp@bbw.ch", "lp", True)]:
        a = AppTest.from_file(str(APP / "streamlit_app.py"), default_timeout=30)
        a.secrets["zugang"] = {"gastkonten": ["test@olat.ch"]}
        a.session_state["nutzer"] = {"id": "1", "email": email, "name": "x", "rolle": rolle, "token": ""}
        a.run()
        if any("keinen Zugang" in e.value for e in a.error) == soll:
            fehler.append(f"Zugang {email} ({rolle}): {'gesperrt' if soll else 'zugelassen'}")
    if not (APP.parent / "beispiele" / "Vorlage_Fragetypen_mit_Loesungen.pdf").is_file():
        fehler.append("Vorlage-PDF fehlt in beispiele/")
    seite = " ".join(m.value for m in at.markdown) + " ".join(c.value for c in at.caption)
    for stichwort in ("Autorenbereich", "Importieren", "Zip-Paket", "Bilder aus dem PDF", "nanoo.tv"):
        if stichwort not in seite:
            fehler.append(f"Erklärung ohne «{stichwort}»")
    if not any("Beispiel-PDF" in b.label for b in [*at.button, *at.download_button]):
        fehler.append("Beispiel-PDF wird nicht angeboten")

    # YAML-Weg: KI-Antwort mit Begleittext und Codeblock einfügen
    prompt = (APP / "prompt_extern.md").read_text(encoding="utf-8")
    beispiel = re.search(FENCE + r"yaml\n(.*?)" + FENCE, prompt, re.S)[1]
    beispielsatz = yaml.safe_load(beispiel)
    n_fragen = sum(len(s["fragen"]) for s in beispielsatz["sektionen"])
    n_sek = len(beispielsatz["sektionen"])
    antwort = f"Gerne, hier der Test:\n\n{FENCE}yaml\n{beispiel}{FENCE}\n\nSag Bescheid, wenn du Änderungen willst."
    feld = next(t for t in at.text_area if t.label == "Antwort der KI (YAML)")
    feld.input(antwort)
    next(b for b in at.button if b.key == "yaml_uebernehmen").click()
    at.run()
    if at.exception:
        fehler.append(f"Absturz nach Übernehmen: {at.exception[0].value}")
    if not at.dataframe:
        fehler.append("keine Prüftabelle nach dem Einfügen")
    kopf = " ".join(h.value for h in at.subheader)
    if f"{n_fragen} Fragen in {n_sek} Sektionen" not in kopf:
        fehler.append(f"Kopfzeile: {kopf!r}")
    next(b for b in at.button if b.label == "Zip für OLAT bauen").click()
    at.run()
    erfolg = " ".join(s.value for s in at.success)
    if f"{n_fragen} Fragen" not in erfolg or "zip" not in at.session_state or at.session_state["pdf_name"] != "werkstoffe-lernkontrolle":
        fehler.append(f"kein Zip: {erfolg!r} / {[e.value for e in at.error]}")

    # kaputtes YAML: verständliche Meldung statt Absturz
    at2 = neu().run()
    next(t for t in at2.text_area if t.label == "Antwort der KI (YAML)").input("titel: x\nfragen:\n  - typ: sc\n   falsch")
    next(b for b in at2.button if b.key == "yaml_uebernehmen").click()
    at2.run()
    if at2.exception or not any("kein gültiges YAML" in e.value for e in at2.error):
        fehler.append("kaputtes YAML ohne klare Meldung")

    # Veralteter Konverter im Speicher (so auf der Cloud nach dem Push vom 23.09.2026): die App lädt ihn
    # bei jedem Lauf neu von der Platte, statt still mit der alten Fassung Pakete zu bauen
    import olatqti
    del olatqti.bloecke
    at_alt = neu().run()
    if not hasattr(sys.modules["olatqti"], "bloecke") or any("veralteten" in e.value for e in at_alt.error):
        fehler.append("veralteter Konverter wird nicht neu geladen")

    # Preisrechner nach einer Umwandlung (Zahlen aus dem Gasgesetze-Lauf vom 22.09.2026)
    at3 = neu()
    at3.session_state["yaml"] = beispiel
    at3.session_state["pdf_name"] = "gas"
    at3.session_state["verbrauch"] = {"eingabe": 3807, "ausgabe": 3033, "modell": "gpt-5.6-luna"}
    at3.run()
    werte = {m.label: m.value for m in at3.metric}
    if werte.get("Kosten dieser Umwandlung") != "$0.0044" or werte.get("100 solche Umwandlungen") != "$0.44":
        fehler.append(f"Preisrechner: {werte}")
    if not any("$0.20 pro Million Eingabe-Tokens" in c.value for c in at3.caption):
        fehler.append("Preisangabe zum Modell fehlt")
    if at2.metric:
        fehler.append("Preisrechner erscheint auch ohne OpenAI-Umwandlung (YAML-Weg)")

    # Bewertung wählbar (23.09.2026): pro Antwort mit/ohne Abzug oder alles richtig — geprüft am gebauten Zip
    def mc_xml(wahl: str, mit_abzug: bool) -> str:
        at4 = neu()
        at4.session_state["yaml"] = beispiel
        at4.session_state["pdf_name"] = "test"
        at4.run()
        at4.radio(key="bewertung").set_value(wahl)
        at4.checkbox(key="abzug").set_value(mit_abzug)
        at4.run()
        next(b for b in at4.button if b.label == "Zip für OLAT bauen").click()
        at4.run()
        if "zip" not in at4.session_state:
            return ""
        with zipfile.ZipFile(io.BytesIO(at4.session_state["zip"])) as z:
            return next(d for n in z.namelist() if n.endswith(".xml")
                        and 'title="A2 Leichtmetalle"' in (d := z.read(n).decode("utf-8")))
    pro, ohne, alles = (mc_xml("Punkte pro richtige Antwort", True), mc_xml("Punkte pro richtige Antwort", False),
                        mc_xml("Punkte nur, wenn alles richtig ist", True))
    if 'mappedValue="1.0"' not in pro or 'mappedValue="-0.5"' not in pro:
        fehler.append("pro Antwort mit Abzug: Mapping fehlt")
    if 'mappedValue="1.0"' not in ohne or 'mappedValue="0.0"' not in ohne or "-0.5" in ohne:
        fehler.append("pro Antwort ohne Abzug: falsche Antworten ziehen trotzdem ab")
    if not alles or "mapping" in alles:
        fehler.append("alles richtig: trotzdem Teilpunkte")
    kopf = umwandeln.mit_bewertung("---\nbewertung: alles\nabzug: 1\ntitel: x\nfragen:\n  - abzug: 2\n", True, False)
    if kopf != "---\nbewertung: antwort\nabzug: 0\ntitel: x\nfragen:\n  - abzug: 2\n":
        fehler.append(f"mit_bewertung: {kopf!r}")

    for x in fehler:
        print("FEHLER", x)
    print(f"App-Test: {len(fehler)} Fehler")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
