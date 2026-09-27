"""Punkte je Lückenart, Einfügen sperren, Kprim gemischt (27.09.2026) — Regeln und Fehlermeldungen.
Der Abgleich mit OpenOlat steht in test_referenz.py (gemischt_pro_antwort, essay_nocopypaste).

    python tests/test_gewichte.py
"""
import re
import sys
import tempfile
import zipfile
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
import olatqti  # noqa: E402


def bauen(yml: str) -> dict[str, str]:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "t.yaml").write_text(yml, encoding="utf-8")
        olatqti.baue_paket(Path(tmp) / "t.yaml", Path(tmp) / "t.zip")
        with zipfile.ZipFile(Path(tmp) / "t.zip") as z:
            return {n: z.read(n).decode("utf-8") for n in z.namelist() if n.endswith(".xml")}


def item(dateien: dict[str, str], praefix: str) -> str:
    return next(d for n, d in dateien.items() if n.startswith(praefix))


def fehler_bei(yml: str) -> str:
    try:
        bauen(yml)
    except olatqti.FehlerImFragensatz as e:
        return str(e)
    return ""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    fehler = []
    kopf = "titel: x\nfragen:\n"

    # gemischt: Gewichte je Art, punkte = Summe (auch ohne punkte-Angabe), Zahl-Lücke mit eigenem Gewicht
    x = item(bauen(kopf + "  - typ: gemischt\n    punkte_dropdown: 1\n    punkte_text: 2\n    punkte_zahl: 0.5\n"
                   "    text: 'A {{*ja|nein}} B {{Bern}} C {{#26}}'\n"), "gapmixed")
    if not re.search(r'MAXSCORE".*?<value>3\.5</value>', x) or 'mappedValue="2.0"' not in x \
            or 'mappedValue="1.0"' not in x or '<baseValue baseType="float">0.5</baseValue>' not in x \
            or "FEEDBACKBASIC\"><baseValue" in x:
        fehler.append("gemischt mit Gewichten: Punkte/Mapping falsch")
    # gemischt ohne Gewichte: jetzt Punkte pro Antwort, gleichmässig verteilt
    x = item(bauen(kopf + "  - typ: gemischt\n    punkte: 2\n    text: 'A {{*ja|nein}} B {{Bern}}'\n"), "gapmixed")
    if x.count('mappedValue="1.0"') != 2 or "SCORE_RESPONSE_2" not in x:
        fehler.append("gemischt ohne Gewichte: nicht gleichmässig pro Antwort")
    # bewertung: alles bleibt möglich
    x = item(bauen(kopf + "  - typ: gemischt\n    bewertung: alles\n    text: 'A {{*ja|nein}} B {{Bern}}'\n"), "gapmixed")
    if 'mappedValue="-1.0"' not in x or "SCORE_RESPONSE_1" in x:
        fehler.append("gemischt mit bewertung: alles ist nicht mehr alles oder nichts")
    # lueckentext mit punkte_text
    x = item(bauen(kopf + "  - typ: lueckentext\n    punkte_text: 1.5\n    text: '{{a}} und {{b}}'\n"), "fib")
    if x.count('mappedValue="1.5"') != 2 or not re.search(r'MAXSCORE".*?<value>3\.0</value>', x):
        fehler.append("lueckentext mit punkte_text falsch")

    for yml, stichwort in (
            ("  - typ: gemischt\n    punkte: 5\n    punkte_dropdown: 1\n    punkte_text: 2\n    text: '{{*a|b}} {{c}}'\n",
             "≠ Summe"),
            ("  - typ: gemischt\n    punkte_dropdown: 1\n    text: '{{*a|b}} {{c}}'\n", "punkte_text fehlt"),
            ("  - typ: gemischt\n    bewertung: alles\n    punkte_text: 1\n    text: '{{c}}'\n", "bewertung: alles"),
            ("  - typ: gemischt\n    punkte_text: zwei\n    text: '{{c}}'\n", "Zahlen")):
        if stichwort not in (m := fehler_bei(kopf + yml)):
            fehler.append(f"Fehlermeldung ohne «{stichwort}»: {m!r}")

    # Freitext: Einfügen standardmässig erlaubt, einfuegen: false sperrt
    offen = item(bauen(kopf + "  - {typ: freitext, frage: A}\n"), "essay")
    zu = item(bauen(kopf + "  - {typ: freitext, frage: A, einfuegen: false}\n"), "essay")
    if 'class=""' not in offen or 'class="essay-nocopypaste"' not in zu:
        fehler.append("einfuegen: Klasse falsch")

    # einfuegen für den ganzen Test, einzelne Frage kann es wieder erlauben
    alle = bauen("titel: x\neinfuegen: false\nfragen:\n  - {typ: freitext, titel: A, frage: A}\n"
                 "  - {typ: freitext, titel: B, frage: B, einfuegen: true}\n")
    klassen = sorted(re.search(r'extendedTextInteraction class="([^"]*)"', d)[1] for d in alle.values() if "<extendedTextInteraction" in d)
    if klassen != ["", "essay-nocopypaste"]:
        fehler.append(f"einfuegen geerbt: {klassen}")

    # Kprim: standardmässig gemischt, mischen: false hält die Reihenfolge
    aussagen = "    aussagen: [{text: a, richtig: true}, {text: b, richtig: false}, {text: c, richtig: true}, {text: d, richtig: false}]\n"
    gem = item(bauen(kopf + "  - typ: kprim\n" + aussagen), "kprim")
    fest = item(bauen(kopf + "  - typ: kprim\n    mischen: false\n" + aussagen), "kprim")
    if 'class="match_krpim" responseIdentifier="KPRIM_RESPONSE_1" shuffle="true"' not in gem or 'shuffle="false"' not in fest:
        fehler.append("kprim: Mischen-Standard falsch")

    for f in fehler:
        print("FEHLER", f)
    print(f"Gewichte-Test: {len(fehler)} Fehler")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
