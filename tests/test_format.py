"""Formatierung: Markdown im Fragensatz -> XHTML in OLAT, und PDF -> Markdown in umwandeln.py.

Vorbild ist Pietros Nachformatierung in OpenOlat (referenz/formatierung/, 23.09.2026, lokal):
<h3> für Zwischentitel, <strong>, <br/> je Zeile bei Texten mit Zeilennummern.

    app/.venv/Scripts/python tests/test_format.py
"""
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

WURZEL = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(WURZEL), str(WURZEL / "app")]
import olatqti as o  # noqa: E402

NS = "{http://www.imsglobal.org/xsd/imsqti_v2p1}"


def html(text: str) -> str:
    return "".join(ET.tostring(el, encoding="unicode") for el in o.bloecke(text)).replace(
        f' xmlns="{NS[1:-1]}"', "").replace("html:", "")


FAELLE = [
    ("Ein Absatz,\nhart umbrochen.", "<p>Ein Absatz, hart umbrochen.</p>"),
    ("Erster.\n\nZweiter.", "<p>Erster.</p><p>Zweiter.</p>"),
    ("### Die Situation\nText *kursiv*.", "<h3>Die Situation</h3><p>Text <em>kursiv</em>.</p>"),
    ("1 **Frage?**\n2 Antwort\n3 weiter", "<p>1 <strong>Frage?</strong><br />2 Antwort<br />3 weiter</p>"),
    ("Musterstrasse 1\\\n8000 Zürich", "<p>Musterstrasse 1<br />8000 Zürich</p>"),
    ("Doppelt\\\\\numbrochen", "<p>Doppelt<br />umbrochen</p>"),
    ("Enthält:\n- einen **Rat**,\n- ein Zitat.", "<p>Enthält:</p><ul><li>einen <strong>Rat</strong>,</li><li>ein Zitat.</li></ul>"),
    ("1. eins\n2. zwei", "<ol><li>eins</li><li>zwei</li></ol>"),
    ("| Stoff | Dichte |\n|---|---|\n| Alu | $2{,}7$ |",
     '<table><tbody><tr><th>Stoff</th><th>Dichte</th></tr><tr><td>Alu</td>'
     '<td><span class="math" title="2%7B%2C%7D7">2{,}7</span></td></tr></tbody></table>'),
    ("| a | b |\n| c | d |", "<table><tbody><tr><td>a</td><td>b</td></tr><tr><td>c</td><td>d</td></tr></tbody></table>"),
    ("Nur 2 Zeilen\n5 beginnt mit Zahl", "<p>Nur 2 Zeilen 5 beginnt mit Zahl</p>"),
]


def pdf_test(fehler: list[str]) -> None:
    """Ein PDF wie die Prüfungssimulation: Zeilennummer links, nach der Zeile geschrieben; fett, kursiv."""
    import pymupdf
    import umwandeln
    doc = pymupdf.open()
    s = doc.new_page()
    s.insert_text((60, 60), "Die Situation", fontname="hebo", fontsize=11)
    s.insert_text((60, 80), "Ein Kollege sagt: ", fontname="helv", fontsize=10)
    s.insert_text((150, 80), "«Soll ich schweigen?»", fontname="heit", fontsize=10)
    for i, (t, schrift) in enumerate([("Was ist das Wichtigste?", "hebo"), ("Das Wichtigste ist die Ausbildung.", "helv")], 1):
        y = 100 + 16 * i
        s.insert_text((89, y), t, fontname=schrift, fontsize=11)
        s.insert_text((76, y), str(i), fontname="helv", fontsize=8)  # Nummer nach der Zeile, wie im Original
    s.draw_circle((66, 160 - 3), 1.5, fill=(0, 0, 0), color=None)
    s.insert_text((74, 160), "einen klaren Rat", fontname="helv", fontsize=10)
    text = umwandeln.pdf_text(doc.tobytes())[0]
    for soll in ("**Die Situation**", "*«Soll ich schweigen?»*", "1 **Was ist das Wichtigste?**",
                 "2 Das Wichtigste ist die Ausbildung.", "- einen klaren Rat"):
        if soll not in text:
            fehler.append(f"PDF-Text: «{soll}» fehlt in\n{text}")


def referenz_test(fehler: list[str]) -> None:
    """Gleiche Bausteine wie Pietros OLAT-Formatierung (h3, strong, br), sofern der Export lokal liegt."""
    ordner = WURZEL / "referenz" / "formatierung"
    if not ordner.is_dir():
        print("referenz/formatierung/ fehlt — Referenzvergleich übersprungen")
        return
    ref = next(ordner.glob("matchtruefalse*.xml")).read_text(encoding="utf-8")
    body = re.search(r"<itemBody>(.*?)<matchInteraction", ref, re.S)[1]
    ref_tags = set(re.findall(r"<(h3|strong|br)\b", body))
    neu = html("### Die Situation\nText\n\n1 **Was ist das Wichtigste?**\n2 Das Wichtigste")
    neu_tags = set(re.findall(r"<(h3|strong|br)\b", neu))
    if ref_tags != neu_tags:
        fehler.append(f"Referenz nutzt {sorted(ref_tags)}, wir {sorted(neu_tags)}")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    fehler = []
    for text, soll in FAELLE:
        if (ist := html(text)) != soll:
            fehler.append(f"{text!r}\n    ist:  {ist}\n    soll: {soll}")
    # Bilder stehen nach allen Blöcken von `frage`, nicht mitten in einer Liste
    import tempfile
    import zipfile
    with tempfile.TemporaryDirectory() as t:
        y, z = Path(t) / "f.yaml", Path(t) / "t.zip"
        y.write_text("titel: x\nfragen:\n  - typ: freitext\n    titel: F\n    frage: |\n      ### Titel\n"
                     "      1 eins\n      2 zwei\n\n      Aufgabe mit **fett**.\n"
                     "    musterloesung: |\n      - Punkt *eins*\n      - Punkt zwei\n", encoding="utf-8")
        o.baue_paket(y, z)
        fehler += [f"Paket: {b}" for b in o.pruefe_paket(z)]
        with zipfile.ZipFile(z) as zz:
            item = next(zz.read(n).decode() for n in zz.namelist() if n.startswith("essay"))
        for soll in ("<h3>Titel</h3>", "1 eins<br />2 zwei", "<strong>fett</strong>", "<li>Punkt <em>eins</em></li>"):
            if soll not in item:
                fehler.append(f"Item: «{soll}» fehlt")
    pdf_test(fehler)
    referenz_test(fehler)
    for f in fehler:
        print("FEHLER", f)
    print(f"Format-Test: {len(fehler)} Fehler")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
