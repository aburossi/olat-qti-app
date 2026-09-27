"""Vier Test-PDFs für eingebettete Medien (27.09.2026) — für den Online-Test der App:

    app/.venv/Scripts/python beispiele/pdf_medien_eingebettet.py   -> ausgabe/Medien_1_YouTube.pdf … Medien_4_Gemischt.pdf

1 YouTube: Ausschnitt mit «(0:30–1:30)», Ausschnitt hinter einem Wort, ganzes Video.
2 SRF-Video: Tagesschau-Beitrag (Einbettungslink), ganze Tagesschau «ab 14:17», Beitrag in der Einleitung.
3 SRF-Audio: Echo-Beitrag (Einbettungslink), Krimi «ab 0:30», Audio-Seite ohne URN (erwartet: Warnung der App).
4 Gemischt wie eine LK: Teile, SRF-Video in der Einleitung, YouTube-Ausschnitt, eingefügter <iframe>-Code.
Nur Links — nichts heruntergeladen. Die Fragen stützen sich nur auf die Titel der Beiträge.
"""
import html
from pathlib import Path

import pymupdf

AUSGABE = Path(__file__).resolve().parent.parent / "ausgabe"
L = '<span style="color:#c00000">'
LINIE = "_" * 60
YT = "https://www.youtube.com/watch?v=q2LBfTE6LI0"       # simpleclub: Ideale Gasgleichung – Was kann die?
YT_KURZ = "https://youtu.be/q2LBfTE6LI0"
EMB = "https://www.srf.ch/play/embed?urn=urn:srf:{}&subdivisions=false"
TS_BANGKOK = EMB.format("video:d0acac4e-ccc9-43ed-9067-3a25863abba4")   # Tagesschau-Beitrag, 1:19
TS_GANZ = "https://www.srf.ch/play/tv/-/video/-?urn=urn:srf:video:e4a49c6c-49e5-45b9-8ff2-9af18c7ee473"
ECHO = EMB.format("audio:4064a09e-0000-314e-aada-4ecf1a951d7e")        # Echo: Mietpreis-Initiative, 3:40
KRIMI = EMB.format("audio:bfd079fd-5430-3334-8fb0-3c91a126fe97")       # Krimi «Treibjagd», 87 Min.
GREDIG_SEITE = "https://www.srf.ch/audio/gredig-direkt/andres-andrekson-vom-stress-stress-zu-sein?id=AUDI20260925_NR_0003"


def offen(nr, punkte, frage, loesung, zeilen=3):
    return (f"<h3>{nr} ({punkte} Punkte)</h3><p>{frage}</p><p>{'<br>'.join([LINIE] * zeilen)}</p>"
            f"<p>{L}Musterlösung: {loesung}</span></p>")


def a(url, text):
    return f'<a href="{html.escape(url)}">{text}</a>'


PDFS = {
    "Medien_1_YouTube": ("Medientest 1 – YouTube-Ausschnitte", f"""
<h2>Teil A – Video «Ideale Gasgleichung»</h2>
<h3>A1 (1 Punkt)</h3>
<p>Schauen Sie den Ausschnitt: {YT} (0:30–1:30)</p>
<p>Wie nennt das Video ein Gas, dessen Teilchen nur elastisch zusammenstossen?</p>
<p>{L}☒ ideales Gas</span><br>☐ reales Gas<br>☐ Edelgas</p>
<h3>A2 (2 Punkte)</h3>
<p>Schauen Sie {a(YT_KURZ, "diesen Ausschnitt")} von 1:00 bis 2:00.</p>
<p>Welche Grössen kommen in der idealen Gasgleichung vor? Nennen Sie zwei.</p>
<p>{LINIE}<br>{LINIE}</p><p>{L}Musterlösung: zwei von Druck, Volumen, Stoffmenge, Temperatur (je 1).</span></p>
<h3>A3 (2 Punkte)</h3>
<p>Das ganze Video: {YT}</p>
<p>Fassen Sie in zwei Sätzen zusammen, wofür man die ideale Gasgleichung braucht.</p>
<p>{LINIE}<br>{LINIE}</p><p>{L}Musterlösung: Zusammenhang der Zustandsgrössen (1), ein Beispiel aus dem Video (1).</span></p>
"""),
    "Medien_2_SRF_Video": ("Medientest 2 – SRF-Video", f"""
<h2>Teil A – Tagesschau vom 26.09.2026</h2>
<p>Schauen Sie den Beitrag: {TS_BANGKOK}</p>
<p>Alle Fragen in Teil A beziehen sich auf diesen Beitrag.</p>
<h3>A1 (1 Punkt)</h3>
<p>Welche Stadt ruft laut Beitrag den Katastrophenfall aus?</p>
<p>{L}☒ Bangkok</span><br>☐ Manila<br>☐ Jakarta</p>
<h3>A2 (1 Punkt)</h3>
<p>Weshalb wird der Katastrophenfall ausgerufen?</p>
<p>{L}☒ wegen Überschwemmungen</span><br>☐ wegen eines Erdbebens<br>☐ wegen einer Hitzewelle</p>
<h2>Teil B – Die ganze Sendung</h2>
<h3>B1 (2 Punkte)</h3>
<p>Schauen Sie die Tagesschau {a(TS_GANZ, "ab 14:17")} bis zum Ende des Beitrags über Bangkok.</p>
<p>Beschreiben Sie in zwei Sätzen, was die Bilder zeigen.</p>
<p>{LINIE}<br>{LINIE}</p><p>{L}Musterlösung: überflutete Strassen (1), Folgen für die Menschen (1) — gemäss Beitrag.</span></p>
"""),
    "Medien_3_SRF_Audio": ("Medientest 3 – SRF-Audio", f"""
<h2>Teil A – Echo der Zeit</h2>
<h3>A1 (1 Punkt)</h3>
<p>Hören Sie den Beitrag: {ECHO}</p>
<p>Was will der Bundesrat der Mietpreis-Initiative gegenüberstellen?</p>
<p>☐ nichts<br>{L}☒ einen indirekten Gegenvorschlag</span><br>☐ einen direkten Gegenentwurf</p>
<h2>Teil B – Hörspiel</h2>
<h3>B1 (2 Punkte)</h3>
<p>Hören Sie den Krimi «Treibjagd» {a(KRIMI, "ab 0:30")} etwa fünf Minuten lang.</p>
<p>Wo beginnt die Geschichte, und welche Figur lernen Sie zuerst kennen?</p>
<p>{LINIE}<br>{LINIE}</p><p>{L}Musterlösung: Ort (1), erste Figur (1) — gemäss Hörspiel.</span></p>
<h2>Teil C – Gespräch</h2>
<h3>C1 (2 Punkte)</h3>
<p>Hören Sie das Gespräch: {GREDIG_SEITE}</p>
<p>Worüber spricht Andres Andrekson? Nennen Sie das Thema und eine Aussage.</p>
<p>{LINIE}<br>{LINIE}</p><p>{L}Musterlösung: Stress (1), eine Aussage aus dem Gespräch (1).</span></p>
"""),
    "Medien_4_Gemischt": ("Lernkontrolle Medien – gemischt", f"""
<h2>Teil 1 – Nachrichten</h2>
<p>Schauen Sie zuerst den Beitrag. Er gilt für alle Aufgaben in Teil 1.</p>
<p>{a(TS_BANGKOK, "Tagesschau-Beitrag: Bangkok ruft Katastrophenfall aus")}</p>
<h3>1.1 (1 Punkt)</h3>
<p>Was ist der Anlass des Beitrags?</p>
<p>{L}☒ Überschwemmungen</span><br>☐ Wahlen<br>☐ ein Streik</p>
<h3>1.2 (2 Punkte)</h3>
<p>Nennen Sie zwei Folgen für die Bevölkerung, die im Beitrag vorkommen.</p>
<p>{LINIE}<br>{LINIE}</p><p>{L}Musterlösung: zwei Folgen gemäss Beitrag (je 1).</span></p>
<h2>Teil 2 – Chemie</h2>
<h3>2.1 (2 Punkte)</h3>
<p>Schauen Sie diesen Ausschnitt (2:00–3:00): {YT}</p>
<p>Erklären Sie mit eigenen Worten, was «ideal» bei einem Gas bedeutet.</p>
<p>{LINIE}<br>{LINIE}</p><p>{L}Musterlösung: nur elastische Stösse (1), keine weiteren Wechselwirkungen (1).</span></p>
<h2>Teil 3 – Politik</h2>
<h3>3.1 (1 Punkt)</h3>
<p>Hören Sie den Beitrag (Einbettungscode von SRF):</p>
<p style="font-family:monospace;font-size:8pt">{html.escape(f'<iframe width="560" height="315" src="{ECHO}" allowfullscreen></iframe>')}</p>
<p>Um welche Initiative geht es?</p>
<p>{L}☒ Mietpreis-Initiative</span><br>☐ Klimafonds-Initiative<br>☐ Erbschaftssteuer-Initiative</p>
"""),
}


def main() -> list[Path]:
    AUSGABE.mkdir(exist_ok=True)
    fertig = []
    for name, (titel, inhalt) in PDFS.items():
        ziel = AUSGABE / f"{name}.pdf"
        story = pymupdf.Story(f"<h1>{titel} – mit Lösungen</h1>{inhalt}",
                              user_css="body{font-family:sans-serif;font-size:10pt} h3{font-size:11pt}")
        writer = pymupdf.DocumentWriter(str(ziel))
        weiter = True
        while weiter:
            geraet = writer.begin_page(pymupdf.paper_rect("a4"))
            weiter, _ = story.place(pymupdf.paper_rect("a4") + (50, 50, -50, -50))
            story.draw(geraet)
            writer.end_page()
        writer.close()
        # DocumentWriter schreibt <a href> nicht als Link — auf den Ankertext legen, wie Word es exportiert
        doc = pymupdf.open(ziel)
        for url, anker in ((u, t) for u, t in __import__("re").findall(r'<a href="([^"]+)">([^<]+)</a>', inhalt)):
            for seite in doc:
                for rect in seite.search_for(anker):
                    seite.insert_link({"kind": pymupdf.LINK_URI, "from": rect, "uri": html.unescape(url)})
        doc.saveIncr()
        fertig.append(ziel)
    return fertig


if __name__ == "__main__":
    for p in main():
        print(p)
