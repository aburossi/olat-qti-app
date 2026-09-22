"""Baut beispiele/allefragen.yaml und vergleicht jede Frage mit dem OpenOlat-Export.

Verglichen wird nach Normalisierung: Identifikatoren werden in der Reihenfolge
ihres Auftretens durchnummeriert, Werte in ungeordneten Lösungsmengen sortiert.
Alles andere — Elemente, Attribute, Texte, Bewertungslogik — muss gleich sein.

    python tests/test_referenz.py
"""
import sys
import tempfile
import zipfile
from pathlib import Path

from lxml import etree

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
import olatqti  # noqa: E402

NS = "{http://www.imsglobal.org/xsd/imsqti_v2p1}"
AUSWAHL = {NS + t for t in olatqti.AUSWAHL}


def normalisiert(daten: bytes) -> str:
    root = etree.fromstring(daten)
    for a in ("identifier", "toolName", "toolVersion"):
        root.attrib.pop(a, None)
    nummer = {}
    for el in root.iter():
        if el.tag in AUSWAHL:
            nummer.setdefault(el.get("identifier"), f"ID{len(nummer) + 1}")

    def ersetze(s):
        return " ".join(nummer.get(t, t) for t in s.split()) if s else s
    for el in root.iter():
        if el.tag in AUSWAHL:
            el.set("identifier", nummer[el.get("identifier")])
        if el.get("mapKey"):
            el.set("mapKey", ersetze(el.get("mapKey")))
        if el.tag == NS + "value":
            el.text = ersetze(el.text)
    for mf in root.iter(NS + "modalFeedback"):
        if mf.get("identifier", "").startswith("Feedback"):  # OpenOlat vergibt die Nummer zufaellig
            mf.set("identifier", "FeedbackN")
    for rd in root.iter(NS + "responseDeclaration"):
        if rd.get("cardinality") == "ordered":
            continue
        for eltern in (rd.find(NS + "correctResponse"), rd.find(NS + "mapping")):
            if eltern is None:
                continue
            kinder = sorted(eltern, key=lambda e: e.get("mapKey") or e.text or "")
            for k in list(eltern):
                eltern.remove(k)
            eltern.extend(kinder)
    return etree.tostring(root, method="c14n").decode("utf-8")


def items_nach_titel(zip_oder_ordner) -> dict[str, bytes]:
    out = {}
    if isinstance(zip_oder_ordner, Path) and zip_oder_ordner.is_dir():
        quellen = {p.name: p.read_bytes() for p in zip_oder_ordner.glob("*.xml")}
    else:
        with zipfile.ZipFile(zip_oder_ordner) as z:
            quellen = {n: z.read(n) for n in z.namelist() if n.endswith(".xml")}
    for name, daten in quellen.items():
        root = etree.fromstring(daten)
        if root.tag == NS + "assessmentItem":
            out[root.get("title")] = daten
    return out


# (Fragensatz in beispiele/, Ordner in referenz/ mit den OpenOlat-Originalen)
PAARE = [("allefragen.yaml", "allefragen"), ("hinweis.yaml", "hinweis"), ("loesung.yaml", "loesung"), ("latex.yaml", "latex")]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    fehler, gesamt = [], 0
    for yaml_name, ordner in PAARE:
        if not (WURZEL / "referenz" / ordner).is_dir() or not (WURZEL / "beispiele" / yaml_name).is_file():
            print(f"  übersprungen: {ordner} — Referenzexport liegt nicht im Repo (Prüfungsinhalte, siehe README)")
            continue
        with tempfile.TemporaryDirectory() as tmp:
            ziel = Path(tmp) / "paket.zip"
            olatqti.baue_paket(WURZEL / "beispiele" / yaml_name, ziel)
            fehler += [f"Prüfung {yaml_name}: {b}" for b in olatqti.pruefe_paket(ziel)]
            gebaut = items_nach_titel(ziel)
        ref = items_nach_titel(WURZEL / "referenz" / ordner)
        gesamt += len(ref)
        for titel, daten in ref.items():
            if titel not in gebaut:
                fehler.append(f"fehlt: {titel}")
                continue
            a, b = normalisiert(daten), normalisiert(gebaut[titel])
            if a != b:
                i = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
                fehler.append(f"{titel}: weicht ab bei Zeichen {i}\n  ref:  …{a[max(0, i - 80):i + 80]}"
                              f"\n  neu:  …{b[max(0, i - 80):i + 80]}")
            else:
                print(f"  gleich  {titel}")
    for f in fehler:
        print("FEHLER", f)
    abweichend = len([f for f in fehler if not f.startswith("Prüfung")])
    if gesamt == 0:
        print("Keine Referenzexporte vorhanden — dieser Test läuft nur dort, wo referenz/ liegt.")
        return 0
    print(f"{gesamt - abweichend}/{gesamt} Fragen identisch")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
