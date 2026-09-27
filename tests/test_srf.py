"""SRF/SRG-Audio → mp3 (olatqti.srg_mp3, umwandeln.srg_links_aufloesen), 27.09.2026.

Ohne Argument mit nachgebauten Antworten (kein Netz). Mit --live gegen SRF, am Beitrag, an dem es entwickelt wurde:

    app/.venv/Scripts/python tests/test_srf.py
    app/.venv/Scripts/python tests/test_srf.py --live
"""
import json
import sys
from pathlib import Path
from urllib.error import HTTPError

WURZEL = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(WURZEL / "app"), str(WURZEL)]
import olatqti  # noqa: E402
import umwandeln  # noqa: E402

GREDIG = "https://www.srf.ch/audio/gredig-direkt/andres-andrekson-vom-stress-stress-zu-sein?id=AUDI20260925_NR_0003"
URN = "urn:srf:audio:76c78916-8854-3579-93ab-c8ffdf9f0679"
MP3 = ("https://download-media.srf.ch/world/audio/Gredig_direkt_radio/2026/09/"
       "Gredig_direkt_radio_AUDI20260925_NR_0003_17865f51254f45939dd9a71f3c7a9f4f.mp3")
ANDERE = "urn:srf:audio:11111111-2222-3333-4444-555555555555"


def il(urn: str, url: str, titel: str = "Beitrag", sperre=None) -> bytes:
    return json.dumps({"chapterList": [{"urn": urn, "title": titel, "duration": 2010000, "blockReason": sperre,
                                        "resourceList": [{"protocol": "HLS", "encoding": "AAC", "url": "x.m3u8"},
                                                         {"protocol": "HTTPS", "encoding": "MP3", "url": url}]}]}).encode()


def netz(antworten: dict):
    aufrufe = []

    def holen(url, zeit=10.0):
        aufrufe.append(url)
        for teil, daten in antworten.items():
            if teil in url:
                return daten
        raise HTTPError(url, 404, "Not Found", {}, None)
    return holen, aufrufe


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    fehler = []
    live = "--live" in sys.argv

    if live:
        for link in (GREDIG, URN, f"https://www.srf.ch/play/radio/redirect/detail/x?urn={URN}"):
            try:
                fund = olatqti.srg_mp3(link)
                print(f"  live: {fund['titel']!r}, {fund['minuten']} Min. ← {link[:60]}")
                if fund["url"] != MP3:
                    fehler.append(f"live {link}: {fund['url']}")
            except olatqti.SrgFehler as e:
                fehler.append(f"live {link}: {e}")
        # Sendungsseite «Echo der Zeit» vom 25.09.2026: der Beitrag (3.7 Min.), nicht die ganze Sendung (41.1 Min.)
        echo = "https://www.srf.ch/audio/echo-der-zeit/mietpreis-initiative-bundesrat-will-indirekten-gegenvorschlag?id=AUDI20260925_RS_0056"
        try:
            fund = olatqti.srg_mp3(echo)
            print(f"  live: {olatqti.srg_beschreibung(fund)}")
            if fund.get("sendung") != "Echo der Zeit" or fund["minuten"] > 10:
                fehler.append(f"live Echo: {fund}")
        except olatqti.SrgFehler as e:
            fehler.append(f"live Echo: {e}")
        from urllib.request import Request, urlopen
        with urlopen(Request(MP3, method="HEAD"), timeout=10) as r:
            if r.headers.get("Content-Type") != "audio/mpeg":
                fehler.append(f"live: mp3 hat Typ {r.headers.get('Content-Type')}")
    else:
        # Audio-Seite mit ?id=: URN aus dem HTML; zwei URNs auf der Seite → die mit der ID im Dateinamen
        seite = f'<html>… "{ANDERE}" … "{URN}" … "{URN}" …</html>'.encode()
        holen, aufrufe = netz({"gredig-direkt": seite, URN: il(URN, MP3, "Andrekson"),
                               ANDERE: il(ANDERE, "https://download-media.srf.ch/x/Andere_AUDI20260101_NR_0001.mp3")})
        fund = olatqti.srg_mp3(GREDIG, holen=holen)
        if fund["url"] != MP3 or fund["titel"] != "Andrekson" or fund["minuten"] != 33.5:
            fehler.append(f"Seite mit id: {fund}")
        # URN direkt und Play-Link mit ?urn=: keine Seite laden
        holen, aufrufe = netz({URN: il(URN, MP3)})
        for link in (URN, f"https://www.srf.ch/play/radio/redirect/detail/x?urn={URN}"):
            if olatqti.srg_mp3(link, holen=holen)["url"] != MP3:
                fehler.append(f"URN/Play-Link: {link}")
        if any("srf.ch/play" in a for a in aufrufe):
            fehler.append("Play-Link: Seite geladen, obwohl die URN im Link steht")
        # Fehlerfälle: 404, keine URN, keine mp3, gesperrt
        for antworten, link, stichwort in (
                ({}, GREDIG, "fehlgeschlagen"),
                ({"gredig-direkt": b"<html>nichts</html>"}, GREDIG, "keine Audio-URN"),
                ({URN: json.dumps({"chapterList": [{"urn": URN, "resourceList": []}]}).encode()}, URN, "keine mp3"),
                ({URN: il(URN, MP3, sperre="GEOBLOCK")}, URN, "gesperrt")):
            try:
                olatqti.srg_mp3(link, holen=netz(antworten)[0])
                fehler.append(f"kein Fehler bei: {stichwort}")
            except olatqti.SrgFehler as e:
                if stichwort not in str(e):
                    fehler.append(f"Meldung ohne «{stichwort}»: {e}")
        # Sendungsseite (Echo der Zeit): Kapitel der ganzen Sendung + Beitrag mit demselben Titel → der Beitrag
        ganz, beitrag, anderer = "urn:srf:audio:aaaa", "urn:srf:audio:bbbb", "urn:srf:audio:cccc"
        echo = json.dumps({"show": {"title": "Echo der Zeit"}, "chapterList": [
            {"urn": ganz, "title": "Mietpreis", "duration": 2466000,
             "resourceList": [{"protocol": "HTTPS", "encoding": "MP3", "url": "https://x/Echo_RS_0056_ganz.mp3"}]},
            {"urn": beitrag, "title": "Mietpreis", "duration": 222000,
             "resourceList": [{"protocol": "HTTPS", "encoding": "MP3", "url": "https://x/Echo_RS_0056_beitrag.mp3"}]},
            {"urn": anderer, "title": "Äthiopien", "duration": 402000,
             "resourceList": [{"protocol": "HTTPS", "encoding": "MP3", "url": "https://x/Echo_RS_0056_andere.mp3"}]}]}).encode()
        holen = netz({"echo-der-zeit": f'"{ganz}"'.encode(), "urn:srf:audio:aaaa": echo})[0]
        fund = olatqti.srg_mp3("https://www.srf.ch/audio/echo-der-zeit/mietpreis?id=AUDI20260925_RS_0056", holen=holen)
        if fund["url"] != "https://x/Echo_RS_0056_beitrag.mp3" or fund["sendung"] != "Echo der Zeit" \
                or "ganze Sendung 41.1 Min." not in olatqti.srg_beschreibung(fund):
            fehler.append(f"Sendungsseite: {fund}")
        # partId: genau dieser Beitrag
        fund = olatqti.srg_mp3("https://www.srf.ch/audio/echo-der-zeit/x?id=AUDI20260925_RS_0056&partId=cccc",
                               holen=holen)
        if fund["url"] != "https://x/Echo_RS_0056_andere.mp3":
            fehler.append(f"partId: {fund}")
        # Seite ohne Audio (Folge nur angekündigt, 27.09.2026: Krimi «Fährimaa 5»)
        try:
            olatqti.srg_mp3("https://www.srf.ch/audio/krimi/x?id=AUDI20260926_NR_0001",
                            holen=netz({"krimi": b'data-urn="urn:srf:eawEpisode:AUDI20260926_NR_0001"'})[0])
            fehler.append("Seite ohne Audio: kein Fehler")
        except olatqti.SrgFehler as e:
            if "noch" not in str(e):
                fehler.append(f"Seite ohne Audio: {e}")
        # Erkennen: Seiten ja, mp3 und fremde Links nein
        for url, soll in ((GREDIG, True), (f"https://www.srf.ch/play/tv/x?urn={URN}", True), (MP3, False),
                          ("https://www.youtube.com/watch?v=q2LBfTE6LI0", False), ("https://www.srf.ch/news/x", False)):
            if olatqti.ist_srg_seite(url) != soll:
                fehler.append(f"ist_srg_seite({url}) != {soll}")

    # Im YAML: nur medien (Sektion und Frage) ersetzen, Links im Fragetext bleiben; Fehler lassen den Link stehen
    yml = (f"titel: x\nsektionen:\n  - titel: A\n    medien: ['{GREDIG}']\n    fragen:\n"
           f"      - {{typ: essay, frage: 'Quelle: {GREDIG}', medien: [{{url: '{GREDIG}', breite: 400}}]}}\n"
           f"      - {{typ: essay, frage: B, medien: ['https://www.srf.ch/audio/x/kaputt?id=AUDI1']}}\n")

    def aufloesen(link):
        if "kaputt" in link:
            raise olatqti.SrgFehler("keine mp3")
        return {"url": MP3, "titel": "Andrekson", "minuten": 33.5, "urn": URN}
    neu, ersetzt, fehl = umwandeln.srg_links_aufloesen(yml, aufloesen)
    import yaml
    s = yaml.safe_load(neu)["sektionen"][0]
    if s["medien"] != [MP3] or s["fragen"][0]["medien"][0]["url"] != MP3 or len(ersetzt) != 1 or len(fehl) != 1 \
            or "kaputt" not in s["fragen"][1]["medien"][0]:
        fehler.append(f"srg_links_aufloesen: {s}, {ersetzt}, {fehl}")
    if s["fragen"][0]["frage"] != f"Quelle: {GREDIG}" or s["fragen"][0]["medien"][0].get("breite") != 400:
        fehler.append(f"Fragetext oder Medienangaben verändert: {s['fragen'][0]}")
    # ohne SRG-Link: Text Zeichen für Zeichen gleich (auch Kommentare)
    ohne = "# Kommentar\ntitel: x\nfragen:\n  - {typ: essay, frage: A, medien: ['https://youtu.be/x']}\n"
    if umwandeln.srg_links_aufloesen(ohne, aufloesen) != (ohne, [], []):
        fehler.append("YAML ohne SRG-Link verändert")

    for f in fehler:
        print("FEHLER", f)
    print(f"SRF-Test{' (live)' if live else ''}: {len(fehler)} Fehler")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
