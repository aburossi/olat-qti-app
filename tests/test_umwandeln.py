"""Prüft app/umwandeln.py ohne OpenAI: eine nachgebaute Modellantwort mit allen Typen
muss durch zu_fragensatz() und den Konverter fehlerfrei zu einem Paket werden.

    app/.venv/Scripts/python tests/test_umwandeln.py
"""
import sys
import tempfile
import zipfile
from pathlib import Path

import yaml

WURZEL = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(WURZEL), str(WURZEL / "app")]
import olatqti  # noqa: E402
import umwandeln  # noqa: E402

LEER = {k: None for k in umwandeln.FRAGE["properties"]}


def f(**kw):
    return {**LEER, "punkte": 1, "quelle": "S. 1", **kw}


ANTWORT = {
    "titel": "Probe Werkstoffe",
    "uebersprungen": ["Aufgabe 9: Bild beschriften — braucht ein Bild"],
    "_alle": [
        f(typ="sc", titel="1 Dichte", frage="Welches Metall ist am leichtesten?",
          antworten=[{"text": "Aluminium", "richtig": True}, {"text": "Stahl", "richtig": False}]),
        f(typ="mc", titel="2 Leichtmetalle", frage="Welche sind Leichtmetalle?",
          antworten=[{"text": "Al", "richtig": True}, {"text": "Mg", "richtig": True},
                     {"text": "Fe", "richtig": False}, {"text": "Cu", "richtig": False}]),
        f(typ="kprim", titel="3 Aussagen", frage="Richtig oder falsch?", punkte=2,
          aussagen=[{"text": t, "richtig": r} for t, r in [("a", True), ("b", False), ("c", True), ("d", False)]]),
        f(typ="matchtruefalse", titel="4 RF", frage="Richtig?",
          aussagen=[{"text": "x", "richtig": True}, {"text": "y", "richtig": False}]),
        f(typ="match", titel="5 Matrix", frage="Zuordnen", zeilen=["Stahl", "Alu"], spalten=["Fe", "NE"],
          zuordnung=[{"zeile": "Stahl", "spalte": "Fe"}, {"zeile": "Alu", "spalte": "NE"}]),
        f(typ="matchdraganddrop", titel="6 DnD", frage="Sortieren", zeilen=["Cu"], spalten=["NE", "Fe"],
          zuordnung=[{"zeile": "Cu", "spalte": "NE"}]),
        f(typ="fib", titel="7 Lücke", text="Die Dichte von Alu ist {{gering|klein}}."),
        f(typ="numerical", titel="8 Zahl", text="Alu schmilzt bei {{#660±5}} °C."),
        f(typ="inlinechoice", titel="9 Dropdown", text="Stahl ist {{*magnetisch|unmagnetisch}}."),
        f(typ="gapmixed", titel="10 Gemischt", text="{{Kupfer}} hat {{#8.9±0.1}} g/cm³ und ist {{*NE|Fe}}."),
        f(typ="hottext", titel="11 Hottext", frage="Markieren Sie Leichtmetalle.",
          text="[[*Aluminium]], [[Blei]] und [[*Titan]]."),
        f(typ="order", titel="12 Reihenfolge", frage="Ordnen", elemente=["Erz", "Roheisen", "Stahl"]),
        f(typ="essay", titel="13 Freitext", frage="Erklären Sie Legieren.", punkte=4, antwortzeilen=8,
          hinweis="Denken Sie an **Festigkeit**.", musterloesung="Legieren erhöht die **Festigkeit**.",
          unsicher="Punktzahl im PDF unleserlich"),
        f(typ="upload", titel="14 Upload", frage="Laden Sie die Skizze hoch."),
    ],
}


ANTWORT["sektionen"] = [
    {"titel": "Teil A – Geschlossene Fragen", "fragen": ANTWORT["_alle"][:6]},
    {"titel": "Teil B – Lücken und offene Fragen", "fragen": ANTWORT.pop("_alle")[6:]},
    {"titel": "Leer", "fragen": []},
]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    satz = umwandeln.zu_fragensatz(ANTWORT)
    text = yaml.safe_dump(satz, allow_unicode=True, sort_keys=False)
    with tempfile.TemporaryDirectory() as tmp:
        quelle, ziel = Path(tmp) / "f.yaml", Path(tmp) / "t.zip"
        quelle.write_text(text, encoding="utf-8")
        info = olatqti.baue_paket(quelle, ziel)
        befunde = olatqti.pruefe_paket(ziel)
        with zipfile.ZipFile(ziel) as z:
            durchgesickert = [n for n in z.namelist() if b"S. 1" in z.read(n) or b"unleserlich" in z.read(n)]
    fehler = list(befunde)
    if info["fragen"] != 14:
        fehler.append(f"{info['fragen']} statt 14 Fragen")
    if durchgesickert:
        fehler.append(f"Notizfelder im Paket: {durchgesickert}")
    sek = [x["titel"] for x in satz["sektionen"]]
    if sek != ["Teil A – Geschlossene Fragen", "Teil B – Lücken und offene Fragen"]:
        fehler.append(f"Sektionen falsch: {sek}")
    with tempfile.TemporaryDirectory() as tmp:
        quelle, ziel = Path(tmp) / "f.yaml", Path(tmp) / "t.zip"
        quelle.write_text(text, encoding="utf-8")
        olatqti.baue_paket(quelle, ziel)
        with zipfile.ZipFile(ziel) as z:
            test = next(z.read(n).decode() for n in z.namelist() if n.startswith("test"))
    if test.count("<assessmentSection") != 2 or "Teil B – Lücken und offene Fragen" not in test:
        fehler.append("Sektionen fehlen im Test-XML")
    for _, q in umwandeln.alle_fragen(satz):
        if not umwandeln.loesung_kurz(q):
            fehler.append(f"keine Lösungszeile für {q['titel']}")
    for x in fehler:
        print("FEHLER", x)
    print(f"{info['fragen']} Fragen, {info['punkte']:g} Punkte, {len(fehler)} Fehler")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
