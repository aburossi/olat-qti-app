"""Test-PDF: SRF-Audio-Links, die die App in abspielbare mp3 umwandelt (27.09.2026).

    app/.venv/Scripts/python beispiele/pdf_srf.py   -> ausgabe/SRF_Links_mit_Loesungen.pdf

Teil A: Link hinter einem Wort, in der Einleitung des Teils (Echo der Zeit, Sendungsseite → erwartet: der Beitrag, 3.7 Min.).
Teil B: Link sichtbar ausgeschrieben (bricht um), bei einer einzelnen Frage (Echo der Zeit → Beitrag, 5.2 Min.).
Teil C: Link hinter einem Wort, auf eine Krimi-Folge, die am 27.09.2026 noch nicht online war → erwartet: Warnung, Link bleibt.
Die Fragen stützen sich nur auf die Titel der Beiträge — der Inhalt der Audios ist hier nicht geprüft.
"""
from pathlib import Path

import pymupdf

HIER = Path(__file__).resolve().parent
L = '<span style="color:#c00000">'
LINIE = "_" * 60
ECHO_MIETE = "https://www.srf.ch/audio/echo-der-zeit/mietpreis-initiative-bundesrat-will-indirekten-gegenvorschlag?id=AUDI20260925_RS_0056"
ECHO_LINKE = "https://www.srf.ch/audio/echo-der-zeit/die-linke-in-berlin-im-kreuzfeuer-der-antisemitisch-kritik?id=AUDI20260926_RS_0052#autoplay"
KRIMI = "https://www.srf.ch/audio/krimi/verzell-du-das-em-faehrimaa-5-spuk-im-studio-gespraech?id=AUDI20260926_NR_0001"

HTML = f"""
<h1>Hörverständnis SRF – mit Lösungen</h1>
<p>Test für die Umwandlung von SRF-Links in abspielbare Audios (OLAT-Test-App).</p>

<h2>Teil A – Mietpreis-Initiative</h2>
<p>Hören Sie den Beitrag aus «Echo der Zeit». Alle Fragen in Teil A beziehen sich darauf.</p>
<p>Audio: <a href="{ECHO_MIETE}">Beitrag «Mietpreis-Initiative» hören</a></p>

<h3>A1 (1 Punkt)</h3>
<p>Was will der Bundesrat laut Beitrag der Mietpreis-Initiative gegenüberstellen?</p>
<p>☐ Nichts, er empfiehlt die Initiative zur Annahme<br>{L}☒ Einen indirekten Gegenvorschlag</span><br>
☐ Einen direkten Gegenentwurf in der Verfassung</p>

<h3>A2 (3 Punkte)</h3>
<p>Fassen Sie in zwei bis drei Sätzen zusammen, worum es im Beitrag geht.</p>
<p>{LINIE}<br>{LINIE}<br>{LINIE}</p>
<p>{L}Musterlösung: Thema Mietpreis-Initiative (1), Haltung des Bundesrats: indirekter Gegenvorschlag (1),
ein Argument oder eine Reaktion aus dem Beitrag (1).</span></p>

<h2>Teil B – Politik in Deutschland</h2>

<h3>B1 (2 Punkte)</h3>
<p>Hören Sie den Beitrag: {ECHO_LINKE}</p>
<p>Weshalb steht die Partei «Die Linke» in Berlin laut Beitrag in der Kritik?</p>
<p>{LINIE}<br>{LINIE}</p>
<p>{L}Musterlösung: wegen Antisemitismus-Vorwürfen (1) — mit einem Beispiel oder einer Stimme aus dem Beitrag (1).</span></p>

<h2>Teil C – Hörspiel</h2>

<h3>C1 (2 Punkte)</h3>
<p>Hören Sie die <a href="{KRIMI}">Krimi-Folge «Verzell du das em Fährimaa 5»</a>.</p>
<p>Beschreiben Sie, wo die Geschichte spielt und was dort Unheimliches geschieht.</p>
<p>{LINIE}<br>{LINIE}</p>
<p>{L}Musterlösung: Ort (1), unheimliches Ereignis («Spuk im Studio») (1).</span></p>
"""


def main() -> Path:
    ziel = HIER.parent / "ausgabe" / "SRF_Links_mit_Loesungen.pdf"
    story = pymupdf.Story(HTML, user_css="body{font-family:sans-serif;font-size:10pt} h3{font-size:11pt}")
    writer = pymupdf.DocumentWriter(str(ziel))
    weiter = True
    while weiter:
        geraet = writer.begin_page(pymupdf.paper_rect("a4"))
        weiter, _ = story.place(pymupdf.paper_rect("a4") + (50, 50, -50, -50))
        story.draw(geraet)
        writer.end_page()
    writer.close()
    # DocumentWriter schreibt <a href> nicht als Link — nachträglich auf den Ankertext legen, wie Word es exportiert
    doc = pymupdf.open(ziel)
    for anker, url in (("Beitrag «Mietpreis-Initiative» hören", ECHO_MIETE),
                       ("Krimi-Folge «Verzell du das em Fährimaa 5»", KRIMI)):
        for seite in doc:
            for rect in seite.search_for(anker):
                seite.insert_link({"kind": pymupdf.LINK_URI, "from": rect, "uri": url})
    doc.saveIncr()
    return ziel


if __name__ == "__main__":
    print(main())
