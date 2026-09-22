"""Medien im PDF-Weg, ohne OpenAI: Links hinter Wörtern werden sichtbar gemacht, `medien`
kommt durch zu_fragensatz() in den Fragensatz, veränderte URLs werden markiert, und im Zip
steht der OLAT-Player.

    app/.venv/Scripts/python tests/test_medien.py
"""
import sys
import tempfile
import zipfile
from pathlib import Path

import pymupdf
import yaml

WURZEL = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(WURZEL), str(WURZEL / "app")]
import olatqti  # noqa: E402
import umwandeln  # noqa: E402

YT = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
MP3 = "https://download-media.srf.ch/world/audio/beispiel.mp3"
NANOO = "https://www.nanoo.tv/link/v/yoKbbkMg"


def pdf_mit_links() -> bytes:
    doc = pymupdf.open()
    s = doc.new_page()
    s.insert_text((50, 60), "A1. Schauen Sie das Video und beantworten Sie die Frage. Wer singt das Lied?", fontsize=10)
    s.insert_text((50, 80), f"Audio: {MP3}", fontsize=10)          # ausgeschrieben
    s.insert_text((50, 100), "Zum Video", fontsize=10)              # Link hinter dem Wort
    s.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(48, 90, 110, 104), "uri": YT})
    s.insert_text((50, 120), f"Beitrag: {NANOO}", fontsize=10)
    s.insert_text((50, 140), "Lösung: Rick Astley. " * 5, fontsize=10)
    return doc.tobytes()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    fehler = []
    seiten = umwandeln.analysiere_pdf(pdf_mit_links())
    text = seiten[0]["text"]
    if f"- Zum Video: {YT}" not in text:
        fehler.append(f"verlinktes Wort nicht aufgelöst: {text[-160:]!r}")
    ohne_links = len("".join(text.split("Links auf dieser Seite")[0].split()))
    if seiten[0]["zeichen"] != ohne_links:
        fehler.append("Linkliste zählt in die Texterkennung mit")

    leer = {k: None for k in umwandeln.FRAGE["properties"]}
    roh = {"titel": "Medien", "uebersprungen": [], "sektionen": [{"titel": "Fragen", "fragen": [
        {**leer, "typ": "sc", "titel": "A1 Sänger", "punkte": 1, "frage": "Wer singt das Lied?", "medien": [YT, MP3, NANOO],
         "antworten": [{"text": "Rick Astley", "richtig": True}, {"text": "Sting", "richtig": False}]},
        {**leer, "typ": "essay", "titel": "A2 Erfunden", "punkte": 1, "frage": "Fassen Sie zusammen.",
         "medien": ["https://www.youtube.com/watch?v=erfunden123"]},
    ]}]}
    satz = umwandeln.zu_fragensatz(roh)
    markiert = umwandeln.pruefe_medien(satz, text)
    fragen = [f for _, f in umwandeln.alle_fragen(satz)]
    if fragen[0].get("medien") != [YT, MP3, NANOO]:
        fehler.append(f"medien nicht übernommen: {fragen[0].get('medien')}")
    if markiert != 1 or "steht so nicht im PDF" not in (fragen[1].get("unsicher") or "") or fragen[0].get("unsicher"):
        fehler.append(f"Link-Prüfung falsch: {markiert} markiert, {[f.get('unsicher') for f in fragen]}")

    with tempfile.TemporaryDirectory() as tmp:
        y, z = Path(tmp) / "f.yaml", Path(tmp) / "t.zip"
        y.write_text(yaml.safe_dump(satz, allow_unicode=True, sort_keys=False), encoding="utf-8")
        olatqti.baue_paket(y, z)
        befunde = olatqti.pruefe_paket(z)
        with zipfile.ZipFile(z) as zz:
            sc = next(zz.read(n).decode() for n in zz.namelist() if n.startswith("sc"))
    if befunde or sc.count('class="olatFlashMovieViewer"') != 3 or any(u not in sc for u in (YT, MP3, NANOO)):
        fehler.append(f"Player fehlt im Zip: {befunde}")

    for x in fehler:
        print("FEHLER", x)
    print(f"Medien-Test: {len(fehler)} Fehler")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
