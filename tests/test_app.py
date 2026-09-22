"""Klickt die Streamlit-App ohne Browser und ohne echten Login durch (streamlit.testing.AppTest).

Angemeldete Lehrperson wird in session_state gesetzt; keine echten Schlüssel, kein OpenAI-Aufruf.
Prüft: beide Tabs, Modellwahl mit Hinweis, und den Weg «YAML einfügen» bis zum Zip —
mit dem Beispiel aus dem Prompt, eingebettet in eine KI-Antwort mit Codeblock.

    app/.venv/Scripts/python tests/test_app.py
"""
import re
import sys
from pathlib import Path

import yaml
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "app"
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
    radio = at.radio[0] if at.radio else None
    if not radio or list(radio.options) != ["gpt-5.6-luna — günstiger (Standard)", "gpt-4.1 — teurer, sehr gleichmässig"] \
            or radio.value != "gpt-5.6-luna":
        fehler.append(f"Modellwahl: {radio and (list(radio.options), radio.value)}")
    seite = " ".join(m.value for m in at.markdown)
    for stichwort in ("günstiger", "teurer", "Punkteschlüssel", "gpt-4.1-mini"):
        if stichwort not in seite:
            fehler.append(f"Modellhinweis ohne «{stichwort}»")

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

    # Veralteter Konverter im Speicher: die App muss stoppen statt still falsche Pakete zu bauen
    import olatqti
    gemerkt = olatqti.inline
    del olatqti.inline
    at_alt = neu().run()
    olatqti.inline = gemerkt
    if not any("veralteten Fassung des Konverters" in e.value for e in at_alt.error):
        fehler.append("kein Hinweis auf veralteten Konverter")

    # Preisrechner nach einer Umwandlung (Zahlen aus dem Gasgesetze-Lauf vom 22.09.2026)
    at3 = neu()
    at3.session_state["yaml"] = beispiel
    at3.session_state["pdf_name"] = "gas"
    at3.session_state["verbrauch"] = {"eingabe": 3807, "ausgabe": 3033, "modell": "gpt-5.6-luna"}
    at3.run()
    werte = {m.label: m.value for m in at3.metric}
    if werte.get("Kosten dieser Umwandlung") != "$0.0044" or werte.get("100 solche Umwandlungen") != "$0.44":
        fehler.append(f"Preisrechner: {werte}")
    if not any("mit gpt-4.1 wären es $0.0319" in c.value for c in at3.caption):
        fehler.append("Vergleich mit gpt-4.1 fehlt oder falsch")
    if at2.metric:
        fehler.append("Preisrechner erscheint auch ohne OpenAI-Umwandlung (YAML-Weg)")

    for x in fehler:
        print("FEHLER", x)
    print(f"App-Test: {len(fehler)} Fehler")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
