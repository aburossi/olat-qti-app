"""Medien eingebettet (27.09.2026): SRF-Player, YouTube-Player mit Ausschnitt, OLAT-Player mit Startzeit,
SRF-Links in der App (offline) und Zeitbereiche vom Modell. Nichts wird heruntergeladen.

Was in OLAT geprüft ist, steht bei olatqti.medium(). Ohne Argument ohne Netz; mit --live fragt srf-einbetten
echte SRF-Seiten ab (nur die Seiten und SRG-Metadaten, keine Mediendatei):

    app/.venv/Scripts/python tests/test_srf.py
    app/.venv/Scripts/python tests/test_srf.py --live
"""
import json
import sys
from pathlib import Path
from urllib.error import HTTPError

import yaml

WURZEL = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(WURZEL / "app"), str(WURZEL)]
import olatqti  # noqa: E402
import umwandeln  # noqa: E402

BANGKOK = "urn:srf:video:d0acac4e-ccc9-43ed-9067-3a25863abba4"          # Tagesschau-Beitrag, 1:19
EMBED = f"https://www.srf.ch/play/embed?urn={BANGKOK}&subdivisions=false"
YT = "https://www.youtube.com/watch?v=q2LBfTE6LI0"


def objekt(m) -> dict:
    return olatqti.medium(m, olatqti.Ids("t")).find(olatqti.q("object")).attrib


def fehler_bei(m) -> str:
    try:
        olatqti.medium(m, olatqti.Ids("t"))
    except olatqti.FehlerImFragensatz as e:
        return str(e)
    return ""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    fehler = []

    # SRF-Player: URN, Play-Link und Einbettungslink ergeben denselben Player; auch als url: erkannt
    for m in ({"srf": BANGKOK}, {"srf": f"https://www.srf.ch/play/tv/-/video/-?urn={BANGKOK}"}, {"srf": EMBED},
              EMBED, {"url": EMBED}):
        o = objekt(m)
        if (o.get("data"), o.get("type"), o.get("height")) != (EMBED, "text/html", "360"):
            fehler.append(f"SRF-Player {m}: {o}")
    if objekt({"srf": "urn:rts:audio:123", "start": "1:30"})["data"] != \
            "https://www.rts.ch/play/embed?urn=urn:rts:audio:123&subdivisions=false&startTime=90":
        fehler.append("SRF-Player: RTS oder start falsch")

    # YouTube mit Ausschnitt → YouTube-Player (nocookie); ohne Zeiten wie bisher im OLAT-Player
    o = objekt({"url": YT, "start": "0:30", "ende": "1:30"})
    if o.get("data") != "https://www.youtube-nocookie.com/embed/q2LBfTE6LI0?start=30&end=90" or o.get("type") != "text/html":
        fehler.append(f"YouTube-Ausschnitt: {o}")
    for kurz in ("https://youtu.be/q2LBfTE6LI0", "https://www.youtube.com/embed/q2LBfTE6LI0",
                 "https://www.youtube.com/watch?feature=share&v=q2LBfTE6LI0"):
        if "q2LBfTE6LI0?start=10&end=20" not in objekt({"url": kurz, "start": 10, "ende": 20})["data"]:
            fehler.append(f"YouTube-ID nicht erkannt: {kurz}")
    o = objekt(YT)
    if o.get("class") != "olatFlashMovieViewer" or ",'',0,'video'," not in o.get("data-oo-movie", ""):
        fehler.append(f"YouTube ganz nicht im OLAT-Player: {o}")

    # OLAT-Player mit Startzeit (mp3, in OLAT geprüft); Zeitformate
    o = objekt({"url": "https://example.org/a.mp3", "start": "1:30"})
    if ",640,480,'90',0,'video'," not in o["data-oo-movie"]:
        fehler.append(f"mp3 mit start: {o['data-oo-movie']}")
    for wert, soll in ((30, 30), ("0:30", 30), ("14:17", 857), ("1:02:03", 3723)):
        if olatqti.sekunden(wert) != soll:
            fehler.append(f"sekunden({wert!r})")

    # was nicht geht, meldet der Konverter klar
    for m, stichwort in (({"url": YT, "start": 30}, "nur zusammen"), ({"url": YT, "ende": 90}, "nur zusammen"),
                         ({"url": YT, "start": 90, "ende": 30}, "nach start"),
                         ({"srf": BANGKOK, "ende": "1:00"}, "kennt der SRF-Player nicht"),
                         ({"url": "https://example.org/a.mp3", "start": 1, "ende": 5}, "nicht stoppen"),
                         ({"srf": "https://www.srf.ch/audio/x?id=AUDI1"}, "Einbettungslink"),
                         ({"url": "https://example.org/a.mp3", "start": "1,5"}, "Minuten:Sekunden")):
        if stichwort not in (m_ := fehler_bei(m)):
            fehler.append(f"Meldung ohne «{stichwort}» für {m}: {m_!r}")

    # App: SRF-Links in medien → {srf: …} (offline); Audio-Seite ohne URN → Hinweis; Fragetext bleibt
    yml = (f"titel: x\nsektionen:\n  - titel: A\n    medien: ['{EMBED}']\n    fragen:\n"
           f"      - {{typ: essay, frage: 'Quelle: {EMBED}', medien: [{{url: 'https://www.srf.ch/play/tv/-/video/-?urn={BANGKOK}', start: '0:10'}}]}}\n"
           f"      - {{typ: essay, frage: B, medien: ['https://www.srf.ch/audio/x/y?id=AUDI20260925_NR_0003', '{YT}']}}\n")
    neu, eingebettet, hinweise = umwandeln.srg_einbetten(yml)
    s = yaml.safe_load(neu)["sektionen"][0]
    if s["medien"] != [{"srf": EMBED}] or s["fragen"][0]["medien"][0].get("start") != "0:10" \
            or "srf" not in s["fragen"][0]["medien"][0] or len(eingebettet) != 2 \
            or hinweise != ["https://www.srf.ch/audio/x/y?id=AUDI20260925_NR_0003"] \
            or s["fragen"][1]["medien"][1] != YT or s["fragen"][0]["frage"] != f"Quelle: {EMBED}":
        fehler.append(f"srg_einbetten: {s}, {eingebettet}, {hinweise}")
    ohne = "# Kommentar\ntitel: x\nfragen:\n  - {typ: essay, frage: A, medien: ['https://youtu.be/x']}\n"
    if umwandeln.srg_einbetten(ohne) != (ohne, [], []):
        fehler.append("YAML ohne SRF-Link verändert")
    with_zip = WURZEL / "ausgabe" / "_test_srf.yaml"
    with_zip.parent.mkdir(exist_ok=True)
    with_zip.write_text(neu.replace("frage: B, medien: ['https://www.srf.ch/audio/x/y?id=AUDI20260925_NR_0003', ",
                                    "frage: B, medien: ["), encoding="utf-8")
    try:
        olatqti.baue_paket(with_zip, with_zip.with_suffix(".zip"))
        if (p := olatqti.pruefe_paket(with_zip.with_suffix(".zip"))):
            fehler.append(f"Paketprüfung: {p}")
    except olatqti.FehlerImFragensatz as e:
        fehler.append(f"Bauen mit SRF-Player: {e}")
    finally:
        with_zip.unlink(missing_ok=True)
        with_zip.with_suffix(".zip").unlink(missing_ok=True)

    # Modell: Medien mit Zeitbereich → YAML
    if umwandeln._medien([{"url": YT, "start": "0:30", "ende": "1:30"}, {"url": EMBED, "start": None, "ende": None},
                          "https://x/a.mp3"]) != [{"url": YT, "start": "0:30", "ende": "1:30"}, EMBED, "https://x/a.mp3"]:
        fehler.append("_medien: Umwandlung vom Modell falsch")
    if umwandeln.medien_url({"srf": EMBED}) != EMBED or umwandeln.medien_url({"url": YT, "start": 1}) != YT:
        fehler.append("medien_url")

    # srf-einbetten (Kommandozeile): Audio-Seite → URN aus der Seite, Sendungsseite → Beitrag mit gleichem Titel
    ganz, beitrag = "urn:srf:audio:aaaa", "urn:srf:audio:bbbb"
    il = json.dumps({"chapterList": [{"urn": ganz, "title": "Mietpreis", "duration": 2466000},
                                     {"urn": beitrag, "title": "Mietpreis", "duration": 222000}]}).encode()

    def holen(url, zeit=10.0):
        if "echo-der-zeit" in url:
            return f'… "{ganz}" …'.encode()
        if "aaaa" in url:
            return il
        if "krimi" in url:
            return b'data-urn="urn:srf:eawEpisode:AUDI20260926_NR_0001"'
        raise HTTPError(url, 404, "Not Found", {}, None)
    if olatqti.srg_einbettungslink("https://www.srf.ch/audio/echo-der-zeit/x?id=AUDI1", holen) != \
            "https://www.srf.ch/play/embed?urn=urn:srf:audio:bbbb&subdivisions=false":
        fehler.append("srf-einbetten: Sendungsseite nicht auf den Beitrag")
    if olatqti.srg_einbettungslink(EMBED, holen) != EMBED:
        fehler.append("srf-einbetten: Link mit URN")
    for link, stichwort in (("https://www.srf.ch/audio/krimi/x?id=AUDI2", "(noch) kein"),
                            ("https://www.srf.ch/audio/fehlt/x?id=AUDI3", "nicht erreichbar")):
        try:
            olatqti.srg_einbettungslink(link, holen)
            fehler.append(f"srf-einbetten ohne Fehler: {link}")
        except olatqti.SrgFehler as e:
            if stichwort not in str(e):
                fehler.append(f"srf-einbetten Meldung: {e}")

    if "--live" in sys.argv:
        for link, soll in (("https://www.srf.ch/audio/echo-der-zeit/mietpreis-initiative-bundesrat-will-indirekten-"
                            "gegenvorschlag?id=AUDI20260925_RS_0056", "4064a09e-0000-314e-aada-4ecf1a951d7e"),
                           ("https://www.srf.ch/audio/krimi/treibjagd-von-cynthia-pughe-co?id=AUDI20260910_NR_0020",
                            "bfd079fd-5430-3334-8fb0-3c91a126fe97")):
            try:
                ergebnis = olatqti.srg_einbettungslink(link)
                print(f"  live: {ergebnis}")
                if soll not in ergebnis:
                    fehler.append(f"live {link}: {ergebnis}")
            except olatqti.SrgFehler as e:
                fehler.append(f"live {link}: {e}")

    for f in fehler:
        print("FEHLER", f)
    print(f"Medien-Einbettung{' (live)' if '--live' in sys.argv else ''}: {len(fehler)} Fehler")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
