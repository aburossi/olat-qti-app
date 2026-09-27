"""Formelprüfung (app/formelcheck.py): reparieren, erkennen, nachbessern (mit Attrappe statt OpenAI), markieren.

    app/.venv/Scripts/python tests/test_formeln.py
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import yaml

WURZEL = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(WURZEL / "app"), str(WURZEL)]
import formelcheck as fc  # noqa: E402

BS = "\\"


class Attrappe:
    """Antwortet wie client.chat.completions.create mit festen Korrekturen."""
    def __init__(self, korrekturen):
        self.korrekturen, self.auftrag = korrekturen, None
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kw):
        self.auftrag = json.loads(kw["messages"][1]["content"])
        inhalt = json.dumps({"korrekturen": self.korrekturen(self.auftrag)})
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=inhalt))],
                               usage=SimpleNamespace(prompt_tokens=100, completion_tokens=20))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    fehler = []

    # Stufe 1: sichere Reparaturen
    for ein, soll in ((f"$V_2 = {{{{#6}}}}{BS},{BS}text{{L}}$", f"$V_2 =$ {{{{#6}}}} ${BS},{BS}text{{L}}$"),
                      ("$p₁ · V₁ = p₂ · V₂$", f"$p_1 {BS}cdot V_1 = p_2 {BS}cdot V_2$"),
                      ("$10⁵ Pa$ und $x₁₂$", "$10^5 Pa$ und $x_{12}$"),
                      (f"${BS}{BS}frac{{a}}{{b}}$", f"${BS}frac{{a}}{{b}}$"),
                      ("Kein $-Zeichen hier: \\$5", "Kein $-Zeichen hier: \\$5")):
        if (ist := fc.text_reparieren(ein)) != soll:
            fehler.append(f"reparieren({ein!r}) = {ist!r}, erwartet {soll!r}")

    # Erkennen: was nicht sicher zu reparieren ist
    for text, stichwort in ((f"${BS}frac{{p}} = 1$", "zweites Argument"), (f"${BS}frca{{a}}{{b}}$", "unbekannter Befehl"),
                            ("$a = {b$", "Klammern"), ("$a$ und $b", "unpaariges"), ("p₁ = 2 bar", "nicht als LaTeX"),
                            (f"es gilt {BS}cdot hier", "ausserhalb"), (f"${BS}left( a$", "left")):
        if not any(stichwort in b for b in fc.befunde(text)):
            fehler.append(f"nicht erkannt: {text!r} ({fc.befunde(text)})")
    for text in (f"$R = 8{{,}}314{BS},{BS}frac{{{BS}text{{J}}}}{{{BS}text{{mol}} {BS}cdot {BS}text{{K}}}}$",
                 f"${BS}sqrt[3]{{x}}$ und ${BS}frac12$", "Preis \\$5, Stern \\*", "$p_2$ = {{#3±0.05}} bar",
                 f"${BS}left( a {BS}right)$", "Ein Satz ohne Formel.", "[[*Thermoplaste]] und $x$"):
        if (b := fc.befunde(text)):
            fehler.append(f"Fehlalarm: {text!r} → {b}")
    # keine Fehlalarme in den Beispielsätzen (dort stehen die in OLAT geprüften Formeln)
    for p in sorted((WURZEL / "beispiele").glob("*.yaml")):
        satz = yaml.safe_load(p.read_text(encoding="utf-8"))
        if (rest := fc.pruefen(satz)):
            fehler.append(f"Fehlalarm in {p.name}: {[(f['ort'], f['befunde']) for f in rest]}")

    # Felder: alle Stellen eines Satzes, auch Einleitung und Matrix-Zeilen (Lösung zieht mit)
    satz = {"titel": "x", "sektionen": [{"titel": "A", "text": "$a = {b$", "fragen": [
        {"typ": "match", "titel": "M", "zeilen": ["$x₁$", "y"], "spalten": ["s"], "loesung": [["$x₁$", "s"]]},
        {"typ": "sc", "titel": "S", "frage": "$\\frac{p} = 1$", "antworten": [{"text": "$p₁$", "richtig": True}, "b"]},
        {"typ": "numerical", "titel": "N", "text": "$n = {{#2}}$ mol"}]}]}
    n = fc.reparieren(satz)
    m = satz["sektionen"][0]["fragen"][0]
    if n != 3 or m["zeilen"][0] != "$x_1$" or m["loesung"] != [["$x_1$", "s"]] \
            or satz["sektionen"][0]["fragen"][2]["text"] != "$n =$ {{#2}} mol":
        fehler.append(f"reparieren(satz): {n} / {m} / {satz['sektionen'][0]['fragen'][2]}")
    rest = fc.pruefen(satz)
    if sorted(f["ort"] for f in rest) != ["A — Einleitung", "S — frage"]:
        fehler.append(f"pruefen(satz): {[f['ort'] for f in rest]}")

    # Stufe 2: gute Korrektur angenommen, umformulierte und lückenverändernde abgelehnt
    def korrekturen(auftrag):
        out = []
        for a in auftrag:
            if "Einleitung" in json.dumps(a) or a["text"].startswith("$a"):
                out.append({"id": a["id"], "text": "Ganz anderer Text $a = {b}$"})   # Wortlaut geändert
            else:
                out.append({"id": a["id"], "text": f"${BS}{BS}frac{{p}}{{2}} = 1$"})   # gut (Backslash doppelt)
        return out
    client = Attrappe(korrekturen)
    angenommen, verbrauch = fc.nachbessern(client, "gpt-5.6-luna", rest)
    frage_s = satz["sektionen"][0]["fragen"][1]["frage"]
    if angenommen != 1 or frage_s != f"${BS}frac{{p}}{{2}} = 1$" or verbrauch != {"eingabe": 100, "ausgabe": 20}:
        fehler.append(f"nachbessern: {angenommen}, {frage_s!r}, {verbrauch}")
    if not client.auftrag or not all(a["fehler"] for a in client.auftrag):
        fehler.append("Auftrag an das Modell ohne Fehlerliste")
    if fc.annehmbar("$x = {{#2}}$", "$x =$ {{#3}}"):
        fehler.append("Korrektur mit veränderter Lücke angenommen")

    # Stufe 3: Rest markieren
    rest = fc.pruefen(satz)
    if fc.markieren(rest) != 1 or "Formel prüfen" not in satz["sektionen"][0].get("unsicher", ""):
        fehler.append(f"markieren: {satz['sektionen'][0].get('unsicher')}")

    for f in fehler:
        print("FEHLER", f)
    print(f"Formel-Test: {len(fehler)} Fehler")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
