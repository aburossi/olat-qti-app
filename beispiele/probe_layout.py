"""Schickt ausgabe/Layout_mit_Loesungen.pdf n-mal an das Modell der App und prüft Einleitungen und Fragetypen.

    app/.venv/Scripts/python beispiele/pdf_layout.py
    app/.venv/Scripts/python beispiele/probe_layout.py [n=3]
    app/.venv/Scripts/python beispiele/probe_layout.py 3 gase   # Beispiel-PDF der App: Video je Teil/Frage

Braucht den OpenAI-Schlüssel aus app/.streamlit/secrets.toml. Kostet je Lauf rund einen halben Rappen.
Massstab: ERWARTET, FALL, DIAGRAMM, LESETEXT in beispiele/pdf_layout.py.
"""
import re
import sys
import tomllib
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(WURZEL / "app"), str(WURZEL), str(WURZEL / "beispiele")]
import umwandeln  # noqa: E402
from openai import OpenAI  # noqa: E402
from pdf_layout import DIAGRAMM, ERWARTET, FALL, LESETEXT, VIDEO  # noqa: E402

MODELL = "gpt-5.6-luna"


def nummer(f: dict) -> str:
    m = re.match(r"\s*([A-C]\d)", f.get("titel", ""))
    return m[1] if m else f.get("titel", "?")


def pruefe(satz: dict) -> list[str]:
    fehler = []
    seks = {s["titel"][:6]: s for s in satz["sektionen"]}
    a, b, c = (next((s for t, s in seks.items() if t.startswith(f"Teil {x}")), {}) for x in "ABC")
    fragen = {nummer(f): f for s in satz["sektionen"] for f in s["fragen"]}
    for n, soll in ERWARTET.items():
        ist = fragen.get(n, {}).get("typ")
        if ist not in (soll if isinstance(soll, set) else {soll}):
            fehler.append(f"{n}: {ist} statt {soll}")
    # Einleitungen
    if FALL not in (a.get("text") or ""):
        fehler.append("A: Fallbeispiel nicht in der Einleitung")
    if [n for n in ("A1", "A2", "A3", "A4") if FALL in (fragen.get(n, {}).get("frage") or "")]:
        fehler.append("A: Fallbeispiel zusätzlich in Fragen kopiert")
    if DIAGRAMM not in (b.get("text") or ""):
        fehler.append("B: Einleitung fehlt")
    if not b.get("bilder") or VIDEO not in (b.get("medien") or []):
        fehler.append(f"B: Bild/Video nicht bei der Sektion (bilder={b.get('bilder')}, medien={b.get('medien')})")
    if [n for n in ("B1", "B2", "B3", "B4") if fragen.get(n, {}).get("bilder")]:
        fehler.append("B: Diagramm zusätzlich bei Fragen")
    if LESETEXT in (c.get("text") or ""):
        fehler.append("C: Lesetext (nur für C1, C2) als Einleitung")
    for n in ("C1", "C2"):
        f = fragen.get(n, {})
        if LESETEXT not in (f.get("frage") or "") + (f.get("text") or ""):
            fehler.append(f"{n}: Lesetext fehlt in der Frage")
    if LESETEXT in (fragen.get("C3", {}).get("frage") or ""):
        fehler.append("C3: Lesetext, obwohl nicht dafür")
    # Liste mit Lücken
    a2 = fragen.get("A2", {}).get("text") or ""
    if a2.count("{{") != 3 or len([z for z in a2.splitlines() if "{{" in z]) != 3:
        fehler.append(f"A2: nicht drei Zeilen mit je einer Lücke: {a2!r}")
    if "Reihenfolge" not in (fragen.get("A2", {}).get("unsicher") or ""):
        fehler.append("A2: freie Reihenfolge nicht markiert")
    if (fragen.get("B1", {}).get("text") or "").count("{{") != 3:
        fehler.append(f"B1: nicht drei Lücken: {fragen.get('B1', {}).get('text')!r}")
    return fehler


GASE_PDF = WURZEL / "beispiele" / "Ideale_Gase_Videotest_mit_Loesungen.pdf"


def pruefe_gase(satz: dict) -> list[str]:
    """Beispiel-PDF: Link steht unter A1, der Kopf sagt «Fragen in Teil A beziehen sich darauf»; B1, B3, C3
    verweisen ausdrücklich auf das Video. Soll: Video bei Sektion A, bei B1/B3/C3, sonst nirgends."""
    fehler = []
    seks = {s["titel"][:6]: s for s in satz["sektionen"]}
    a = next((s for t, s in seks.items() if t.startswith("Teil A")), {})
    if VIDEO not in (a.get("medien") or []):
        fehler.append(f"A: Video nicht bei der Sektion ({a.get('medien')})")
    fragen = {nummer(f): f for s in satz["sektionen"] for f in s["fragen"]}
    mit = {n for n, f in fragen.items() if VIDEO in (f.get("medien") or [])}
    if mit != {"B1", "B3", "C3"}:
        fehler.append(f"Video bei Fragen {sorted(mit)} statt ['B1', 'B3', 'C3']")
    for n, f in fragen.items():
        vor = re.split(r"\{\{", (f.get("text") or "").replace(r"\$", ""))[:-1]
        if any(sum(t.count("$") for t in vor[:i + 1]) % 2 for i in range(len(vor))):
            fehler.append(f"{n}: Lücke in Formel (Konverter repariert es): {f['text']!r}")
    return fehler


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    gase = "gase" in sys.argv[2:]
    schluessel = tomllib.loads((WURZEL / "app" / ".streamlit" / "secrets.toml").read_text(encoding="utf-8"))["openai"]["api_key"]
    daten = (GASE_PDF if gase else WURZEL / "ausgabe" / "Layout_mit_Loesungen.pdf").read_bytes()
    funde = umwandeln.bilder_aus_pdf(daten)
    text = umwandeln.pdf_text_mit_bildern(daten, funde)
    gesamt = []
    for lauf in range(1, n + 1):
        roh, verbrauch = umwandeln.frage_openai(OpenAI(api_key=schluessel), MODELL, text)
        satz = umwandeln.zu_fragensatz(roh)
        umwandeln.pruefe_medien(satz, text)
        umwandeln.medien_verteilen(satz)
        umwandeln.pruefe_bilder(satz, {f["name"] for f in funde})
        (WURZEL / "ausgabe" / f"probe_{'gase' if gase else 'layout'}_{lauf}.yaml").write_text(umwandeln.als_yaml(satz), encoding="utf-8")
        fehler = pruefe_gase(satz) if gase else pruefe(satz)
        gesamt.append(len(fehler))
        print(f"Lauf {lauf}: {len(fehler)} Abweichung(en), ${umwandeln.kosten(verbrauch, MODELL):.4f}")
        for x in fehler:
            print("   ", x)
    print(f"Abweichungen je Lauf: {gesamt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
