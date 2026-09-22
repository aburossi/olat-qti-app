"""Zeichnet die vier Bilder für saetze/2026-09-22_gasgesetze.yaml (eigene Skizzen, kein fremdes Material).

    app/.venv/Scripts/python beispiele/bilder_gasgesetze.py
"""
import math
from pathlib import Path

import pymupdf

ZIEL = Path(__file__).resolve().parent.parent / "saetze" / "bilder"
BLAU, ROT, GRAU, DUNKEL = (0.15, 0.35, 0.8), (0.8, 0.15, 0.1), (0.55, 0.55, 0.55), (0.15, 0.15, 0.15)


def zeichne(b, h, malen, fmt="png"):
    doc = pymupdf.open()
    s = doc.new_page(width=b, height=h)
    s.draw_rect(s.rect, color=None, fill=(1, 1, 1))
    malen(s)
    return s.get_pixmap(dpi=144).tobytes(fmt)


def achsen(s, x_label, y_label, x0=60, y0=250, x1=460, y1=30):
    s.draw_line((x0, y0), (x1, y0), width=1.5)
    s.draw_line((x0, y0), (x0, y1), width=1.5)
    s.draw_polyline([(x1 - 8, y0 - 4), (x1, y0), (x1 - 8, y0 + 4)], width=1.5)
    s.draw_polyline([(x0 - 4, y1 + 8), (x0, y1), (x0 + 4, y1 + 8)], width=1.5)
    s.insert_text((x1 - 125, y0 + 32), x_label, fontsize=12)
    s.insert_text((x0 + 10, y1 + 8), y_label, fontsize=12)


def p_v(s):
    """Isotherme: p fällt hyperbolisch mit V."""
    achsen(s, "Volumen V", "Druck p")
    punkte = [(60 + v * 38, 250 - min(215, 330 / v)) for v in [1.4 + i * 0.1 for i in range(88)]]
    s.draw_polyline(punkte, color=BLAU, width=3)
    s.insert_text((300, 170), "T = konstant", fontsize=12, color=BLAU)


def v_t(s):
    """Isobare: V steigt linear mit T (in Kelvin), Verlängerung zum Nullpunkt gestrichelt."""
    achsen(s, "Temperatur T in K", "Volumen V")
    s.draw_line((60, 250), (150, 205), color=ROT, width=1.5, dashes="[5] 0")
    s.draw_line((150, 205), (440, 60), color=ROT, width=3)
    for t, x in [(0, 60), (100, 140), (200, 220), (300, 300), (400, 380)]:
        s.draw_line((x, 250), (x, 256), width=1)
        s.insert_text((x - 8, 270), str(t), fontsize=10)
    s.insert_text((250, 110), "p = konstant", fontsize=12, color=ROT)


def zylinder(s):
    """Zylinder mit Gas und beweglichem Kolben, Kraftpfeil."""
    s.draw_polyline([(60, 60), (380, 60)], color=DUNKEL, width=4)
    s.draw_polyline([(60, 200), (380, 200)], color=DUNKEL, width=4)
    s.draw_line((60, 60), (60, 200), color=DUNKEL, width=4)
    s.draw_rect(pymupdf.Rect(62, 62, 258, 198), color=None, fill=(0.85, 0.92, 1))
    for x, y in [(90, 90), (140, 150), (200, 100), (110, 170), (230, 170), (180, 80), (160, 120), (230, 120)]:
        s.draw_circle((x, y), 5, color=BLAU, fill=BLAU)
    s.draw_rect(pymupdf.Rect(258, 62, 278, 198), color=DUNKEL, fill=GRAU)          # Kolben
    s.draw_rect(pymupdf.Rect(278, 120, 420, 140), color=DUNKEL, fill=GRAU)         # Kolbenstange
    s.draw_line((470, 130), (430, 130), color=ROT, width=3)
    s.draw_polyline([(440, 122), (428, 130), (440, 138)], color=ROT, fill=ROT, closePath=True)
    s.insert_text((440, 115), "F", fontsize=16, color=ROT)
    s.insert_text((120, 230), "Gas", fontsize=13)
    s.insert_text((245, 230), "Kolben", fontsize=13)


def ballon(s):
    """Links warmes Zimmer mit grossem Ballon, rechts kalter Balkon mit kleinerem Ballon."""
    s.draw_rect(pymupdf.Rect(0, 0, 250, 300), color=None, fill=(1, 0.93, 0.85))
    s.draw_rect(pymupdf.Rect(250, 0, 500, 300), color=None, fill=(0.85, 0.92, 1))
    s.draw_oval(pymupdf.Rect(65, 50, 185, 190), color=(0.6, 0.05, 0.1), fill=(0.9, 0.2, 0.25), width=2)
    s.draw_oval(pymupdf.Rect(333, 80, 417, 180), color=(0.6, 0.05, 0.1), fill=(0.9, 0.2, 0.25), width=2)
    s.draw_polyline([(125, 190), (120, 230), (130, 260)], color=DUNKEL, width=1)
    s.draw_polyline([(375, 180), (370, 220), (380, 250)], color=DUNKEL, width=1)
    s.insert_text((70, 285), "Zimmer: 22 °C", fontsize=14)
    s.insert_text((320, 285), "Balkon: -5 °C", fontsize=14)


def main():
    ZIEL.mkdir(parents=True, exist_ok=True)
    for name, b, h, malen, fmt in [("gas_pv_diagramm.png", 500, 290, p_v, "png"),
                                   ("gas_vt_diagramm.png", 500, 290, v_t, "png"),
                                   ("gas_zylinder.png", 500, 250, zylinder, "png"),
                                   ("gas_ballon.jpg", 500, 300, ballon, "jpg")]:
        (ZIEL / name).write_bytes(zeichne(b, h, malen, fmt))
        print(ZIEL / name)


if __name__ == "__main__":
    main()
