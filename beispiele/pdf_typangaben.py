"""Test-PDF: Fragetyp steht im Titel der Aufgabe — auch dort, wo die Form etwas anderes nahelegt.

    app/.venv/Scripts/python beispiele/pdf_typangaben.py   -> ausgabe/Typangaben_mit_Loesungen.pdf

Fallen (Form ≠ Titel): 2 Multiple Choice mit nur einer richtigen, 3 Richtig/Falsch mit genau 4 Aussagen
(Form: kprim), 12 Freitext mit Ein-Wort-Antwort (Form: Lückentext). 14 ohne Typangabe (Kontrolle: kprim).
ERWARTET unten ist der Massstab für den Vergleich.
"""
from pathlib import Path

import pymupdf

ERWARTET = {1: "sc", 2: "mc", 3: "matchtruefalse", 4: "kprim", 5: "fib", 6: "numerical", 7: "inlinechoice",
            8: "order", 9: "match", 10: "matchdraganddrop", 11: "hottext", 12: "essay", 13: "upload", 14: "kprim"}

L = '<span style="color:#c00000">'  # Lösung in Rot, wie in Pietros Lösungsblättern

AUFGABEN = [
    ("Aufgabe 1 – Single Choice (1 Punkt)", "Welche Stadt ist die Bundesstadt der Schweiz?",
     f"☐ Zürich<br>{L}☒ Bern</span><br>☐ Genf<br>☐ Basel"),
    ("Aufgabe 2 – Multiple Choice (2 Punkte)", "Welche dieser Stoffe sind Metalle?",
     f"{L}☒ Kupfer</span><br>☐ Holz<br>☐ Glas<br>☐ Porzellan"),
    ("Aufgabe 3 – Richtig/Falsch (2 Punkte)", "Beurteilen Sie die Aussagen zum Lehrvertrag.",
     f"Der Lehrvertrag muss schriftlich sein. {L}richtig</span><br>"
     f"Die Probezeit dauert mindestens 6 Monate. {L}falsch</span><br>"
     f"Lernende haben Anspruch auf Ferien. {L}richtig</span><br>"
     f"Der Lehrvertrag braucht keine Unterschrift der Eltern. {L}falsch</span>"),
    ("Aufgabe 4 – Kprim (2 Punkte)", "Beurteilen Sie: Was gilt für Minderjährige in der Lehre?",
     f"Höchstens 9 Stunden Arbeit pro Tag. {L}richtig</span><br>"
     f"Nachtarbeit ist ohne Bewilligung erlaubt. {L}falsch</span><br>"
     f"Mindestens 5 Wochen Ferien bis 20 Jahre. {L}richtig</span><br>"
     f"Überstunden sind unbeschränkt möglich. {L}falsch</span>"),
    ("Aufgabe 5 – Lückentext (1 Punkt)", "Ergänzen Sie.",
     f"Die Aufsicht über die Lehre hat das kantonale {L}Berufsbildungsamt</span>."),
    ("Aufgabe 6 – Zahl (1 Punkt)", "Eine Lernende arbeitet 5 Tage à 8,5 Stunden. Wie viele Stunden sind das pro Woche?",
     f"Antwort: {L}42,5</span> Stunden"),
    ("Aufgabe 7 – Dropdown (1 Punkt)", "Wählen Sie das richtige Wort.",
     f"Die Probezeit dauert höchstens (1 / {L}3</span> / 6) Monate."),
    ("Aufgabe 8 – Reihenfolge (1 Punkt)", "Bringen Sie die Schritte bei einem Konflikt in die richtige Reihenfolge.",
     f"Lehraufsicht kontaktieren · Gespräch mit Berufsbildner · Vertrauensperson einbeziehen<br>"
     f"{L}Lösung: Gespräch mit Berufsbildner → Vertrauensperson einbeziehen → Lehraufsicht kontaktieren</span>"),
    ("Aufgabe 9 – Zuordnung (Matrix) (2 Punkte)", "Kreuzen Sie an, wer den Lehrvertrag unterschreibt.",
     "<table border='1' cellpadding='3'><tr><th></th><th>unterschreibt</th><th>unterschreibt nicht</th></tr>"
     f"<tr><td>Lernende Person</td><td>{L}X</span></td><td></td></tr>"
     f"<tr><td>Berufsfachschule</td><td></td><td>{L}X</span></td></tr>"
     f"<tr><td>Lehrbetrieb</td><td>{L}X</span></td><td></td></tr></table>"),
    ("Aufgabe 10 – Drag and Drop (2 Punkte)", "Ziehen Sie die Begriffe in die richtige Gruppe: Pflichten oder Rechte.",
     f"Ferien · Sorgfaltspflicht · Lohn · Schweigepflicht<br>"
     f"{L}Rechte: Ferien, Lohn — Pflichten: Sorgfaltspflicht, Schweigepflicht</span>"),
    ("Aufgabe 11 – Hottext (1 Punkt)", "Markieren Sie alle Verben im Satz.",
     f"Die Lernende {L}arbeitet</span> im Betrieb und {L}besucht</span> die Berufsfachschule."),
    ("Aufgabe 12 – Freitext (2 Punkte)", "Wie heisst die Stelle des Kantons, die Lehrverhältnisse beaufsichtigt?",
     f"{L}Lehraufsicht (kantonales Berufsbildungsamt)</span>"),
    ("Aufgabe 13 – Upload (2 Punkte)", "Laden Sie Ihren unterschriebenen Lehrvertrag als PDF hoch.", ""),
    ("Aufgabe 14 (2 Punkte)", "Beurteilen Sie die Aussagen zur Berufsfachschule. Richtig oder falsch?",
     f"Der Schulbesuch ist obligatorisch. {L}richtig</span><br>"
     f"Die Schulzeit gilt als Arbeitszeit. {L}richtig</span><br>"
     f"Der Lehrbetrieb darf den Schulbesuch verbieten. {L}falsch</span><br>"
     f"Schulstoff wird nie geprüft. {L}falsch</span>"),
]


def main() -> Path:
    html = "<h1>Lernkontrolle Lehrvertrag – mit Lösungen</h1>" + "".join(
        f"<h3>{t}</h3><p>{f}</p><p>{a}</p>" for t, f, a in AUFGABEN)
    doc = pymupdf.open()
    story = pymupdf.Story(html, user_css="body{font-family:sans-serif;font-size:10pt} h3{font-size:11pt}")
    ziel = Path(__file__).resolve().parent.parent / "ausgabe" / "Typangaben_mit_Loesungen.pdf"
    writer = pymupdf.DocumentWriter(str(ziel))
    weiter = True
    while weiter:
        geraet = writer.begin_page(pymupdf.paper_rect("a4"))
        weiter, _ = story.place(pymupdf.paper_rect("a4") + (50, 50, -50, -50))
        story.draw(geraet)
        writer.end_page()
    writer.close()
    doc.close()
    return ziel


if __name__ == "__main__":
    print(main())
