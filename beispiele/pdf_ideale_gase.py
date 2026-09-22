"""Erzeugt «Ideale_Gase_Videotest_mit_Loesungen.pdf» — Abschlusstest der App (22.09.2026).

Grundlage: Video «Ideale Gasgleichung – Was kann die?» (simpleclub, YouTube q2LBfTE6LI0) und sein Transkript.
Teil A Verständnisfragen zum Video (mit Link), Teil B Rechnen mit einfachen und komplexen Formeln (Unicode wie
aus Word, gestapelte Brüche), Teil C handlungsorientierte offene Fragen für Polymechaniker/innen.

    app/.venv/Scripts/python beispiele/pdf_ideale_gase.py
"""
import sys
from pathlib import Path

import pymupdf

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "beispiele"))
from pdf_mathe import MatheBlatt  # noqa: E402

ZIEL = WURZEL / "ausgabe" / "Ideale_Gase_Videotest_mit_Loesungen.pdf"
VIDEO = "https://www.youtube.com/watch?v=q2LBfTE6LI0"
BILDER = WURZEL / "saetze" / "bilder"
UNTEN = 790


class Test(MatheBlatt):
    """MatheBlatt mit automatischem Seitenumbruch."""

    def platz(self, hoehe):
        if self.y + hoehe > UNTEN:
            self.neue_seite()

    def text(self, t, groesse=10.5, fett=False, abstand=4, einzug=0):
        f = pymupdf.Font(fontfile="C:/Windows/Fonts/cambriab.ttf" if fett else "C:/Windows/Fonts/cambria.ttc")
        zeilen = f.text_length(t, groesse) / (500 - einzug) + 1
        self.platz(zeilen * groesse * 1.35 + abstand)
        super().text(t, groesse, fett, abstand, einzug)

    def bild(self, daten, breite, hoehe):
        self.platz(hoehe + 12)  # sonst wird das Bild am Seitenende abgeschnitten
        super().bild(daten, breite, hoehe)

    def formel(self, t, groesse=12, einzug=30, abstand=8):
        self.platz(groesse + abstand)
        super().formel(t, groesse, einzug, abstand)

    def gestapelt(self, x, links, zaehler, nenner, rechts="", groesse=12):
        self.platz(2 * groesse + 16)
        super().gestapelt(x, links, zaehler, nenner, rechts, groesse)

    def frage(self, t, bild_hoehe=0):
        # Frage, Bild und Antwortoptionen gehören zusammen auf eine Seite
        self.platz(90 + bild_hoehe)
        self.text(t, fett=True)

    def teil(self, t):
        self.platz(140)
        self.text(t, 13, True, 8)


def main():
    bl = Test()
    bl.text("Ideale Gase - vom Furz bis zur Druckluftflasche", 16, True, 2)
    bl.text("Videotest mit Lösungen · Physik/Chemie für Polymechaniker/innen · 45 Minuten · Total 32 Punkte", 10,
            abstand=4)
    bl.text("Grundlage: Video «Ideale Gasgleichung - Was kann die?» (simpleclub, 4 Minuten). "
            "Schauen Sie das Video zuerst ganz an. Die Fragen in Teil A beziehen sich direkt darauf.", 10, abstand=14)

    # ---------------------------------------------------------------- Teil A
    bl.teil("Teil A - Verständnisfragen zum Video | 12 Punkte")
    bl.frage("A1. Schauen Sie das Video an. Wann nennt man ein Gas laut Video «ideal»? (1 P)")
    bl.text("Video: " + VIDEO, 9.5, abstand=4, einzug=15)
    bl.auswahl(["Wenn es zwischen den Teilchen nur elastische Stösse und keine anderen Wechselwirkungen gibt.",
                "Wenn die Teilchen einen «Hammer-Body» haben.",
                "Wenn das Gas genau 20 °C warm ist.",
                "Wenn das Gas geruchlos ist - Bromdämpfe und Fürze sind deshalb nie ideal."], {0})
    bl.text("Lösung: A. Das gilt für echte Gase nie ganz, ist aber oft eine sehr gute Näherung.", abstand=12)

    bl.frage("A2. Ordnen Sie jedem Gasgesetz zu, welche Grösse dabei konstant bleibt. (2 P)")
    spalten_x = (250, 330, 410)
    bl.platz(70)
    for x, kopf in zip(spalten_x, ("T konstant", "p konstant", "V konstant")):
        bl.s.insert_text((x, bl.y + 10), kopf, fontname="cam", fontsize=10)
    bl.y += 16
    for gesetz, spalte in [("Gesetz von Boyle-Mariotte", 0), ("Gesetz von Gay-Lussac", 1), ("Gesetz von Amontons", 2)]:
        bl.s.insert_text((65, bl.y + 10), gesetz, fontname="cam", fontsize=10)
        for i, x in enumerate(spalten_x):
            bl.s.insert_text((x + 15, bl.y + 10), "[x]" if i == spalte else "[  ]", fontname="cam", fontsize=10)
        bl.y += 15
    bl.y += 4
    bl.text("Lösung: Boyle-Mariotte - Temperatur konstant; Gay-Lussac - Druck konstant; Amontons - Volumen konstant.",
            abstand=12)

    bl.frage("A3. Beurteilen Sie die Aussagen aus dem Video. (2 P)")
    for aussage, wahr in [("Bei gleicher Temperatur gilt: je höher der Druck, desto kleiner das Volumen.", True),
                          ("Bei konstantem Volumen sinkt der Druck, wenn die Temperatur steigt.", False),
                          ("Bei festem Druck und fester Temperatur ist das Volumen proportional zur Stoffmenge.", True),
                          ("Die Gasgesetze gelten für Bromdämpfe im Labor, aber nicht für einen Furz.", False)]:
        bl.text(f"{'[x] richtig  [  ] falsch' if wahr else '[  ] richtig  [x] falsch'}    {aussage}", 10,
                abstand=2, einzug=15)
    bl.text("Lösung: richtig, falsch, richtig, falsch. Laut Video gilt alles «egal ob ein Furz, irgendwelche "
            "Bromdämpfe im Labor oder einfach die Gase in der Luft».", abstand=12)

    bl.frage("A4. Das Video betont die richtigen Einheiten für die ideale Gasgleichung. Streichen Sie das Falsche. (3 P)")
    bl.text("Der Druck wird in (Pascal / bar / Atmosphären) angegeben, das Volumen in (Kubikmetern / Litern / "
            "Millilitern) und die Temperatur in (Kelvin / Grad Celsius).")
    bl.text("Lösung: Pascal; Kubikmetern; Kelvin", abstand=12)

    bl.frage("A5. Ergänzen Sie die Zahlenwerte aus dem Video. (2 P)")
    bl.text("Die universelle Gaskonstante beträgt R = ________ J/(mol · K). "
            "Der Atmosphärendruck beträgt ________ Pa.")
    bl.text("Lösung: R = 8,314 J/(mol · K) (Toleranz ± 0,001); Atmosphärendruck 1,013 · 10⁵ Pa = 101 300 Pa "
            "(Toleranz ± 100 Pa).", abstand=14)

    bl.frage("A6. Das Diagramm zeigt Messwerte eines Gases bei konstanter Temperatur. "
             "Welches Gesetz ist dargestellt? (1 P)", bild_hoehe=200)
    bl.bild((BILDER / "gas_pv_diagramm.png").read_bytes(), 290, 168)
    bl.auswahl(["Gesetz von Boyle-Mariotte", "Gesetz von Gay-Lussac", "Gesetz von Amontons",
                "Gesetz von Avogadro"], {0})
    bl.text("Lösung: A. Druck und Volumen sind umgekehrt proportional, die Kurve ist eine Hyperbel.", abstand=12)

    bl.frage("A7. Dieses Diagramm zeigt ein Gas bei konstantem Druck. Was passiert mit dem Volumen, wenn die "
             "absolute Temperatur verdoppelt wird? (1 P)", bild_hoehe=200)
    bl.bild((BILDER / "gas_vt_diagramm.png").read_bytes(), 290, 168)
    bl.auswahl(["Es verdoppelt sich.", "Es halbiert sich.", "Es bleibt gleich.",
                "Es vervierfacht sich."], {0})
    bl.text("Lösung: A. Volumen und absolute Temperatur sind proportional (Gesetz von Gay-Lussac). "
            "Achtung: Das gilt nur in Kelvin, nicht in Grad Celsius.", abstand=14)

    # ---------------------------------------------------------------- Teil B
    bl.teil("Teil B - Rechnen mit den Gasgesetzen | 10 Punkte")
    bl.frage("B1. Das Beispiel aus dem Video: Ein Reifen wird mit p₁ = 2 bar gefüllt und fasst V₁ = 3 L. "
             "Welches Volumen V₂ bräuchte die Luft bei normalem Druck p₂ = 1 bar und gleicher Temperatur? (2 P)", bild_hoehe=165)
    bl.bild((BILDER / "gas_zylinder.png").read_bytes(), 260, 130)
    bl.formel("p₁ · V₁ = p₂ · V₂")
    bl.text("Lösung: V₂ = p₁ · V₁ / p₂ = 2 bar · 3 L / 1 bar = 6 L (Toleranz ± 0,05 L).", abstand=12)

    bl.frage("B2. Welche Umformung der idealen Gasgleichung p · V = n · R · T liefert die Stoffmenge n? (1 P)")
    bl.auswahl(["n = p · V / (R · T)", "n = R · T / (p · V)", "n = p · V · R · T", "n = p · R / (V · T)"], {0})
    bl.text("Lösung: A. Beide Seiten durch R · T teilen.", abstand=12)

    bl.frage("B3. Das Video fragt, welche Stoffmenge Gas in Ihrem Zimmer herumfliegt. Ein Schulzimmer ist "
             "5 m lang, 4 m breit und 2,5 m hoch. Es herrschen 20 °C und Atmosphärendruck. Berechnen Sie n. (3 P)")
    bl.gestapelt(80, "n = ", "p · V", "R · T", "  mit  V = 50 m³,  T = 293,15 K,  p = 1,013 · 10⁵ Pa")
    bl.text("Lösung: n = 1,013 · 10⁵ Pa · 50 m³ / (8,314 J/(mol · K) · 293,15 K) = 2078 mol "
            "(Toleranz ± 21 mol, also 1 %).", abstand=12)

    bl.frage("B4. Aus der Gasgleichung folgt das Molvolumen V_m, das Volumen von einem Mol Gas. Berechnen Sie "
             "V_m in Litern bei 0 °C und Atmosphärendruck. (2 P)")
    bl.gestapelt(80, "V_m = ", "V", "n", "")
    bl.gestapelt(80, "     = ", "R · T", "p", "  mit  T = 273,15 K,  p = 1,013 · 10⁵ Pa")
    bl.text("Lösung: V_m = 8,314 · 273,15 / 101 300 m³ = 0,02242 m³ = 22,4 L (Toleranz ± 0,1 L).", abstand=12)

    bl.frage("B5. Ein geschlossener Druckluftbehälter enthält Luft mit p₁ = 8 bar (absolut) bei ϑ₁ = 20 °C. "
             "In der Sonne erwärmt er sich auf ϑ₂ = 50 °C, das Volumen bleibt gleich. Berechnen Sie den "
             "neuen Druck p₂. (2 P)")
    bl.gestapelt(80, "", "p₁", "T₁", "")
    bl.y -= 40
    bl.gestapelt(118, "= ", "p₂", "T₂", "   ⇒   p₂ = p₁ · T₂ / T₁")
    bl.text("Lösung: p₂ = 8 bar · 323,15 K / 293,15 K = 8,82 bar (Toleranz ± 0,05 bar).", abstand=14)

    # ---------------------------------------------------------------- Teil C
    bl.neue_seite()
    bl.teil("Teil C - Handlungsorientierte Aufgaben für Polymechaniker/innen | 10 Punkte")
    bl.frage("C1. Druckluft an der Südfassade. Ihr Betrieb will den Druckluftbehälter (500 L, Betriebsdruck "
             "8 bar) aus Platzgründen draussen an die Südfassade stellen. Im Sommer wird die Blechwand dort über "
             "50 °C heiss. Ihre Berufsbildnerin fragt Sie um Ihre Meinung. Beurteilen Sie die Idee mit dem "
             "passenden Gasgesetz und schlagen Sie zwei konkrete Massnahmen vor. (4 P)")
    bl.text("Lösung: Bei konstantem Volumen gilt das Gesetz von Amontons: p₁ / T₁ = p₂ / T₂. Erwärmt sich die Luft "
            "von 20 °C auf 50 °C, steigt der Druck um rund 10 % (8 bar werden etwa 8,8 bar, gerechnet mit dem "
            "absoluten Druck). Das Sicherheitsventil kann ansprechen, der Behälter wird stärker belastet, und die "
            "warme Luft bringt mehr Feuchtigkeit ins Netz. Massnahmen: Standort im Schatten oder im Innenraum, "
            "Sonnenschutz oder Beschattung, Sicherheitsventil und Manometer regelmässig prüfen, Kondensat "
            "ablassen, Betriebsdruck im Sommer etwas tiefer einstellen. Punkte: Gesetz genannt 1 P; Wirkung "
            "(Druck steigt, rund 10 %) 1 P; zwei sinnvolle Massnahmen je 1 P.", abstand=12)

    bl.frage("C2. Reicht das Schutzgas? Für einen Schweissauftrag steht eine Argonflasche mit 50 L Inhalt und "
             "200 bar Fülldruck bereit. Beim WIG-Schweissen brauchen Sie 15 L/min Argon bei Atmosphärendruck, und "
             "Sie schweissen heute insgesamt 4 Stunden. Reicht die Flasche für den ganzen Tag? Begründen Sie mit "
             "einer Rechnung. (4 P)")
    bl.text("Lösung: Boyle-Mariotte bei gleicher Temperatur: p₁ · V₁ = p₂ · V₂, also V₂ = 200 bar · 50 L / 1 bar = "
            "10 000 L Argon (vereinfacht, Überdruck und Restdruck vernachlässigt). Bedarf: 15 L/min · 240 min = "
            "3 600 L. Die Flasche reicht, sogar für knapp drei solche Tage. Punkte: Gesetz und Ansatz 1 P; "
            "verfügbares Volumen 1 P; Bedarf 1 P; begründete Entscheidung 1 P.", abstand=12)

    bl.frage("C3. Das Video endet mit einem Auftrag: «Postet mal eine Eselsbrücke für p · V = n · R · T.» Erfinden "
             "Sie eine Eselsbrücke, die ein Polymechaniker-Lernender in der Werkstatt nie mehr vergisst. "
             "Erklären Sie kurz, welches Wort für welche Grösse steht. (2 P)")
    bl.text("Lösung: Individuell. Beispiele: «Der Pavian (p · V) ist gleich Nashorn, Rhino, Tiger (n · R · T).» "
            "oder «Präzision vor Nachlässigkeit: Rechnen tut gut.» Punkte: alle fünf Grössen in der richtigen "
            "Reihenfolge und Seite 1 P; Zuordnung erklärt 1 P. Originalität darf mit einem Lächeln belohnt werden.")

    ZIEL.parent.mkdir(exist_ok=True)
    bl.doc.save(ZIEL)
    print(ZIEL, bl.doc.page_count, "Seiten")


if __name__ == "__main__":
    main()
