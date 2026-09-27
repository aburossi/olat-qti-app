"""Textlücken mit `laenge` / `platzhalter`: die Lücke muss so aussehen wie in OpenOLAT 21.0.3
(«Erwartete Länge», «Platzhalter»; referenz/laenge/, Export 27.09.2026). Ohne `laenge` bleibt alles
wie bisher — dafür sorgt zusätzlich test_referenz.py.

    python tests/test_laenge.py
"""
import re
import sys
import tempfile
import zipfile
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
import olatqti  # noqa: E402

TAG = re.compile(r"<textEntryInteraction\b[^>]*/>")


def attribute(tag: str) -> list[tuple[str, str]]:
    """Attribute in Schreibreihenfolge, Kennung neutralisiert."""
    paare = re.findall(r'(\w+)="([^"]*)"', tag)
    return [(k, "R" if k == "responseIdentifier" else v) for k, v in paare]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    fehler = []
    with tempfile.TemporaryDirectory() as tmp:
        ziel = Path(tmp) / "t.zip"
        olatqti.baue_paket(WURZEL / "beispiele" / "laenge.yaml", ziel)
        fehler += [f"Prüfung: {b}" for b in olatqti.pruefe_paket(ziel)]
        with zipfile.ZipFile(ziel) as z:
            items = {re.search(r'title="([^"]+)"', x).group(1): x
                     for x in (z.read(n).decode("utf-8") for n in z.namelist() if n.endswith(".xml"))
                     if "<assessmentItem " in x}

    def luecken(titel):
        return [attribute(t) for t in TAG.findall(items[titel])]

    erwartet = [("class", ""), ("responseIdentifier", "R"), ("expectedLength", "150"),
                ("placeholderText", "Ihre Antwort hier")]
    ref = sorted((WURZEL / "referenz" / "laenge").glob("*.xml")) if (WURZEL / "referenz" / "laenge").is_dir() else []
    if ref:
        ref_luecken = [attribute(t) for t in TAG.findall(ref[0].read_text(encoding="utf-8"))]
        if ref_luecken != [erwartet]:
            fehler.append(f"Referenz sieht anders aus als erwartet: {ref_luecken}")
    else:
        print("  übersprungen: Abgleich mit referenz/laenge/ — Export liegt nicht im Repo")

    if luecken("L1 Tatsache oder Bewertung") != [erwartet]:
        fehler.append(f"gemischt: {luecken('L1 Tatsache oder Bewertung')}")
    if luecken("L2 Kurz erklären") != [erwartet[:3] + [("placeholderText", "")]]:
        fehler.append(f"lueckentext: {luecken('L2 Kurz erklären')}")
    if luecken("L3 Ohne Länge") != [[("class", ""), ("responseIdentifier", "R"), ("placeholderText", "")]]:
        fehler.append(f"ohne laenge verändert: {luecken('L3 Ohne Länge')}")

    for f in fehler:
        print("FEHLER", f)
    print("OK — Textlücken mit Länge wie in OpenOLAT" if not fehler else f"{len(fehler)} Fehler")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
