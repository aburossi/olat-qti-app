"""Bilder im Fragetext: aus einem PDF holen und als <img> ins Paket.

Erzeugt drei Bilder (Diagramm PNG, Proben JPEG, Biegeskizze PNG), legt sie mit einem Logo auf
jeder Seite und einem kleinen Symbol in ein PDF, holt sie mit umwandeln.bilder_aus_pdf() wieder
heraus (Logo und Symbol müssen wegfallen) und baut daraus beispiele/bildtest.yaml → ausgabe/bildtest.zip.

    app/.venv/Scripts/python tests/test_bilder.py
"""
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pymupdf

WURZEL = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(WURZEL), str(WURZEL / "app")]
import olatqti  # noqa: E402
import umwandeln  # noqa: E402

BEISPIELE = WURZEL / "beispiele"
BILDER = BEISPIELE / "bilder"


def zeichne(b: int, h: int, malen, fmt: str = "png") -> bytes:
    doc = pymupdf.open()
    s = doc.new_page(width=b, height=h)
    s.draw_rect(s.rect, color=None, fill=(1, 1, 1))
    malen(s)
    return s.get_pixmap(dpi=144).tobytes(fmt)


def diagramm(s):
    s.draw_line((50, 260), (470, 260), width=1.5)  # Dehnung
    s.draw_line((50, 260), (50, 30), width=1.5)    # Spannung
    s.insert_text((380, 285), "Dehnung", fontsize=11)
    s.insert_text((10, 25), "Spannung", fontsize=11)
    kurven = [("hochfester Stahl", (0.8, 0.1, 0.1), [(50, 260), (80, 70), (120, 55), (150, 60)]),
              ("Baustahl", (0.1, 0.3, 0.8), [(50, 260), (75, 150), (180, 120), (300, 110), (340, 125)]),
              ("Aluminium", (0.1, 0.6, 0.2), [(50, 260), (65, 215), (200, 195), (400, 190), (440, 200)])]
    for name, farbe, punkte in kurven:
        s.draw_polyline(punkte, color=farbe, width=2)
        x, y = punkte[-1]
        s.insert_text((x + 5, y - 5), name, fontsize=10, color=farbe)


def proben(s):
    for i, (name, farbe) in enumerate([("A", (0.75, 0.77, 0.8)), ("B", (0.72, 0.45, 0.2)), ("C", (0.3, 0.3, 0.32))]):
        x = 30 + i * 150
        s.draw_rect(pymupdf.Rect(x, 40, x + 120, 200), color=(0.2, 0.2, 0.2), fill=farbe, width=1)
        s.insert_text((x + 35, 230), f"Probe {name}", fontsize=13)


def biegung(s):
    s.draw_polyline([(40, 200), (220, 200), (330, 80)], color=(0.2, 0.2, 0.2), width=8)
    s.draw_polyline([(220, 200), (345, 95)], color=(0.8, 0.1, 0.1), width=2, dashes="[4] 0")
    s.insert_text((250, 215), "nach Entlastung (rot gestrichelt)", fontsize=10, color=(0.8, 0.1, 0.1))
    s.insert_text((40, 30), "Blech vor und nach dem Entlasten", fontsize=12)


def logo(s):
    s.draw_rect(s.rect, color=None, fill=(0.1, 0.2, 0.5))
    s.insert_text((10, 26), "bbw", fontsize=18, color=(1, 1, 1))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    fehler = []
    bild_diagramm = zeichne(500, 300, diagramm)
    bild_proben = zeichne(480, 250, proben, "jpg")
    bild_biegung = zeichne(420, 240, biegung)
    bild_logo = zeichne(100, 40, logo)
    bild_symbol = zeichne(20, 20, lambda s: s.draw_circle((10, 10), 8, fill=(0, 0, 0)))

    # PDF wie von einer Lehrperson: Logo oben auf jeder Seite, Bilder bei den Fragen
    doc = pymupdf.open()
    for text, bild in [("Teil A – Diagramme\nA1. Welcher Werkstoff hat im Diagramm die grösste Dehnung?", bild_diagramm),
                       ("A2. Welche Probe ist Kupfer?", bild_proben)]:
        s = doc.new_page()
        s.insert_image(pymupdf.Rect(460, 20, 560, 60), stream=bild_logo)
        s.insert_image(pymupdf.Rect(40, 70, 60, 90), stream=bild_symbol)
        s.insert_textbox(pymupdf.Rect(70, 70, 560, 130), text, fontsize=11)
        s.insert_image(pymupdf.Rect(60, 140, 540, 430), stream=bild)
    s.insert_image(pymupdf.Rect(60, 450, 480, 690), stream=bild_biegung)
    funde = umwandeln.bilder_aus_pdf(doc.tobytes())

    namen = [f["name"] for f in funde]
    print("aus dem PDF geholt:", [(f["name"], f["breite"], f["hoehe"]) for f in funde])
    if namen != ["s1_bild1.png", "s2_bild1.jpg", "s2_bild2.png"]:
        fehler.append(f"Extraktion falsch (Logo/Symbol nicht aussortiert oder Reihenfolge): {namen}")
    if funde and olatqti.png_groesse(funde[1]["daten"]) != (funde[1]["breite"], funde[1]["hoehe"]):
        fehler.append("JPEG-Grösse nicht aus dem Dateikopf lesbar")

    # App-Weg: Marken im Text an der richtigen Stelle, unbekannte Bildnamen werden entfernt
    text = umwandeln.pdf_text_mit_bildern(doc.tobytes(), funde)
    marken = [z for z in text.splitlines() if z.startswith("[Bild: ")]
    if marken != ["[Bild: s1_bild1.png]", "[Bild: s2_bild1.jpg]", "[Bild: s2_bild2.png]"]:
        fehler.append(f"Bildmarken falsch: {marken}")
    if text.index("A1. Welcher") > text.index("[Bild: s1_bild1.png]"):
        fehler.append("Bildmarke steht vor ihrer Frage")
    satz = {"titel": "t", "fragen": [
        {"typ": "essay", "titel": "X", "frage": "F", "bilder": [{"datei": "bilder/s1_bild1.png", "alt": "a"},
                                                               {"datei": "bilder/erfunden.png", "alt": "b"}]}]}
    ohne = umwandeln.pruefe_bilder(satz, set(namen))
    f0 = satz["fragen"][0]
    if [b["datei"] for b in f0["bilder"]] != ["bilder/s1_bild1.png"] or "erfunden" not in f0.get("unsicher", "") \
            or ohne != ["s2_bild1.jpg", "s2_bild2.png"]:
        fehler.append(f"pruefe_bilder falsch: {f0}, ohne Frage {ohne}")

    BILDER.mkdir(parents=True, exist_ok=True)
    for f in funde:
        (BILDER / f["name"]).write_bytes(f["daten"])
    (BEISPIELE / "bildtest.yaml").write_text(BILDTEST, encoding="utf-8")
    ziel = WURZEL / "ausgabe" / "bildtest.zip"
    ziel.parent.mkdir(exist_ok=True)
    info = olatqti.baue_paket(BEISPIELE / "bildtest.yaml", ziel)
    fehler += olatqti.pruefe_paket(ziel)
    with zipfile.ZipFile(ziel) as z:
        im_paket = set(z.namelist())
        imgs = []
        for n in z.namelist():
            if n.endswith(".xml") and not n.startswith(("imsmanifest", "QTI21", "test")):
                root = ET.fromstring(z.read(n))
                imgs += [(root.get("title"), i.get("src"), i.get("width"), i.get("height"))
                         for i in root.iter("{http://www.imsglobal.org/xsd/imsqti_v2p1}img")]
    print("im Zip:", sorted(x for x in im_paket if not x.endswith(".xml")))
    for t in imgs:
        print("  img:", t)
    if len(imgs) != 4 or not {"s1_bild1.png", "s2_bild1.jpg", "s2_bild2.png"} <= im_paket:
        fehler.append(f"Bilder fehlen im Zip: {imgs}")
    if any(int(w) > olatqti.MAX_BILDBREITE for _, _, w, _ in imgs):
        fehler.append("Anzeigebreite über dem Maximum")
    for x in fehler:
        print("FEHLER", x)
    print(f"{ziel}  {info['fragen']} Fragen — Bild-Test: {len(fehler)} Fehler")
    return 1 if fehler else 0


BILDTEST = """\
# Test: Bilder im Fragetext (erzeugt von tests/test_bilder.py, 22.09.2026).
# Noch nicht an einem OLAT-Export verifiziert — in OLAT importieren und ansehen.
titel: BILDTEST olat-qti
sektionen:
  - titel: Teil A – Diagramme
    fragen:
      - typ: sc
        titel: A1 Diagramm lesen (PNG)
        frage: Welcher Werkstoff hat im Diagramm die grösste Dehnung?
        bilder:
          - {datei: bilder/s1_bild1.png, alt: "Spannungs-Dehnungs-Diagramm mit drei Werkstoffen"}
        antworten:
          - {text: "Aluminium", richtig: true}
          - {text: "Baustahl", richtig: false}
          - {text: "hochfester Stahl", richtig: false}

      - typ: sc
        titel: A2 Proben erkennen (JPEG)
        frage: Welche Probe ist Kupfer?
        bilder:
          - {datei: bilder/s2_bild1.jpg, alt: "Drei Werkstoffproben A, B und C"}
        antworten:
          - {text: "Probe A", richtig: false}
          - {text: "Probe B", richtig: true}
          - {text: "Probe C", richtig: false}

  - titel: Teil B – Offene Frage
    fragen:
      - typ: freitext
        titel: B1 Zwei Bilder
        punkte: 3
        frage: |
          Die Skizze zeigt ein Blech vor und nach dem Entlasten, das Diagramm die Werkstoffe.

          Erklären Sie mit beiden Abbildungen, weshalb das Blech zurückfedert.
        bilder:
          - {datei: bilder/s2_bild2.png, alt: "Gebogenes Blech vor und nach dem Entlasten"}
          - bilder/s1_bild1.png
        musterloesung: Der **elastische** Anteil der Verformung federt zurück, der **plastische** bleibt.
"""

if __name__ == "__main__":
    sys.exit(main())
