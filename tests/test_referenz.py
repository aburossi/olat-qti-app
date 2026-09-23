"""Baut beispiele/allefragen.yaml und vergleicht jede Frage mit dem OpenOlat-Export.

Verglichen wird nach Normalisierung: Identifikatoren werden in der Reihenfolge
ihres Auftretens durchnummeriert, Werte in ungeordneten Lösungsmengen sortiert.
Alles andere — Elemente, Attribute, Texte, Bewertungslogik — muss gleich sein.

    python tests/test_referenz.py
"""
import re
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


LEER = re.compile(r"\s+")
BLOCK = {NS + t for t in ("p", "li", "td", "th", "h3", "h4", "div", "hottextInteraction")}


def weissraum(root) -> None:
    """Leerraum im itemBody so, wie der Browser ihn zeigt: Folgen = ein Leerzeichen, am Blockende und
    vor <br/> unsichtbar, leere Absätze weg. Der OLAT-Editor hinterlässt dort beliebige Reste."""
    body = root.find(NS + "itemBody")
    if body is None:
        return
    for el in body.iter():
        if el.text:
            el.text = LEER.sub(" ", el.text)
        if el.tail:
            el.tail = LEER.sub(" ", el.tail)
    for el in list(body.iter()):
        if el.tag == NS + "br":
            vor = el.getprevious()
            if vor is not None:
                vor.tail = (vor.tail or "").rstrip() or None
            else:
                el.getparent().text = (el.getparent().text or "").rstrip() or None
        if el.tag in BLOCK:
            if len(el):
                el[-1].tail = (el[-1].tail or "").rstrip() or None
            else:
                el.text = (el.text or "").rstrip() or None
    for el in list(body.iter(NS + "p")):
        if not len(el) and not el.text:
            el.getparent().remove(el)
    for el in body.iter(NS + "textEntryInteraction"):
        if el.get("placeholderText") == "":  # mal geschrieben, mal nicht — gleichbedeutend
            del el.attrib["placeholderText"]
    for ia in body.iter(NS + "inlineChoiceInteraction"):
        if ia.get("shuffle") == "true":  # gemischt: die Reihenfolge der Optionen zählt nicht
            ia[:] = sorted(ia, key=lambda e: e.text or "")


def luecken_ordnen(root) -> None:
    """Antwort-Kennungen nach Reihenfolge im itemBody umbenennen (OpenOlat nennt eine neu eingefügte
    Lücke mal RESPONSE_2, mal inline…) und die Deklarationen und Teilbewertungen je Lücke danach
    sortieren — OpenOlat schreibt sie in Bearbeitungsreihenfolge."""
    body = root.find(NS + "itemBody")
    name = {}
    for el in body.iter():
        if el.get("responseIdentifier"):
            name.setdefault(el.get("responseIdentifier"), f"R{len(name) + 1:03d}")

    def neu(s):
        if s in name:
            return name[s]
        for k in ("SCORE_", "MINSCORE_"):
            if s.startswith(k) and s[len(k):] in name:
                return k + name[s[len(k):]]
        return s
    for el in root.iter():
        for a in ("identifier", "responseIdentifier"):
            if el.get(a):
                el.set(a, neu(el.get(a)))

    def schluessel(el):
        ident = el.get("identifier") or ""
        if el.tag == NS + "responseDeclaration":
            return ident
        if el.tag == NS + "responseCondition":
            ziel = el.find(f"{NS}responseIf/{NS}setOutcomeValue")
            ident = ziel.get("identifier") if ziel is not None else ""
        if el.tag in (NS + "outcomeDeclaration", NS + "variable", NS + "setOutcomeValue", NS + "responseCondition"):
            for k in ("SCORE_", "MINSCORE_"):
                if ident.startswith(k):
                    return ident[len(k):]
        return None
    for eltern in list(root.iter()):
        kinder, lauf = list(eltern), []
        neu_ = list(kinder)
        for i in range(len(kinder) + 1):
            if i < len(kinder) and schluessel(kinder[i]) is not None:
                lauf.append(i)
                continue
            if len(lauf) > 1:
                sortiert = sorted((kinder[j] for j in lauf), key=schluessel)  # stabil: SCORE_ vor MINSCORE_
                for j, k in zip(lauf, sortiert):
                    neu_[j] = k
            lauf = []
        if neu_ != kinder:
            eltern[:] = neu_


def normalisiert(daten: bytes) -> str:
    root = etree.fromstring(daten)
    for a in ("identifier", "toolName", "toolVersion"):
        root.attrib.pop(a, None)
    weissraum(root)
    luecken_ordnen(root)
    for i, v in enumerate(v for v in root.iter(NS + "value") if v.get("id")):
        v.set("id", f"G{i}")  # globale Dropdown-Optionen (templateDeclaration)
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
PAARE = [("allefragen.yaml", "allefragen"), ("hinweis.yaml", "hinweis"), ("loesung.yaml", "loesung"), ("latex.yaml", "latex"),
         ("punkte_pro_antwort.yaml", "punkte_pro_antwort")]


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
