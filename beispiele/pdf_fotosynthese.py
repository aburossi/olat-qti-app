"""Erzeugt ein 3-seitiges Test-PDF «Lernkontrolle Fotosynthese – mit Lösungen» mit vier Bildern.

Zum Durchprobieren der Streamlit-App (Bilder, Sektionen, verschiedene Fragetypen). Enthält absichtlich
ein Logo auf jeder Seite und ein kleines Deko-Symbol — beide dürfen NICHT im Test landen.

    app/.venv/Scripts/python beispiele/pdf_fotosynthese.py
"""
import math
from pathlib import Path

import pymupdf

ZIEL = Path(__file__).resolve().parent.parent / "ausgabe" / "Fotosynthese_Lernkontrolle_mit_Loesungen.pdf"
GRUEN, DUNKELGRUEN, BLAU, ROT, GRAU = (0.25, 0.6, 0.25), (0.1, 0.4, 0.15), (0.2, 0.4, 0.85), (0.8, 0.15, 0.1), (0.35, 0.35, 0.35)


def zeichne(b, h, malen, fmt="png"):
    doc = pymupdf.open()
    s = doc.new_page(width=b, height=h)
    s.draw_rect(s.rect, color=None, fill=(1, 1, 1))
    malen(s)
    return s.get_pixmap(dpi=144).tobytes(fmt)


def pfeil(s, a, b, farbe, breite=3):
    s.draw_line(a, b, color=farbe, width=breite)
    w = math.atan2(b[1] - a[1], b[0] - a[0])
    spitze = [b, (b[0] - 12 * math.cos(w - 0.4), b[1] - 12 * math.sin(w - 0.4)),
              (b[0] - 12 * math.cos(w + 0.4), b[1] - 12 * math.sin(w + 0.4))]
    s.draw_polyline(spitze + [b], color=farbe, fill=farbe, closePath=True)


def schema(s):
    s.draw_circle((60, 55), 30, color=(0.9, 0.6, 0), fill=(1, 0.85, 0.2))           # Sonne
    s.draw_oval(pymupdf.Rect(170, 90, 330, 190), color=DUNKELGRUEN, fill=GRUEN, width=2)  # Blatt
    s.draw_line((250, 190), (250, 270), color=DUNKELGRUEN, width=4)                   # Stängel
    pfeil(s, (90, 75), (185, 110), (0.9, 0.6, 0))                                      # D Licht
    pfeil(s, (40, 160), (165, 145), GRAU)                                              # A CO2 hinein
    pfeil(s, (250, 280), (250, 200), BLAU)                                             # B Wasser hinauf
    pfeil(s, (335, 135), (440, 110), ROT)                                              # C O2 hinaus
    for text, pos in [("D", (125, 80)), ("A", (90, 145)), ("B", (262, 250)), ("C", (385, 105))]:
        s.insert_text(pos, text, fontsize=18, fontname="hebo")
    s.insert_text((210, 145), "Blatt", fontsize=13, color=(1, 1, 1), fontname="hebo")


def wasserpest(s):
    s.draw_rect(s.rect, color=None, fill=(0.93, 0.93, 0.9))
    s.draw_rect(pymupdf.Rect(130, 60, 330, 270), color=GRAU, fill=(0.75, 0.88, 0.95), width=2)   # Glas
    for x in (180, 215, 250, 285):
        s.draw_polyline([(x, 265), (x - 8, 200), (x + 6, 140), (x - 4, 95)], color=DUNKELGRUEN, width=5)
    for x, y, r in [(176, 80, 4), (212, 72, 3), (247, 84, 5), (284, 70, 3), (220, 110, 3), (258, 120, 4)]:
        s.draw_circle((x, y), r + 3, color=(0.15, 0.35, 0.6), fill=(1, 1, 1), width=1.5)                                    # Bläschen
    s.draw_rect(pymupdf.Rect(360, 20, 430, 50), color=GRAU, fill=(0.95, 0.9, 0.5))             # Lampe
    s.insert_text((352, 70), "Lampe", fontsize=12)
    s.insert_text((150, 295), "Wasserpest im Wasserglas", fontsize=12)


def chloroplast(s):
    s.draw_oval(pymupdf.Rect(40, 40, 420, 230), color=DUNKELGRUEN, fill=(0.75, 0.9, 0.7), width=4)
    for x in (110, 190, 270, 340):
        for k in range(4):
            y = 105 + k * 16
            s.draw_oval(pymupdf.Rect(x, y, x + 45, y + 12), color=DUNKELGRUEN, fill=GRUEN, width=1)
    for nr, von, zu in [("1", (212, 120), (230, 20)), ("2", (160, 190), (150, 265)), ("3", (395, 90), (460, 45))]:
        s.draw_line(von, zu, color=(0, 0, 0), width=1.2)
        s.insert_text((zu[0] + 4, zu[1] + 4), nr, fontsize=18, fontname="hebo")


def diagramm(s):
    s.draw_line((60, 240), (460, 240), width=1.5)
    s.draw_line((60, 240), (60, 30), width=1.5)
    for i, klx in enumerate((0, 10, 20, 30, 40)):
        x = 60 + i * 95
        s.draw_line((x, 240), (x, 246), width=1)
        s.insert_text((x - 6, 262), str(klx), fontsize=11)
    s.insert_text((300, 285), "Lichtintensität in klx", fontsize=12)
    s.insert_text((12, 22), "Fotosyntheserate", fontsize=12)
    punkte = [(60 + x * 380 / 40, 240 - 190 * (1 - math.exp(-x / 6.5))) for x in [i * 0.5 for i in range(81)]]
    s.draw_polyline(punkte, color=GRUEN, width=3)


def logo(s):
    s.draw_rect(s.rect, color=None, fill=(0.1, 0.2, 0.5))
    s.insert_text((12, 28), "bbw", fontsize=20, color=(1, 1, 1), fontname="hebo")


def sonne_klein(s):
    s.draw_circle((15, 15), 12, color=(0.9, 0.6, 0), fill=(1, 0.85, 0.2))


class Blatt:
    """Schreibt Text von oben nach unten; neue Seite mit Logo, wenn der Platz ausgeht."""

    def __init__(self):
        self.doc = pymupdf.open()
        self.bild_logo = zeichne(110, 40, logo)
        self.neue_seite()

    def neue_seite(self):
        self.s = self.doc.new_page()
        self.s.insert_image(pymupdf.Rect(470, 20, 560, 53), stream=self.bild_logo)
        self.y = 70

    def text(self, t, groesse=10.5, fett=False, abstand=4, einzug=0):
        r = pymupdf.Rect(50 + einzug, self.y, 550, self.y + 400)
        rest = self.s.insert_textbox(r, t, fontsize=groesse, fontname="hebo" if fett else "helv")
        self.y += 400 - rest + abstand

    def bild(self, daten, breite, hoehe):
        self.s.insert_image(pymupdf.Rect(80, self.y, 80 + breite, self.y + hoehe), stream=daten)
        self.y += hoehe + 8

    def auswahl(self, optionen, richtig):
        for i, o in enumerate(optionen):
            self.text(f"{'[x]' if i in richtig else '[  ]'}  {'ABCDE'[i]}) {o}", abstand=1, einzug=15)
        self.y += 3


def main():
    bl = Blatt()
    bl.s.insert_image(pymupdf.Rect(50, 22, 80, 52), stream=zeichne(30, 30, sonne_klein))
    bl.text("Lernkontrolle Fotosynthese - mit Lösungen", 16, True, 2, einzug=40)
    bl.text("Biologie · Bearbeitungszeit 25 Minuten · Total 19 Punkte", 10, abstand=14)

    bl.text("Teil A - Single Choice | 3 Punkte", 13, True, 8)
    bl.text("A1. Das Schema zeigt, was ein Blatt bei der Fotosynthese aufnimmt und abgibt. "
            "Welcher Pfeil steht für die Abgabe von Sauerstoff? (1 P)", fett=True)
    bl.bild(zeichne(470, 290, schema), 300, 185)
    bl.auswahl(["Pfeil A", "Pfeil B", "Pfeil C", "Pfeil D"], {2})
    bl.text("Lösung: C - Sauerstoff entsteht bei der Fotosynthese und wird über die Blätter abgegeben.", abstand=12)

    bl.text("A2. Wo in der Pflanzenzelle findet die Fotosynthese statt? (1 P)", fett=True)
    bl.auswahl(["im Mitochondrium", "im Chloroplasten", "im Zellkern", "in der Vakuole"], {1})
    bl.text("Lösung: Die Fotosynthese läuft in den Chloroplasten ab, die das grüne Chlorophyll enthalten.", abstand=12)

    bl.neue_seite()
    bl.text("A3. Im Versuch steht Wasserpest im Licht. An den Blättern steigen Bläschen auf. "
            "Welches Gas bildet die Bläschen? (1 P)", fett=True)
    bl.bild(zeichne(460, 310, wasserpest, "jpg"), 260, 175)
    bl.auswahl(["Sauerstoff", "Kohlenstoffdioxid", "Stickstoff", "Wasserdampf"], {0})
    bl.text("Lösung: Sauerstoff - er entsteht bei der Fotosynthese und entweicht als Gas.", abstand=14)

    bl.text("Teil B - Mehrfachauswahl, Zuordnung und Lückentext | 6 Punkte", 13, True, 8)
    bl.text("B1. Welche Stoffe nimmt die Pflanze für die Fotosynthese auf? (2 P)", fett=True)
    bl.auswahl(["Wasser", "Kohlenstoffdioxid", "Sauerstoff", "Glucose"], {0, 1})
    bl.text("Lösung: Wasser und Kohlenstoffdioxid sind die Ausgangsstoffe; Sauerstoff und Glucose entstehen.", abstand=12)

    bl.text("B2. Die Abbildung zeigt einen Chloroplasten. Ordnen Sie den Nummern die richtigen "
            "Bestandteile zu: Thylakoide (Granum), Stroma, Hüllmembran. (2 P)", fett=True)
    bl.bild(zeichne(480, 280, chloroplast), 280, 163)
    bl.text("Lösung: 1 = Thylakoide (Granum) · 2 = Stroma · 3 = Hüllmembran", abstand=10)

    bl.neue_seite()
    bl.text("B3. Ergänzen Sie die Lücken. (2 P)", fett=True)
    bl.text("Bei der Fotosynthese entstehen aus Kohlenstoffdioxid und ________ mit Hilfe von Lichtenergie "
            "die Stoffe Glucose und ________.")
    bl.text("Lösung: Wasser; Sauerstoff", abstand=14)

    bl.text("Teil C - Diagramm und offene Fragen | 10 Punkte", 13, True, 8)
    bl.text("Das Diagramm zeigt, wie die Fotosyntheserate einer Pflanze von der Lichtintensität abhängt.")
    bl.bild(zeichne(480, 300, diagramm), 290, 181)
    bl.text("C1. Lesen Sie aus dem Diagramm ab: Ab welcher Lichtintensität steigt die Fotosyntheserate "
            "kaum noch an? Antwort in klx. (2 P)", fett=True)
    bl.text("Lösung: etwa 20 klx (akzeptiert: 18 bis 22 klx).", abstand=10)
    bl.text("C2. Erklären Sie, weshalb die Fotosyntheserate ab dieser Lichtintensität nicht weiter steigt, "
            "und nennen Sie einen Faktor, der sie dann begrenzt. (4 P)", fett=True)
    bl.text("Lösung: Ab etwa 20 klx ist das Licht nicht mehr der begrenzende Faktor. Die Rate wird dann durch "
            "einen anderen Faktor begrenzt, zum Beispiel die Kohlenstoffdioxid-Konzentration oder die Temperatur. "
            "Punkte: Licht nicht mehr begrenzend 2 P; begrenzender Faktor genannt und begründet 2 P.", abstand=10)
    bl.text("C3. Erklären Sie, weshalb die Fotosynthese auch für Menschen und Tiere lebenswichtig ist. "
            "Nennen Sie zwei Gründe. (4 P)", fett=True)
    bl.text("Lösung: Sie liefert den Sauerstoff, den Menschen und Tiere zum Atmen brauchen. Die entstehende "
            "Glucose ist die Grundlage der Nahrungskette - Pflanzen sind Nahrung für Pflanzenfresser und damit "
            "indirekt für alle Tiere. Punkte: je Grund mit Erklärung 2 P.")

    ZIEL.parent.mkdir(exist_ok=True)
    bl.doc.save(ZIEL)
    print(ZIEL, bl.doc.page_count, "Seiten")


if __name__ == "__main__":
    main()
