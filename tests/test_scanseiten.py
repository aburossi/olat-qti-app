"""Prüft die Seitenanalyse und die Bildübermittlung in app/umwandeln.py — ohne OpenAI.

Baut ein PDF mit drei Seiten: 1 Text, 2 reiner Scan (nur Bild), 3 kurze Überschrift über
einem grossen Bild. Seite 2 und 3 müssen erkannt, gerendert und als Bild in der Anfrage
landen; Seite 1 nur als Text.

    app/.venv/Scripts/python tests/test_scanseiten.py
"""
import base64
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pymupdf

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "app"))
import umwandeln  # noqa: E402

FRAGE = ("Aufgabe 1: Welches Metall hat die geringste Dichte? A) Stahl B) Aluminium C) Kupfer. "
         "Lösung: B. ") * 3


def baue_pdf() -> bytes:
    quelle = pymupdf.open()
    s = quelle.new_page()
    s.insert_textbox(pymupdf.Rect(50, 50, 550, 800), FRAGE.replace("1", "2"), fontsize=12)
    scan = quelle[0].get_pixmap(dpi=100).tobytes("png")  # «eingescannte» Seite

    doc = pymupdf.open()
    p1 = doc.new_page()
    p1.insert_textbox(pymupdf.Rect(50, 50, 550, 800), FRAGE, fontsize=12)
    p2 = doc.new_page()
    p2.insert_image(p2.rect, stream=scan)
    p3 = doc.new_page()
    p3.insert_text((50, 30), "Teil B – Fallbeispiel. Lesen Sie die Ausgangslage", fontsize=11)
    p3.insert_text((50, 48), "im Bild und beantworten Sie dann die Fragen dazu.", fontsize=11)
    p3.insert_image(pymupdf.Rect(40, 60, 560, 700), stream=scan)
    return doc.tobytes()


class FakeClient:
    """Fängt die Anfrage ab und antwortet mit einem leeren, gültigen Test."""

    def __init__(self):
        self.anfrage = None
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.anfrage = kw
        inhalt = json.dumps({"titel": "t", "sektionen": [], "uebersprungen": []})
        return SimpleNamespace(
            choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content=inhalt, refusal=None))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    fehler = []
    daten = baue_pdf()
    seiten = umwandeln.analysiere_pdf(daten)
    arten = [s["art"] for s in seiten]
    print("Seiten:", [(s["nr"], s["art"], s["zeichen"], s["bild_anteil"]) for s in seiten])
    if arten != ["text", "ohne_text", "bild_mit_wenig_text"]:
        fehler.append(f"Erkennung falsch: {arten}")

    nummern = [s["nr"] for s in seiten if s["art"] != "text"]
    bilder = umwandeln.seiten_als_bild(daten, nummern)
    if [n for n, _ in bilder] != [2, 3] or any(not png.startswith(b"\x89PNG") for _, png in bilder):
        fehler.append("Seitenbilder falsch")

    text, anzahl = umwandeln.pdf_text(daten)
    client = FakeClient()
    umwandeln.frage_openai(client, "modell", text, bilder)
    msgs = client.anfrage["messages"]
    if "SEITEN ALS BILD" not in msgs[0]["content"]:
        fehler.append("Scan-Zusatz fehlt im Systemprompt")
    teile = msgs[1]["content"]
    bildteile = [t for t in teile if t["type"] == "image_url"]
    ansagen = [t["text"] for t in teile if t["type"] == "text"][1:]
    if len(bildteile) != 2 or ansagen != ["--- Seite 2 als Bild ---", "--- Seite 3 als Bild ---"]:
        fehler.append(f"Bildteile falsch: {len(bildteile)} Bilder, Ansagen {ansagen}")
    for t in bildteile:
        url = t["image_url"]["url"]
        if not url.startswith("data:image/png;base64,") or not base64.b64decode(url.split(",", 1)[1]).startswith(b"\x89PNG"):
            fehler.append("Bild-URL kein gültiges PNG")

    ohne = FakeClient()
    umwandeln.frage_openai(ohne, "modell", text, [])
    if not isinstance(ohne.anfrage["messages"][1]["content"], str) or "SEITEN ALS BILD" in ohne.anfrage["messages"][0]["content"]:
        fehler.append("Ohne Bilder muss die Anfrage reiner Text bleiben")

    for x in fehler:
        print("FEHLER", x)
    print(f"{len(fehler)} Fehler")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
