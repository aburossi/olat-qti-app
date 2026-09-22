"""Erzeugt «Pruefung_Gasgesetze_mit_Loesungen.pdf» — dieselbe Prüfung wie saetze/2026-09-22_gasgesetze.yaml,
aber so, wie eine Lehrperson sie in Word schreibt: Formeln als Klartext (p1 · V1 = p2 · V2), die vier
Bilder bei ihren Fragen, ein Logo auf jeder Seite (darf nicht im Test landen).

Zum Testen der Streamlit-App: Bilder zuordnen, Formeln nach LaTeX umsetzen, Sektionen, Zahl-Lücken.

    app/.venv/Scripts/python beispiele/bilder_gasgesetze.py     # zuerst, falls die Bilder fehlen
    app/.venv/Scripts/python beispiele/pdf_gasgesetze.py
"""
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "beispiele"))
from pdf_fotosynthese import Blatt  # noqa: E402  (Seitenaufbau mit Logo)

BILDER = WURZEL / "saetze" / "bilder"
ZIEL = WURZEL / "ausgabe" / "Pruefung_Gasgesetze_mit_Loesungen.pdf"


def bild(name):
    return (BILDER / name).read_bytes()


def richtig_falsch(bl, aussagen):
    for text, wahr in aussagen:
        bl.text(f"{'[x] richtig  [  ] falsch' if wahr else '[  ] richtig  [x] falsch'}    {text}", abstand=2, einzug=15)
    bl.y += 3


def main():
    bl = Blatt()
    bl.text("Prüfung Gasgesetze - mit Lösungen", 16, True, 2)
    bl.text("Physik · Bearbeitungszeit 30 Minuten · Total 20 Punkte · Hilfsmittel: Taschenrechner", 10, abstand=14)

    bl.text("Teil A - Grundlagen | 6 Punkte", 13, True, 8)
    bl.text("A1. Welches Gasgesetz beschreibt der Verlauf im Diagramm? (1 P)", fett=True)
    bl.bild(bild("gas_pv_diagramm.png"), 290, 168)
    bl.auswahl(["Gesetz von Boyle-Mariotte", "Gesetz von Gay-Lussac", "Gesetz von Amontons", "Gesetz von Avogadro"], {0})
    bl.text("Lösung: Boyle-Mariotte. Bei konstanter Temperatur gilt p · V = konstant, die Kurve ist eine Hyperbel.",
            abstand=12)

    bl.text("A2. Welche Gleichung gilt für ein ideales Gas bei konstantem Volumen (Gesetz von Amontons)? (1 P)", fett=True)
    bl.auswahl(["p / T = konstant", "p · V = konstant", "V / T = konstant", "p · T = konstant"], {0})
    bl.text("Lösung: p / T = konstant. Druck und absolute Temperatur sind proportional.", abstand=12)

    bl.text("A3. Welche Annahmen gehören zum Modell des idealen Gases? (2 P)", fett=True)
    bl.auswahl(["Die Teilchen haben kein Eigenvolumen.", "Zwischen den Teilchen wirken keine Anziehungskräfte.",
                "Die Teilchen stossen elastisch zusammen.", "Das Gas wird bei tiefer Temperatur flüssig."], {0, 1, 2})
    bl.text("Lösung: A, B und C. Kondensation ist eine Eigenschaft realer Gase.", abstand=12)

    bl.neue_seite()
    bl.text("A4. Beurteilen Sie die Aussagen zur allgemeinen Gasgleichung p · V = n · R · T. (2 P)", fett=True)
    richtig_falsch(bl, [
        ("Verdoppelt sich bei gleicher Temperatur der Druck, halbiert sich das Volumen.", True),
        ("Steigt bei gleichem Druck die Temperatur von 20 °C auf 40 °C, verdoppelt sich das Volumen.", False),
        ("Die universelle Gaskonstante beträgt R = 8,314 J/(mol · K).", True),
        ("Entweicht bei gleichem Volumen und gleicher Temperatur Gas aus dem Behälter, steigt der Druck.", False)])
    bl.text("Lösung: richtig, falsch, richtig, falsch. Zu Aussage 2: Es zählt die absolute Temperatur "
            "(293 K auf 313 K).", abstand=14)

    bl.text("Teil B - Rechnen | 8 Punkte", 13, True, 8)
    bl.text("B1. Im Zylinder hat ein Gas den Druck p1 = 1 bar und das Volumen V1 = 6 L. Der Kolben wird bei "
            "konstanter Temperatur hineingeschoben, bis V2 = 2 L. Berechnen Sie den Druck p2. (2 P)", fett=True)
    bl.bild(bild("gas_zylinder.png"), 280, 140)
    bl.text("Lösung: p1 · V1 = p2 · V2, also p2 = 1 bar · 6 L / 2 L = 3 bar.", abstand=12)

    bl.text("B2. Das Diagramm zeigt, wie das Volumen eines Gases bei konstantem Druck von der Temperatur abhängt. "
            "Ein Gas hat bei T1 = 300 K das Volumen V1 = 3 L und wird bei konstantem Druck auf T2 = 400 K erwärmt. "
            "Berechnen Sie das Volumen V2. (2 P)", fett=True)
    bl.bild(bild("gas_vt_diagramm.png"), 290, 168)
    bl.text("Lösung: V1 / T1 = V2 / T2, also V2 = 3 L · 400 K / 300 K = 4 L.", abstand=12)

    bl.neue_seite()
    bl.text("B3. In einem Behälter mit V = 24,94 L herrscht bei T = 300 K der Druck p = 100 000 Pa. "
            "Verwenden Sie R = 8,314 J/(mol · K). Berechnen Sie die Stoffmenge n des Gases. (2 P)", fett=True)
    bl.text("Lösung: n = p · V / (R · T) = 100 000 Pa · 0,02494 m³ / (8,314 J/(mol · K) · 300 K) = 1,0 mol. "
            "Toleranz: 0,95 bis 1,05 mol.", abstand=12)

    bl.text("B4. Rechnen Sie um und runden Sie auf ganze Zahlen. (2 P)", fett=True)
    bl.text("25 °C entsprechen ________ K. Der absolute Nullpunkt liegt bei ________ °C.")
    bl.text("Lösung: 298 K; -273 °C (je plus/minus 1 akzeptiert).", abstand=14)

    bl.text("Teil C - Verstehen | 6 Punkte", 13, True, 8)
    bl.text("C1. Streichen Sie das Falsche. (2 P)", fett=True)
    bl.text("Wird ein geschlossener Behälter erwärmt, (steigt / sinkt / bleibt gleich) der Druck, weil die Teilchen "
            "(schneller / langsamer) gegen die Wände stossen.")
    bl.text("Lösung: steigt; schneller", abstand=12)

    bl.text("C2. Ein Luftballon mit V1 = 4 L wird aus dem Zimmer (22 °C) auf den Balkon (-5 °C) gebracht und wird "
            "kleiner. Der Druck bleibt ungefähr gleich. Erklären Sie die Beobachtung mit dem passenden Gasgesetz "
            "und berechnen Sie das neue Volumen V2. (4 P)", fett=True)
    bl.bild(bild("gas_ballon.jpg"), 280, 168)
    bl.text("Lösung: Es gilt das Gesetz von Gay-Lussac (Druck konstant): V1 / T1 = V2 / T2. In der Kälte bewegen "
            "sich die Teilchen langsamer, das Gas zieht sich zusammen. Temperaturen in Kelvin: T1 = 295,15 K, "
            "T2 = 268,15 K. Damit V2 = 4 L · 268,15 / 295,15 = ca. 3,6 L. "
            "Punkte: Gesetz genannt 1 P; Erklärung mit Teilchenbewegung 1 P; Umrechnung in Kelvin 1 P; "
            "Ergebnis 1 P.")

    ZIEL.parent.mkdir(exist_ok=True)
    bl.doc.save(ZIEL)
    print(ZIEL, bl.doc.page_count, "Seiten")


if __name__ == "__main__":
    main()
