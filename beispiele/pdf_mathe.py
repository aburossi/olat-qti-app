"""Erzeugt «Pruefung_Mathematik_Formeln_mit_Loesungen.pdf» — Formeln wie aus Word: Unicode-Mathe-
zeichen (√ ∫ ∑ ± π ², ₁), dazu gestapelte Brüche, eine Matrix und ein Binomialkoeffizient, die beim
Textauslesen in einzelne Zeilen zerfallen. Test für die Streamlit-App: setzt das Modell daraus
korrektes LaTeX zusammen?

    app/.venv/Scripts/python beispiele/pdf_mathe.py
"""
import sys
from pathlib import Path

import pymupdf

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "beispiele"))
from pdf_fotosynthese import Blatt  # noqa: E402

ZIEL = WURZEL / "ausgabe" / "Pruefung_Mathematik_Formeln_mit_Loesungen.pdf"
CAMBRIA = "C:/Windows/Fonts/cambria.ttc"


class MatheBlatt(Blatt):
    def neue_seite(self):
        super().neue_seite()
        self.s.insert_font(fontname="cam", fontfile=CAMBRIA)
        self.s.insert_font(fontname="camb", fontfile="C:/Windows/Fonts/cambriab.ttf")

    def text(self, t, groesse=10.5, fett=False, abstand=4, einzug=0):
        """Wie Blatt.text, aber in Cambria — die Standardschrift kennt − √ ₁ ′ ˣ nicht."""
        r = pymupdf.Rect(50 + einzug, self.y, 550, self.y + 400)
        rest = self.s.insert_textbox(r, t, fontsize=groesse, fontname="camb" if fett else "cam")
        self.y += 400 - rest + abstand

    def formel(self, t, groesse=12, einzug=30, abstand=8):
        """Eine Formelzeile in Cambria (Unicode-Mathe wie Word)."""
        self.s.insert_text((50 + einzug, self.y + groesse), t, fontname="cam", fontsize=groesse)
        self.y += groesse + abstand

    def gestapelt(self, x, links, zaehler, nenner, rechts="", groesse=12):
        """Bruch mit Bruchstrich: links  zaehler / nenner  rechts, auf einer gemeinsamen Mittellinie."""
        f = pymupdf.Font(fontfile=CAMBRIA)
        mitte = self.y + groesse + 6
        self.s.insert_text((x, mitte + 4), links, fontname="cam", fontsize=groesse)
        x0 = x + f.text_length(links, groesse) + 4
        breite = max(f.text_length(zaehler, groesse), f.text_length(nenner, groesse)) + 6
        self.s.insert_text((x0 + (breite - f.text_length(zaehler, groesse)) / 2, mitte - 4), zaehler,
                           fontname="cam", fontsize=groesse)
        self.s.draw_line((x0, mitte), (x0 + breite, mitte), width=0.8)
        self.s.insert_text((x0 + (breite - f.text_length(nenner, groesse)) / 2, mitte + groesse + 2), nenner,
                           fontname="cam", fontsize=groesse)
        self.s.insert_text((x0 + breite + 4, mitte + 4), rechts, fontname="cam", fontsize=groesse)
        self.y += 2 * groesse + 16

    def matrix(self, x, links, zeilen, rechts="", groesse=12):
        """2×2-Matrix mit runden Klammern, zeilenweise gesetzt."""
        f = pymupdf.Font(fontfile=CAMBRIA)
        oben = self.y + 4
        self.s.insert_text((x, oben + groesse + 8), links, fontname="cam", fontsize=groesse)
        x0 = x + f.text_length(links, groesse) + 6
        hoehe = len(zeilen) * (groesse + 6)
        self.s.draw_bezier((x0 + 5, oben), (x0 - 2, oben + hoehe / 3), (x0 - 2, oben + 2 * hoehe / 3), (x0 + 5, oben + hoehe), width=0.8)
        for i, zeile in enumerate(zeilen):
            for j, eintrag in enumerate(zeile):
                self.s.insert_text((x0 + 10 + j * 22, oben + (i + 1) * (groesse + 4)), eintrag, fontname="cam", fontsize=groesse)
        x1 = x0 + 10 + len(zeilen[0]) * 22
        self.s.draw_bezier((x1 - 3, oben), (x1 + 4, oben + hoehe / 3), (x1 + 4, oben + 2 * hoehe / 3), (x1 - 3, oben + hoehe), width=0.8)
        self.s.insert_text((x1 + 10, oben + groesse + 8), rechts, fontname="cam", fontsize=groesse)
        self.y += hoehe + 12


def main():
    bl = MatheBlatt()
    bl.text("Prüfung Mathematik - Formeln - mit Lösungen", 16, True, 2)
    bl.text("Analysis, Algebra und Stochastik · Bearbeitungszeit 30 Minuten · Total 14 Punkte", 10, abstand=14)

    bl.text("Teil A - Algebra und Analysis | 8 Punkte", 13, True, 8)
    bl.text("A1. Lösen Sie die Gleichung x² − 5x + 6 = 0 mit der Mitternachtsformel. Welche Lösungen hat sie? (1 P)",
            fett=True)
    bl.gestapelt(80, "x₁,₂ = ", "−b ± √(b² − 4ac)", "2a")
    bl.auswahl(["x₁ = 2, x₂ = 3", "x₁ = −2, x₂ = −3", "x₁ = 1, x₂ = 6", "x₁ = −1, x₂ = 6"], {0})
    bl.text("Lösung: x₁ = 2, x₂ = 3, denn √(25 − 24) = 1 und (5 ± 1) / 2 ergibt 2 und 3.", abstand=12)

    bl.text("A2. Berechnen Sie das bestimmte Integral. (2 P)", fett=True)
    bl.formel("∫₀² (3x² + 1) dx")
    bl.auswahl(["10", "8", "12", "14"], {0})
    bl.text("Lösung: [x³ + x]₀² = 8 + 2 = 10.", abstand=12)

    bl.text("A3. Berechnen Sie die Summe der natürlichen Zahlen von 1 bis 100. (2 P)", fett=True)
    bl.gestapelt(80, "∑ₖ₌₁¹⁰⁰ k = ", "n(n + 1)", "2", "  mit n = 100")
    bl.text("Lösung: 5050 (exakt).", abstand=12)

    bl.text("A4. Beurteilen Sie die Aussagen. (2 P)", fett=True)
    for aussage, wahr in [("e^(iπ) + 1 = 0", True), ("(a + b)² = a² + b²", False),
                          ("lim_(x→0) sin(x) / x = 1", True), ("∑ₖ₌₁^∞ 1/k² = π²/4", False)]:
        bl.formel(f"{'[x] richtig  [  ] falsch' if wahr else '[  ] richtig  [x] falsch'}      {aussage}", 11, 15, 5)
    bl.text("Lösung: richtig, falsch, richtig, falsch. Die Reihe konvergiert gegen π²/6.", abstand=12)

    bl.neue_seite()
    bl.text("A5. Berechnen Sie die Determinante der Matrix A. (1 P)", fett=True)
    bl.matrix(80, "A = ", [["3", "2"], ["1", "4"]], "      det(A) = a₁₁ · a₂₂ − a₁₂ · a₂₁")
    bl.text("Lösung: 3 · 4 − 2 · 1 = 10.", abstand=14)

    bl.text("Teil B - Anwenden | 6 Punkte", 13, True, 8)
    bl.text("B1. Leiten Sie die Funktion ab und fassen Sie zusammen. Nennen Sie die verwendete Regel. (3 P)",
            fett=True)
    bl.formel("f(x) = x² · eˣ")
    bl.text("Lösung: Produktregel (u · v)′ = u′ · v + u · v′ mit u = x² und v = eˣ. "
            "f′(x) = 2x · eˣ + x² · eˣ = (x² + 2x) · eˣ. "
            "Punkte: Regel genannt 1 P; korrekte Ableitung 1 P; zusammengefasst 1 P.", abstand=12)

    bl.text("B2. Eine faire Münze wird viermal geworfen. X ist die Anzahl «Kopf». Berechnen Sie P(X = 2) "
            "mit der Binomialverteilung. (3 P)", fett=True)
    bl.matrix(80, "P(X = k) = ", [["n"], ["k"]], "· pᵏ · (1 − p)ⁿ⁻ᵏ     mit n = 4, p = 0,5")
    bl.text("Lösung: P(X = 2) = 6 · 0,5² · 0,5² = 6/16 = 0,375 (Toleranz ± 0,001).")

    ZIEL.parent.mkdir(exist_ok=True)
    bl.doc.save(ZIEL)
    print(ZIEL, bl.doc.page_count, "Seiten")


if __name__ == "__main__":
    main()
