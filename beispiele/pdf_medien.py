"""Erzeugt «Medientest_Video_Audio_mit_Loesungen.pdf» — dieselben zwei Fragen wie beispiele/medientest.yaml.

Prüft beide Wege, auf denen Links in einem PDF stehen:
- Video: Link HINTER den Wörtern «Video ansehen» (wie in Word mit Strg+K) — steht nicht im Text,
  muss über die Link-Liste der Seite gefunden werden;
- Audio: mp3-URL AUSGESCHRIEBEN im Text (zusätzlich anklickbar).

    app/.venv/Scripts/python beispiele/pdf_medien.py
"""
import sys
from pathlib import Path

import pymupdf

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "beispiele"))
from pdf_fotosynthese import Blatt  # noqa: E402

YOUTUBE = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
MP3 = ("https://download-media.srf.ch/world/audio/Corona_kompakt_radio/2026/09/"
       "Corona_kompakt_radio_AUDI20260921_NR_0023_6ee934efe47c4bf0928cd2f42c6c2e93.mp3")
ZIEL = WURZEL / "ausgabe" / "Medientest_Video_Audio_mit_Loesungen.pdf"


def main():
    bl = Blatt()
    bl.text("Medientest - Video und Audio - mit Lösungen", 16, True, 2)
    bl.text("Bearbeitungszeit 10 Minuten · Total 3 Punkte", 10, abstand=14)

    bl.text("Teil A - Video | 1 Punkt", 13, True, 8)
    bl.text("M1. Schauen Sie das Video an. Wer singt dieses Lied? (1 P)", fett=True)
    y = bl.y
    bl.text("Video ansehen", abstand=6, einzug=15)
    breite = pymupdf.get_text_length("Video ansehen", fontname="helv", fontsize=10.5)
    bl.s.draw_line((65, y + 12), (65 + breite, y + 12), color=(0.1, 0.3, 0.8), width=0.6)   # unterstrichen wie ein Link
    bl.s.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(63, y - 1, 67 + breite, y + 14), "uri": YOUTUBE})
    bl.auswahl(["Rick Astley", "Phil Collins", "Bruce Springsteen", "Sting"], {0})
    bl.text("Lösung: Rick Astley.", abstand=16)

    bl.text("Teil B - Audio | 2 Punkte", 13, True, 8)
    bl.text("M2. Hören Sie den Beitrag. Fassen Sie ihn in drei Sätzen zusammen. (2 P)", fett=True)
    bl.text("Audio:", abstand=1, einzug=15)
    y = bl.y
    bl.s.insert_text((65, y + 8), MP3, fontsize=6.5, color=(0.1, 0.3, 0.8))                 # ausgeschrieben, eine Zeile
    laenge = pymupdf.get_text_length(MP3, fontname="helv", fontsize=6.5)
    bl.s.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(63, y, 67 + laenge, y + 11), "uri": MP3})
    bl.y += 20
    bl.text("Lösung: Bewertung nach Inhalt - drei zutreffende Kernaussagen des Beitrags in eigenen Worten. "
            "Punkte: Kernaussagen 1 P; verständliche, eigene Formulierung 1 P.")

    ZIEL.parent.mkdir(exist_ok=True)
    bl.doc.save(ZIEL)
    print(ZIEL, bl.doc.page_count, "Seite(n);", "mp3-Zeile", round(laenge), "pt breit")


if __name__ == "__main__":
    main()
