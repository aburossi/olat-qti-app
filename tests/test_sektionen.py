"""Teile, Sektionen mit Einleitung, Zeitlimit, Bestehensgrenze und Testkonfiguration.

Baut beispiele/sektionen_teile.yaml und vergleicht die Teststruktur (assessmentTest) mit dem
OpenOlat-Export referenz/sektionen_neutral/, dazu QTI21PackageConfig.xml je Konfiguration mit
referenz/sektionen_{neutral,formativ,summativ}/. Die Fragen selbst prüft test_referenz.py.

    python tests/test_sektionen.py
"""
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import yaml

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
import olatqti  # noqa: E402

q = olatqti.q
REF = WURZEL / "referenz"


def lies_paket(quelle) -> dict[str, bytes]:
    if isinstance(quelle, Path) and quelle.is_dir():
        return {p.name: p.read_bytes() for p in quelle.iterdir() if p.is_file()}
    with zipfile.ZipFile(quelle) as z:
        return {n: z.read(n) for n in z.namelist()}


def struktur(dateien: dict[str, bytes]) -> dict:
    """Was am Test zählt, ohne Kennungen: Teile → Sektionen (Titel, Fragetitel, Einleitung),
    Zeitlimit, Maximalpunkte, Bestehensgrenze, Auswertung."""
    test = next(ET.fromstring(d) for n, d in dateien.items()
                if n.endswith(".xml") and ET.fromstring(d).tag == q("assessmentTest"))
    titel_von = {n: ET.fromstring(d).get("title") for n, d in dateien.items()
                 if n.endswith(".xml") and ET.fromstring(d).tag == q("assessmentItem")}
    teile = []
    for tp in test.iter(q("testPart")):
        seks = []
        for s in tp.iter(q("assessmentSection")):
            rb = s.find(q("rubricBlock"))
            texte = ["".join(p.itertext()).strip() for p in rb.iter(q("p")) if not len(p.findall("*"))
                     or all(k.tag in (q("strong"), q("em")) for k in p)]
            seks.append({
                "titel": s.get("title"),
                "fragen": [titel_von[r.get("href")] for r in s.iter(q("assessmentItemRef"))],
                "texte": [t for t in texte if t],
                "medien": [o.get("data") for o in rb.iter(q("object"))],
                "bilder": [(i.get("src"), i.get("width"), i.get("height")) for i in rb.iter(q("img"))],
                "gemischt": (s.find(q("ordering")) is not None and s.find(q("ordering")).get("shuffle") == "true"),
            })
        isc = tp.find(q("itemSessionControl"))
        teile.append({"navigation": tp.get("navigationMode"), "abgabe": tp.get("submissionMode"),
                      "steuerung": dict(isc.attrib), "sektionen": seks})
    decl = {d.get("identifier"): "".join(d.itertext()) for d in test.iter(q("outcomeDeclaration"))}
    tl = test.find(q("timeLimits"))
    op = test.find(q("outcomeProcessing"))
    return {"teile": teile, "deklarationen": decl, "zeit": tl.get("maxTime") if tl is not None else None,
            "auswertung": ET.tostring(op, encoding="unicode")}


def vergleiche(name, ref, neu, fehler):
    if ref == neu:
        print(f"  gleich  {name}")
    else:
        fehler.append(f"{name}:\n  ref: {ref}\n  neu: {neu}")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if not (REF / "sektionen_neutral").is_dir():
        print("  übersprungen: referenz/sektionen_* liegt nicht im Repo")
        return 0
    fehler = []
    satz = yaml.safe_load((WURZEL / "beispiele" / "sektionen_teile.yaml").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ziel = tmp / "paket.zip"
        info = olatqti.baue_paket(WURZEL / "beispiele" / "sektionen_teile.yaml", ziel)
        fehler += [f"Prüfung: {b}" for b in olatqti.pruefe_paket(ziel)]
        neu, ref = struktur(lies_paket(ziel)), struktur(lies_paket(REF / "sektionen_neutral"))

        # Die Einleitung im Export hat zusätzliche Beschriftungen («Video», «Bild») zwischen den Medien —
        # die YAML-Einleitung ist Text, dann Medien, dann Bilder. Verlangt: alle YAML-Absätze stehen im Export.
        for tr, tn in zip(ref["teile"], neu["teile"]):
            for sr, sn in zip(tr["sektionen"], tn["sektionen"]):
                fehlend = [t for t in sn["texte"] if t not in sr["texte"]]
                if fehlend:
                    fehler.append(f"Sektion {sn['titel']}: Einleitung nicht im Export: {fehlend}")
                sr["texte"] = sn["texte"] = None
        vergleiche("Teile und Sektionen", ref["teile"], neu["teile"], fehler)
        vergleiche("Deklarationen (MAXSCORE, PASS)", ref["deklarationen"], neu["deklarationen"], fehler)
        vergleiche("Zeitlimit", ref["zeit"], neu["zeit"], fehler)
        vergleiche("Auswertung mit Bestehensgrenze", ref["auswertung"], neu["auswertung"], fehler)
        vergleiche("Zusammenfassung", (2, 3), (info["teile"], info["sektionen"]), fehler)
        mit_bild = lies_paket(ziel)
        if "zeichnen_bg.png" not in mit_bild:
            fehler.append("Bild der Sektionseinleitung fehlt im Paket")

        # Konfigurationen: mit Bestehensgrenze byte-gleich zum Export
        for k in olatqti.KONFIGURATIONEN:
            (tmp / f"{k}.yaml").write_text(yaml.safe_dump(dict(satz, konfig=k)), encoding="utf-8")
            # Bildpfade sind relativ zur YAML-Datei — die Kopie liegt woanders, also absolut machen
            s = yaml.safe_load((tmp / f"{k}.yaml").read_text(encoding="utf-8"))
            s["teile"][0]["sektionen"][0]["bilder"] = [str(REF / "allefragen" / "zeichnen_bg.png")]
            for f in s["teile"][0]["sektionen"][0]["fragen"]:
                if f.get("bild"):
                    f["bild"] = str((WURZEL / "beispiele" / f["bild"]).resolve())
            (tmp / f"{k}.yaml").write_text(yaml.safe_dump(s, allow_unicode=True), encoding="utf-8")
            olatqti.baue_paket(tmp / f"{k}.yaml", tmp / f"{k}.zip")
            vergleiche(f"Konfiguration {k}", (REF / f"sektionen_{k}" / "QTI21PackageConfig.xml").read_bytes(),
                       lies_paket(tmp / f"{k}.zip")["QTI21PackageConfig.xml"], fehler)

        # ohne Teile, Zeitlimit, Bestehensgrenze: ein Teil, kein PASS, kein timeLimits, kein passedType
        (tmp / "einfach.yaml").write_text("titel: X\nfragen:\n  - {typ: essay, frage: Warum}\n", encoding="utf-8")
        olatqti.baue_paket(tmp / "einfach.yaml", tmp / "einfach.zip")
        e = lies_paket(tmp / "einfach.zip")
        s = struktur(e)
        vergleiche("Standard: ein Teil, keine Grenze, kein Zeitlimit", (1, False, None),
                   (len(s["teile"]), "PASS" in s["deklarationen"], s["zeit"]), fehler)
        if b"passedType" in e["QTI21PackageConfig.xml"] or b"<enableSuspend>true" not in e["QTI21PackageConfig.xml"]:
            fehler.append("Standard-Konfiguration ist nicht «neutral» ohne passedType")

        for yml, erwartet in (("titel: X\nkonfig: streng\nfragen: [{typ: essay, frage: A}]\n", "konfig"),
                              ("titel: X\nbestehen: 5\nfragen: [{typ: essay, frage: A}]\n", "bestehen"),
                              ("titel: X\nteile: [{titel: leer}]\n", "Teil 1"),
                              ("titel: X\nzeitlimit: 0\nfragen: [{typ: essay, frage: A}]\n", "zeitlimit"),
                              ("titel: X\nzeitlimit: 30 min\nfragen: [{typ: essay, frage: A}]\n", "keine Zahl"),
                              ("titel: X\nbestehen: -1\nfragen: [{typ: essay, frage: A}]\n", "bestehen")):
            (tmp / "falsch.yaml").write_text(yml, encoding="utf-8")
            try:
                olatqti.baue_paket(tmp / "falsch.yaml", tmp / "falsch.zip")
                fehler.append(f"kein Fehler bei: {yml.splitlines()[1]}")
            except olatqti.FehlerImFragensatz as ex:
                if erwartet not in str(ex):
                    fehler.append(f"falsche Meldung: {ex}")
                else:
                    print(f"  abgelehnt  {ex}")
    for f in fehler:
        print("FEHLER", f)
    print("ok" if not fehler else f"{len(fehler)} Fehler")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
