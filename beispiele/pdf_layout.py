"""Test-PDF: Sektionseinleitungen und Antwortform → Fragetyp (27.09.2026). Keine Typangaben in den Titeln.

    app/.venv/Scripts/python beispiele/pdf_layout.py   -> ausgabe/Layout_mit_Loesungen.pdf

Fallen:
- Teil A: Fallbeispiel für ALLE Fragen → Einleitung der Sektion, nicht in jede Frage kopiert.
  A2 nummerierte Antwortlinien («Nennen Sie drei …») → fib mit Liste, freie Reihenfolge → unsicher.
- Teil B: Diagramm und Video für alle Fragen → Bild und Medium der Sektion.
  B1 leere Tabelle mit Kurzantworten → fib; B2 Wortkasten → inlinechoice; B3 Kästchen nummerieren → order;
  B4 Paare verbinden → match.
- Teil C: Text nur für C1 und C2 → keine Einleitung, sondern in diesen zwei Fragen; C3 ohne Text.
ERWARTET und PRUEFUNGEN unten sind der Massstab für beispiele/probe_layout.py.
"""
from pathlib import Path

import pymupdf

HIER = Path(__file__).resolve().parent
L = '<span style="color:#c00000">'  # Lösung in Rot, wie in Pietros Lösungsblättern
LINIE = "_" * 30
VIDEO = "https://www.youtube.com/watch?v=q2LBfTE6LI0"

ERWARTET = {"A1": "sc", "A2": "fib", "A3": "essay", "A4": "numerical",
            "B1": {"fib", "gapmixed"}, "B2": "inlinechoice", "B3": "order", "B4": "match",
            "C1": "hottext", "C2": "essay", "C3": "sc"}
# Wendungen, an denen man sieht, wo ein Text gelandet ist
FALL = "Ausbildung als Polymechanikerin"
DIAGRAMM = "gilt für alle Aufgaben dieses Teils"
LESETEXT = "Kunststoffe werden aus Erdöl"

HTML = f"""
<h1>Lernkontrolle Lehre und Werkstoffe – mit Lösungen</h1>

<h2>Teil A – Der Lehrvertrag von Lara</h2>
<p>Lara ist 16 Jahre alt und beginnt im August ihre {FALL} bei der Muster AG in Winterthur.
Im Lehrvertrag ist eine Probezeit von drei Monaten vereinbart. Nach zwei Wochen verlangt ihr Chef, dass sie
jeden Samstag arbeitet.</p>

<h3>A1 (1 Punkt)</h3>
<p>Wer muss den Lehrvertrag von Lara zusätzlich unterschreiben?</p>
<p>☐ Die Berufsfachschule<br>{L}☒ Ihre Eltern</span><br>☐ Die Gemeinde</p>

<h3>A2 (3 Punkte)</h3>
<p>Nennen Sie drei Pflichten, die Lara als Lernende hat.</p>
<p>1. {LINIE}<br>2. {LINIE}<br>3. {LINIE}</p>
<p>{L}Lösung (je 1 Punkt, Reihenfolge beliebig): Weisungen befolgen, Sorgfalt, Berufsfachschule besuchen, Geheimhaltung</span></p>

<h3>A3 (3 Punkte)</h3>
<p>Begründen Sie, ob der Chef von Lara verlangen darf, dass sie jeden Samstag arbeitet.</p>
<p>{LINIE}{LINIE}<br>{LINIE}{LINIE}<br>{LINIE}{LINIE}<br>{LINIE}{LINIE}</p>
<p>{L}Musterlösung: Nur wenn es im Lehrvertrag vereinbart ist; die wöchentliche Höchstarbeitszeit und die Ruhezeit
müssen eingehalten werden.</span></p>

<h3>A4 (1 Punkt)</h3>
<p>Wie viele Monate darf die Probezeit einer Lehre höchstens dauern?</p>
<p>Antwort: {L}6</span> Monate</p>

<h2>Teil B – Werkstoffe im Zugversuch</h2>
<p>Das Diagramm zeigt drei Werkstoffe im Zugversuch. Es {DIAGRAMM}.</p>
<p><img src="bilder/s1_bild1.png" width="400"/></p>
<p>Video zum Zugversuch: {VIDEO}</p>

<h3>B1 (3 Punkte)</h3>
<p>Tragen Sie für jeden Werkstoff die Festigkeit ein (hoch, mittel oder tief).</p>
<table border="1" cellpadding="4">
<tr><th>Werkstoff</th><th>Festigkeit</th></tr>
<tr><td>hochfester Stahl</td><td>{L}hoch</span></td></tr>
<tr><td>Baustahl</td><td>{L}mittel</span></td></tr>
<tr><td>Aluminium</td><td>{L}tief</span></td></tr>
</table>

<h3>B2 (2 Punkte)</h3>
<p>Setzen Sie die passenden Wörter ein.</p>
<p><b>Wörter:</b> elastisch · plastisch · spröde</p>
<p>Bei kleiner Last verformt sich Stahl {L}elastisch</span>, er federt zurück. Bei grosser Last verformt er sich
{L}plastisch</span>, die Verformung bleibt.</p>

<h3>B3 (1 Punkt)</h3>
<p>Nummerieren Sie die Schritte des Zugversuchs in der richtigen Reihenfolge.</p>
<p>[{L}3</span>] Probe zieht sich, bis sie bricht<br>[{L}1</span>] Probe einspannen<br>
[{L}4</span>] Diagramm auswerten<br>[{L}2</span>] Kraft langsam erhöhen</p>

<h3>B4 (3 Punkte)</h3>
<p>Verbinden Sie jede Legierung mit ihren Hauptbestandteilen.</p>
<p>Stahl ●&nbsp;&nbsp;&nbsp;&nbsp;● Kupfer und Zinn<br>Bronze ●&nbsp;&nbsp;&nbsp;&nbsp;● Eisen und Kohlenstoff<br>
Messing ●&nbsp;&nbsp;&nbsp;&nbsp;● Kupfer und Zink</p>
<p>{L}Lösung: Stahl – Eisen und Kohlenstoff; Bronze – Kupfer und Zinn; Messing – Kupfer und Zink</span></p>

<h2>Teil C – Kunststoffe</h2>
<p><b>Lesen Sie den folgenden Text für die Aufgaben C1 und C2.</b></p>
<p>{LESETEXT} hergestellt. Thermoplaste lassen sich beim Erwärmen wieder formen, Duroplaste dagegen nicht.
Viele Verpackungen bestehen aus Thermoplasten und können rezykliert werden.</p>

<h3>C1 (2 Punkte)</h3>
<p>Unterstreichen Sie im folgenden Satz die zwei Kunststoffarten.</p>
<p>Man unterscheidet {L}<u>Thermoplaste</u></span> und {L}<u>Duroplaste</u></span> nach ihrem Verhalten beim Erwärmen.</p>

<h3>C2 (2 Punkte)</h3>
<p>Erklären Sie, warum sich Thermoplaste besser rezyklieren lassen als Duroplaste.</p>
<p>{LINIE}{LINIE}<br>{LINIE}{LINIE}<br>{LINIE}{LINIE}</p>
<p>{L}Musterlösung: Thermoplaste lassen sich einschmelzen und neu formen, Duroplaste nicht.</span></p>

<h3>C3 (1 Punkt)</h3>
<p>Welches Metall ist am leichtesten?</p>
<p>☐ Eisen<br>{L}☒ Aluminium</span><br>☐ Kupfer</p>
"""


def main() -> Path:
    ziel = HIER.parent / "ausgabe" / "Layout_mit_Loesungen.pdf"
    story = pymupdf.Story(HTML, user_css="body{font-family:sans-serif;font-size:10pt} h3{font-size:11pt}",
                          archive=pymupdf.Archive(str(HIER)))
    writer = pymupdf.DocumentWriter(str(ziel))
    weiter = True
    while weiter:
        geraet = writer.begin_page(pymupdf.paper_rect("a4"))
        weiter, _ = story.place(pymupdf.paper_rect("a4") + (50, 50, -50, -50))
        story.draw(geraet)
        writer.end_page()
    writer.close()
    return ziel


if __name__ == "__main__":
    print(main())
