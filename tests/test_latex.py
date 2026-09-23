"""LaTeX ($…$), fett (**…**) und kursiv (*…*) im Text — Randfälle, ohne OLAT.

Das eigentliche Format prüft test_referenz.py gegen einen OLAT-Export (referenz/latex/).
Hier: Dollarzeichen ohne Formel, Escape, Umlaute/Unicode im title, Antworten mit Formeln.

    app/.venv/Scripts/python tests/test_latex.py
"""
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import olatqti as o  # noqa: E402

NS = "{http://www.imsglobal.org/xsd/imsqti_v2p1}"


def roh(el):
    return ET.tostring(el, encoding="unicode").replace(f' xmlns="{NS[1:-1]}"', "")


FAELLE = [
    # (Text, erwartetes XML)
    ("Ohne Formel.", "<p>Ohne Formel.</p>"),
    ("Preis 5 \\$ pro Stück", "<p>Preis 5 $ pro Stück</p>"),
    ("Das kostet $5 und $6", '<p>Das kostet <span class="math" title="5%20und%20">5 und</span>6</p>'),
    ("Es gilt $p \\cdot V = konst.$ bei gleicher Temperatur.",
     '<p>Es gilt <span class="math" title="p%20%5Ccdot%20V%20%3D%20konst.">p \\cdot V = konst.</span> bei gleicher Temperatur.</p>'),
    ("Auch in Antworten: **fett** und *kursiv*.", "<p>Auch in Antworten: <strong>fett</strong> und <em>kursiv</em>.</p>"),
    ("Kein kursiv: 3*4*5, a * b, \\*Stern\\*","<p>Kein kursiv: 3*4*5, a * b, *Stern*</p>"),
    ("Mit **fett** und $\\Delta T$.",
     '<p>Mit <strong>fett</strong> und <span class="math" title="%5CDelta%20T">\\Delta T</span>.</p>'),
]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    fehler = []
    # title wie JavaScripts escape(): + / . - _ * @ bleiben, Rest %XX bzw. %uXXXX
    for ein, soll in [("\\frac{3}{4+12}", "%5Cfrac%7B3%7D%7B4+12%7D"), ("Δ °C", "%u0394%20%B0C"), ("a/b-c_d*e@f.g", "a/b-c_d*e@f.g")]:
        if o.js_escape(ein) != soll:
            fehler.append(f"js_escape({ein!r}) = {o.js_escape(ein)!r}, erwartet {soll!r}")
    for text, soll in FAELLE:
        ist = roh(o.inline(o.E("p"), text))
        # «$5 und $» ist absichtlich eine Formel (Paar gefunden) — dokumentiert, nicht schön; \$ schützt
        soll_norm = soll.replace('title="5%20und%20">5 und</span>', 'title="5%20und">5 und</span>')
        if ist != soll_norm:
            fehler.append(f"{text!r}\n    ist:  {ist}\n    soll: {soll_norm}")
    # Formeln in Antworten eines ganzen Items
    import tempfile
    import zipfile
    with tempfile.TemporaryDirectory() as t:
        y, z = Path(t) / "f.yaml", Path(t) / "t.zip"
        y.write_text('titel: x\nfragen:\n  - typ: sc\n    titel: G\n    frage: "Welche Gleichung?"\n    antworten:\n'
                     '      - {text: "$p \\\\cdot V = \\\\text{konst.}$", richtig: true}\n'
                     '      - {text: "$\\\\frac{V}{T} = \\\\text{konst.}$", richtig: false}\n', encoding="utf-8")
        o.baue_paket(y, z)
        with zipfile.ZipFile(z) as zz:
            sc = next(zz.read(n).decode() for n in zz.namelist() if n.startswith("sc"))
    if sc.count('class="math"') != 2 or "\\text{konst.}" not in sc:
        fehler.append("Formeln in Antworten fehlen")

    # Formel im Lückentext und im Hottext (zwischen den Lücken, nicht darin)
    with tempfile.TemporaryDirectory() as t:
        y, z = Path(t) / "f.yaml", Path(t) / "t.zip"
        y.write_text("titel: x\nfragen:\n  - typ: numerisch\n    titel: N\n"
                     "    text: '$p_2$ = {{#3±0.05}} bar, weil $p_1 \\cdot V_1 = p_2 \\cdot V_2$.'\n"
                     "  - typ: hottext\n    titel: H\n    text: 'Bei $V$ konstant gilt [[*Amontons]], nicht [[Boyle]].'\n",
                     encoding="utf-8")
        o.baue_paket(y, z)
        with zipfile.ZipFile(z) as zz:
            num = next(zz.read(n).decode() for n in zz.namelist() if n.startswith("numerical"))
            ht = next(zz.read(n).decode() for n in zz.namelist() if n.startswith("hottext"))
    if num.count('class="math"') != 2 or "<textEntryInteraction" not in num or ht.count('class="math"') != 1:
        fehler.append("Formeln im Lücken-/Hottext falsch")

    # Dezimalkomma in Zahl-Lücken (Schweizer Unterlagen, gpt-5.6-luna am 22.09.2026)
    with tempfile.TemporaryDirectory() as t:
        y, z = Path(t) / "f.yaml", Path(t) / "t.zip"
        y.write_text("titel: x\nfragen:\n  - typ: numerisch\n    titel: N\n    text: 'R = {{#8,314±0,001}}'\n",
                     encoding="utf-8")
        o.baue_paket(y, z)
        with zipfile.ZipFile(z) as zz:
            num = next(zz.read(n).decode() for n in zz.namelist() if n.startswith("numerical"))
    if "<value>8.314</value>" not in num or 'tolerance="0.001 0.001"' not in num:
        fehler.append("Dezimalkomma in Zahl-Lücke falsch umgesetzt")

    # Reparatur doppelter Backslashes aus dem Modell (app/umwandeln.py)
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
    import umwandeln
    bs = "\\"
    rep = umwandeln._latex_reparieren(f"${bs*2}frac{{p}}{{T}}$ und $a {bs*2} b$ sowie {bs*2}cdot")
    if rep != f"${bs}frac{{p}}{{T}}$ und $a {bs*2} b$ sowie {bs*2}cdot":
        fehler.append(f"Backslash-Reparatur falsch: {rep}")
    for f in fehler:
        print("FEHLER", f)
    print(f"LaTeX-Test: {len(fehler)} Fehler")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
