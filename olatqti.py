"""olatqti — YAML-Fragensatz -> QTI-2.1-Paket für OpenOlat.

Das Ausgabeformat ist dem Export von OpenOlat 21.0.2 nachgebaut
(referenz/allefragen/). Wo OpenOlat vom QTI-Standard abweicht oder eigene
Konventionen hat, folgt dieses Skript OpenOlat, nicht dem Standard.

    python olatqti.py build fragen.yaml [-o test.zip]
    python olatqti.py check test.zip
"""
from __future__ import annotations

import argparse
import hashlib
import re
import struct
import sys
import uuid
import zipfile
import zlib
from pathlib import Path
from xml.etree import ElementTree as ET

import yaml

QTI = "http://www.imsglobal.org/xsd/imsqti_v2p1"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
SCHEMA_LOC = f"{QTI} http://www.imsglobal.org/xsd/imsqti_v2p1.xsd"
TOOL = {"toolName": "OpenOLAT", "toolVersion": "21.0.2"}

ET.register_namespace("", QTI)
ET.register_namespace("xsi", XSI)

# questionType (OpenOlat) -> interactionType (Manifest)
TYPEN = {
    "sc": "choiceInteraction",
    "mc": "choiceInteraction",
    "kprim": "matchInteraction",
    "match": "matchInteraction",
    "matchdraganddrop": "matchInteraction",
    "matchtruefalse": "matchInteraction",
    "fib": "textEntryInteraction",
    "numerical": "textEntryInteraction",
    "inlinechoice": "inlineChoiceInteraction",
    "gapmixed": "textEntryInteraction",
    "hottext": "hottextInteraction",
    "hotspot": "hotspotInteraction",
    "order": "orderInteraction",
    "essay": "extendedTextInteraction",
    "upload": "uploadInteraction",
    "drawing": "drawingInteraction",
}
# deutsche Kurznamen, damit Fragensätze lesbar bleiben
ALIASE = {
    "einfachauswahl": "sc", "mehrfachauswahl": "mc",
    "matrix": "match", "dragdrop": "matchdraganddrop", "richtigfalsch": "matchtruefalse",
    "lueckentext": "fib", "numerisch": "numerical", "dropdown": "inlinechoice",
    "gemischt": "gapmixed", "reihenfolge": "order", "freitext": "essay",
    "zeichnen": "drawing",
}
FIB_KLASSE = {"fib": "gap_text", "numerical": "gap_numerical",
              "inlinechoice": "inline_choice", "gapmixed": "gap_mixed"}


class FehlerImFragensatz(ValueError):
    pass


# --------------------------------------------------------------- Hilfen

def q(tag: str) -> str:
    return f"{{{QTI}}}{tag}"


def E(tag: str, attrs: dict | None = None, *kinder, text: str | None = None) -> ET.Element:
    el = ET.Element(q(tag), {k: str(v) for k, v in (attrs or {}).items()})
    if text is not None:
        el.text = text
    for k in kinder:
        if k is not None:
            el.append(k)
    return el


def zahl(x) -> str:
    """Gleitkomma wie Java/OpenOlat: 1.0, 0.25, -0.25."""
    return str(float(x))


class Ids:
    """Stabile Identifikatoren: gleicher Fragensatz -> gleiche Datei."""

    def __init__(self, saat: str):
        self.saat = saat
        self.n = 0

    def __call__(self, praefix: str, laenge: int = 32) -> str:
        self.n += 1
        h = hashlib.sha1(f"{self.saat}/{self.n}".encode()).hexdigest()
        return (praefix + h)[:laenge]


def absaetze(text: str | None) -> list[str]:
    if not text:
        return []
    return [" ".join(a.split()) for a in re.split(r"\n\s*\n", str(text).strip()) if a.strip()]


def js_escape(s: str) -> str:
    """Wie JavaScripts escape(): so kodiert OpenOlat die Formel im title-Attribut (referenz/latex/)."""
    return "".join(c if c.isascii() and (c.isalnum() or c in "@*_+-./")
                   else f"%{ord(c):02X}" if ord(c) < 256 else f"%u{ord(c):04X}" for c in s)


# $…$ = LaTeX-Formel, \$ = echtes Dollarzeichen; **…** = fett, *…* = kursiv, \* = echter Stern
INLINE = re.compile(r"(?<!\\)\$(?P<mathe>[^$\n]+?)(?<!\\)\$"
                    r"|\*\*(?P<fett>[^*\n]+?)\*\*"
                    r"|(?<![\w*\\])\*(?![\s*])(?P<kursiv>[^*\n]+?)(?<![\s\\])\*(?![\w*])")


def inline(el: ET.Element, text: str) -> ET.Element:
    """Füllt el mit Text, Formeln (<span class="math"> wie der OLAT-Editor), <strong> und <em>."""
    letztes, pos = None, 0

    def haenge(t: str) -> None:
        t = t.replace("\\$", "$").replace("\\*", "*")
        if letztes is None:
            el.text = (el.text or "") + t
        else:
            letztes.tail = (letztes.tail or "") + t

    for m in INLINE.finditer(text):
        haenge(text[pos:m.start()])
        if m["mathe"] is not None:
            formel = m["mathe"].strip()
            letztes = E("span", {"class": "math", "title": js_escape(formel)}, text=formel)
        elif m["fett"] is not None:
            letztes = E("strong", text=m["fett"])
        else:
            letztes = E("em", text=m["kursiv"])
        el.append(letztes)
        pos = m.end()
    haenge(text[pos:])
    if letztes is not None and not letztes.tail:
        letztes.tail = None
    return el


def p(text: str) -> ET.Element:
    return inline(E("p"), str(text))


# Zeilen in einem Absatz, Markdown-Teilmenge (Vorbild: Pietros Nachformatierung in OpenOlat, 23.09.2026)
TITEL = re.compile(r"(#{1,4})\s+(.+)")               # ### Titel -> <h3>, #### -> <h4>
LISTE = re.compile(r"(?:[-•*]|(\d{1,2})[.)])\s+(.+)")  # - Punkt -> <ul>, 1. Punkt -> <ol>
TABELLE = re.compile(r"\|.*\|")                      # | a | b | -> <table>
TRENNER = re.compile(r"\|(?::?-{3,}:?\|)+")          # |---|---| nach der Kopfzeile
NUMMERIERT = re.compile(r"\d{1,3}\s")                # Text mit Zeilennummern: Umbrüche bleiben


def _sonderzeile(z: str) -> bool:
    return bool(TITEL.fullmatch(z) or LISTE.fullmatch(z) or TABELLE.fullmatch(z))


def textabsatz(zeilen: list[str]) -> ET.Element:
    """<p>; Zeilenumbruch <br/>, wo eine Zeile mit \\ endet oder jede Zeile mit einer Nummer beginnt."""
    zeilen = [" ".join(z.split()) for z in zeilen]
    nummeriert = len(zeilen) > 1 and all(NUMMERIERT.match(z) for z in zeilen)
    el = E("p")
    for i, z in enumerate(zeilen):
        umbruch = z.endswith("\\")  # auch «\\»: Sprachmodelle verdoppeln Backslashes gern
        anhaengen(el, z.rstrip("\\").rstrip() if umbruch else z)
        if i < len(zeilen) - 1:
            if umbruch or nummeriert:
                el.append(E("br"))
            else:
                anhaengen(el, " ")
    return el


# So schreibt der OLAT-Editor eine Tabelle mit Gitter (referenz/formatierung_demo/, 23.09.2026)
RAHMEN = "border-color:rgb( 126 , 140 , 141 )"
TABELLE_STIL = f"border-collapse:collapse;width:100%;{RAHMEN};border-style:solid;margin-left:0px;margin-right:auto"


def tabelle(zeilen: list[str]) -> ET.Element:
    kopf = len(zeilen) > 1 and TRENNER.fullmatch(zeilen[1].replace(" ", ""))
    body = E("tbody")
    for n, z in enumerate(zeilen):
        if n == 1 and kopf:
            continue
        body.append(E("tr", None, *[inline(E("th" if kopf and n == 0 else "td", {"style": RAHMEN}), " ".join(c.split()))
                                    for c in z.strip()[1:-1].split("|")]))
    return E("table", {"class": "b_grid", "style": TABELLE_STIL}, body)


def bloecke(text: str | None) -> list[ET.Element]:
    """Text -> XHTML-Blöcke. Leerzeile = neuer Absatz; darin Zeile für Zeile:
    ### Titel, - Aufzählung, 1. Liste, | Tabelle |, sonst Fliesstext (Zeilen mit Leerzeichen verbunden)."""
    out = []
    if not text:
        return out
    for absatz in re.split(r"\n\s*\n", str(text).strip()):
        zeilen = [z.strip() for z in absatz.splitlines() if z.strip()]
        i = 0
        while i < len(zeilen):
            z = zeilen[i]
            if m := TITEL.fullmatch(z):
                out.append(inline(E("h4" if len(m[1]) == 4 else "h3"), m[2]))
                i += 1
            elif TABELLE.fullmatch(z):
                j = i
                while j < len(zeilen) and TABELLE.fullmatch(zeilen[j]):
                    j += 1
                out.append(tabelle(zeilen[i:j]))
                i = j
            elif m := LISTE.fullmatch(z):
                geordnet = m[1] is not None
                liste = E("ol" if geordnet else "ul")
                while i < len(zeilen) and (m := LISTE.fullmatch(zeilen[i])) and (m[1] is not None) == geordnet:
                    liste.append(inline(E("li"), m[2]))
                    i += 1
                out.append(liste)
            else:
                j = i + 1
                while j < len(zeilen) and not _sonderzeile(zeilen[j]):
                    j += 1
                out.append(textabsatz(zeilen[i:j]))
                i = j
    return out


def anhaengen(el: ET.Element, text: str) -> None:
    """Hängt Text (mit $Formeln$) hinten an el an — für Absätze, in denen Lücken oder Hottexte stehen."""
    tmp = inline(E("p"), text)
    if len(el):
        el[-1].tail = (el[-1].tail or "") + (tmp.text or "")
    else:
        el.text = (el.text or "") + (tmp.text or "")
    for kind in list(tmp):
        el.append(kind)


def medium(m, ids) -> ET.Element:
    """Video oder Audio per URL, so wie es OpenOlats «Medien einfügen» schreibt.
    Auch mp3 läuft als type="video" — OLAT hat nur den einen Player."""
    if isinstance(m, str):
        m = {"url": m}
    url, b, h = str(m["url"]), int(m.get("breite", 640)), int(m.get("hoehe", 480))
    vid = f"olatFlashMovieViewer{int(ids('', 12), 16) % 900000 + 100000}"
    # der Rest von data-oo-movie ist alte Flowplayer-Konfiguration, unverändert übernommen
    oo = f"'{url}','{vid}',{b},{h},'',0,'video','',false,false,true,''"
    return E("p", None, E("object", {"id": vid, "class": "olatFlashMovieViewer", "data": url, "type": "video",
                                     "width": b, "height": h, "data-oo-movie": oo}, text=" "))


def stamm(f: dict, ids, frage=None) -> list[ET.Element]:
    """Fragetext-Absätze, danach die Medien aus `medien:`."""
    return [*bloecke(frage if frage is not None else f.get("frage")),
            *(medium(m, ids) for m in f.get("medien") or [])]


def value(v) -> ET.Element:
    return E("value", text=str(v))


def outcomes(punkte, feedback_zuerst: bool = False) -> list[ET.Element]:
    def od(ident, base, default, view=False):
        a = {"identifier": ident, "cardinality": "single", "baseType": base}
        if view:
            a["view"] = "testConstructor"
        return E("outcomeDeclaration", a, E("defaultValue", None, value(default)))
    fb = od("FEEDBACKBASIC", "identifier", "none", view=True)
    rest = [od("SCORE", "float", "0.0"), od("MINSCORE", "float", "0.0", view=True),
            od("MAXSCORE", "float", zahl(punkte))]
    return [fb, *rest] if feedback_zuerst else [*rest, fb]


def var(ident):
    return E("variable", {"identifier": ident})


def setze_feedback(wert):
    return E("setOutcomeValue", {"identifier": "FEEDBACKBASIC"},
             E("baseValue", {"baseType": "identifier"}, text=wert))


def volle_punkte():
    return E("setOutcomeValue", {"identifier": "SCORE"}, E("sum", None, var("SCORE"), var("MAXSCORE")))


def ist_richtig(resp="RESPONSE_1"):
    return E("match", None, var(resp), E("correct", {"identifier": resp}))


def ist_leer(resp="RESPONSE_1"):
    return E("isNull", None, var(resp))


def klammer_min_max() -> list[ET.Element]:
    def rc(op, grenze):
        return E("responseCondition", None, E("responseIf", None,
                 E(op, None, var("SCORE"), var(grenze)),
                 E("setOutcomeValue", {"identifier": "SCORE"}, var(grenze))))
    return [rc("lt", "MINSCORE"), rc("gt", "MAXSCORE")]


def verarbeitung(bedingung: ET.Element) -> ET.Element:
    return E("responseProcessing", None, bedingung, *klammer_min_max())


def alles_oder_nichts(treffer: ET.Element, leer_zuerst: bool = False) -> ET.Element:
    """Volle Punkte bei `treffer`, sonst 0 — OpenOlats Standardbewertung."""
    zweige = []
    if leer_zuerst:
        zweige.append(E("responseIf", None, ist_leer(), setze_feedback("empty")))
    tag = "responseElseIf" if leer_zuerst else "responseIf"
    zweige.append(E(tag, None, treffer, volle_punkte(), setze_feedback("correct")))
    zweige.append(E("responseElse", None, setze_feedback("incorrect")))
    return verarbeitung(E("responseCondition", None, *zweige))


def item(ident: str, titel: str, decls: list, body: ET.Element, rp: ET.Element) -> ET.Element:
    root = E("assessmentItem", {"identifier": ident, "title": titel, "adaptive": "false",
                                "timeDependent": "false", **TOOL})
    root.set(f"{{{XSI}}}schemaLocation", SCHEMA_LOC)
    for d in decls:
        root.append(d)
    root.append(body)
    root.append(rp)
    return root


def antwortliste(f: dict, feld: str) -> list[tuple[str, bool]]:
    """`- Bern` oder `- {text: Bern, richtig: true}` -> [(text, richtig)]."""
    out = []
    for a in f.get(feld) or []:
        if isinstance(a, dict):
            fremd = [k for k in a if k not in ("text", "richtig")]
            if fremd or "text" not in a:
                # typisch: {text: Temperatur, bei der …} — das Komma zerschneidet den Text
                raise FehlerImFragensatz(
                    f"«{f.get('titel', '?')}»: Eintrag in {feld} unvollständig oder zerschnitten "
                    f"({', '.join(map(repr, fremd)) or 'kein text'}) — Text mit Komma in Anführungszeichen setzen")
            out.append((str(a["text"]), bool(a.get("richtig", False))))
        else:
            out.append((str(a), False))
    return out


def pflicht(f: dict, feld: str):
    if feld not in f or f[feld] in (None, "", []):
        raise FehlerImFragensatz(f"Frage «{f.get('titel', '?')}»: Feld «{feld}» fehlt")
    return f[feld]


# --------------------------------------------------------------- Fragetypen

def bau_choice(f, ids, typ):
    antworten = antwortliste(f, "antworten")
    richtige = [t for t, r in antworten if r]
    if typ == "sc" and len(richtige) != 1:
        raise FehlerImFragensatz(f"«{f['titel']}»: sc braucht genau eine richtige Antwort")
    if typ == "mc" and not richtige:
        raise FehlerImFragensatz(f"«{f['titel']}»: mc braucht mindestens eine richtige Antwort")
    cid = {t: ids(typ) for t, _ in antworten}
    decl = E("responseDeclaration", {"identifier": "RESPONSE_1",
             "cardinality": "single" if typ == "sc" else "multiple", "baseType": "identifier"},
             E("correctResponse", None, *[value(cid[t]) for t in richtige]))
    ia = {"responseIdentifier": "RESPONSE_1", "shuffle": str(f.get("mischen", True)).lower()}
    ia |= {"maxChoices": "1"} if typ == "sc" else {"maxChoices": "0", "minChoices": "0"}
    ia["orientation"] = "vertical"
    inter = E("choiceInteraction", ia,
              *[E("simpleChoice", {"identifier": cid[t]}, p(t)) for t, _ in antworten])
    body = E("itemBody", None, *stamm(f, ids), inter)
    return [decl], body, alles_oder_nichts(ist_richtig(), leer_zuerst=(typ == "sc"))


def bau_kprim(f, ids, typ):
    aussagen = antwortliste(f, "aussagen")
    if len(aussagen) != 4:
        raise FehlerImFragensatz(f"«{f['titel']}»: kprim braucht genau 4 Aussagen")
    punkte = float(f.get("punkte", 1))
    viertel = punkte / 4
    cid = [ids("k", 16) for _ in aussagen]
    paare = [f"{c} {'correct' if r else 'wrong'}" for c, (_, r) in zip(cid, aussagen)]
    decl = E("responseDeclaration", {"identifier": "KPRIM_RESPONSE_1", "cardinality": "multiple",
                                     "baseType": "directedPair"},
             E("correctResponse", None, *map(value, paare)),
             E("mapping", {"defaultValue": zahl(-viertel)},
               *[E("mapEntry", {"mapKey": k, "mappedValue": zahl(viertel)}) for k in paare]))
    inter = E("matchInteraction", {"class": "match_krpim",  # sic, so schreibt es OpenOlat
                                   "responseIdentifier": "KPRIM_RESPONSE_1",
                                   "shuffle": str(f.get("mischen", False)).lower(),
                                   "maxAssociations": "4"},
              E("simpleMatchSet", None, *[
                  E("simpleAssociableChoice", {"identifier": c, "matchMax": "1", "matchMin": "1"}, p(t))
                  for c, (t, _) in zip(cid, aussagen)]),
              E("simpleMatchSet", None,
                E("simpleAssociableChoice", {"identifier": "correct", "fixed": "true", "matchMax": "4"}, text="+"),
                E("simpleAssociableChoice", {"identifier": "wrong", "fixed": "true", "matchMax": "4"}, text="-")))
    body = E("itemBody", None, *stamm(f, ids), inter)
    resp = "KPRIM_RESPONSE_1"
    groesse = E("containerSize", None, var(resp))
    rc = E("responseCondition", None,
           E("responseIf", None, ist_leer(resp), setze_feedback("empty")),
           E("responseElseIf", None,
             E("not", None, E("equal", {"toleranceMode": "exact"}, groesse,
                              E("baseValue", {"baseType": "integer"}, text="4"))),
             E("setOutcomeValue", {"identifier": "SCORE"}, E("sum", None,
               E("mapResponse", {"identifier": resp}),
               E("product", None,
                 E("subtract", None, E("baseValue", {"baseType": "integer"}, text="4"),
                   E("containerSize", None, var(resp))),
                 E("baseValue", {"baseType": "float"}, text=zahl(-viertel)))))),
           E("responseElseIf", None, ist_richtig(resp), volle_punkte(), setze_feedback("correct")),
           E("responseElse", None,
             E("setOutcomeValue", {"identifier": "SCORE"}, E("sum", None, E("mapResponse", {"identifier": resp}))),
             setze_feedback("incorrect")))
    return [decl], body, verarbeitung(rc)


def zuordnung(f) -> list[tuple[str, str]]:
    """loesung: {Zeile: Spalte} oder {Zeile: [Spalte, ...]} oder [[Zeile, Spalte], ...]."""
    l = pflicht(f, "loesung")
    paare = []
    if isinstance(l, dict):
        for z, s in l.items():
            for s1 in (s if isinstance(s, list) else [s]):
                paare.append((str(z), str(s1)))
    else:
        paare = [(str(z), str(s)) for z, s in l]
    return paare


def bau_match(f, ids, typ):
    zeilen = [str(z) for z in pflicht(f, "zeilen")]
    spalten = [str(s) for s in pflicht(f, "spalten")]
    zid = {z: ids("A", 16) for z in zeilen}
    sid = {s: ids("M", 16) for s in spalten}
    paare = zuordnung(f)
    for z, s in paare:
        if z not in zid or s not in sid:
            raise FehlerImFragensatz(f"«{f['titel']}»: Lösung {z!r} -> {s!r} passt zu keiner Zeile/Spalte")
    klasse = "match_matrix" if typ == "match" else "match_dnd source-left"
    decl = E("responseDeclaration", {"identifier": "RESPONSE_1", "cardinality": "multiple",
                                     "baseType": "directedPair"},
             E("correctResponse", None, *[value(f"{zid[z]} {sid[s]}") for z, s in paare]))

    def satz(d):
        return E("simpleMatchSet", None, *[
            E("simpleAssociableChoice", {"identifier": i, "matchMax": "0", "matchMin": "0"}, p(t))
            for t, i in d.items()])
    inter = E("matchInteraction", {"class": klasse, "responseIdentifier": "RESPONSE_1",
                                   "shuffle": str(f.get("mischen", False)).lower(), "maxAssociations": "0"},
              satz(zid), satz(sid))
    body = E("itemBody", None, *stamm(f, ids), inter)
    return [decl], body, alles_oder_nichts(ist_richtig())


def bau_truefalse(f, ids, typ):
    aussagen = antwortliste(f, "aussagen")
    aid = [ids("A", 16) for _ in aussagen]
    offen, richtig, falsch = ids("unanswered", 26), ids("right", 21), ids("wrong", 21)
    decl = E("responseDeclaration", {"identifier": "RESPONSE_1", "cardinality": "multiple",
                                     "baseType": "directedPair"},
             E("correctResponse", None, *[value(f"{i} {richtig if r else falsch}")
                                          for i, (_, r) in zip(aid, aussagen)]))
    inter = E("matchInteraction", {"class": "match_true_false source-right", "responseIdentifier": "RESPONSE_1",
                                   "shuffle": str(f.get("mischen", False)).lower(), "maxAssociations": "0"},
              E("simpleMatchSet", None, *[
                  E("simpleAssociableChoice", {"identifier": i, "matchMax": "1", "matchMin": "0"}, p(t))
                  for i, (t, _) in zip(aid, aussagen)]),
              E("simpleMatchSet", None, *[
                  E("simpleAssociableChoice", {"identifier": i, "matchMax": "0", "matchMin": "0"}, p(t))
                  for i, t in ((offen, "Unbeantwortet"), (richtig, "Richtig"), (falsch, "Falsch"))]))
    body = E("itemBody", None, *stamm(f, ids), inter)
    return [decl], body, alles_oder_nichts(ist_richtig())


LUECKE = re.compile(r"\{\{(.+?)\}\}")


def bau_luecken(f, ids, typ):
    """Lücken im Feld `text`:
         {{Bern|Berne}}   Texteingabe, jede Variante gilt
         {{#100}}         Zahl, {{#100±0.5}} mit Toleranz
         {{*Sonne|Mond}}  Dropdown, * markiert die richtige Option
    fib erlaubt nur Text-, numerical nur Zahl-, inlinechoice nur Dropdown-Lücken."""
    erlaubt = {"fib": {"text"}, "numerical": {"zahl"}, "inlinechoice": {"dropdown"},
               "gapmixed": {"text", "zahl", "dropdown"}}[typ]
    gross_klein = bool(f.get("gross_klein", False))
    decls, bedingungen = [], []

    def luecke(roh: str, n: int) -> ET.Element:
        resp = f"RESPONSE_{n}"
        roh = roh.strip()
        if roh.startswith("#"):
            art = "zahl"
        elif any(o.strip().startswith("*") for o in roh.split("|")):
            art = "dropdown"
        else:
            art = "text"
        if art not in erlaubt:
            raise FehlerImFragensatz(f"«{f['titel']}»: Lücke {{{{{roh}}}}} ist {art}, in {typ} nicht erlaubt")
        if art == "text":
            varianten = [v.strip() for v in roh.split("|")]
            decls.append(E("responseDeclaration", {"identifier": resp, "cardinality": "single", "baseType": "string"},
                           E("correctResponse", None, value(varianten[0])),
                           E("mapping", {"defaultValue": "0.0"}, *[
                               E("mapEntry", {"mapKey": v, "mappedValue": "-1.0",
                                              "caseSensitive": str(gross_klein).lower()}) for v in varianten])))
            # OpenOlat-Konvention: -1.0 aus dem Mapping heisst «eine gültige Variante getroffen»
            bedingungen.append(E("match", None, E("baseValue", {"baseType": "float"}, text="-1.0"),
                                 E("mapResponse", {"identifier": resp})))
            return E("textEntryInteraction", {"class": "", "responseIdentifier": resp, "placeholderText": ""})
        if art == "zahl":
            # Dezimalkomma wie in Schweizer Unterlagen ({{#8,314±0,001}}) gilt wie ein Punkt
            m = re.fullmatch(r"#\s*(-?\d+(?:[.,]\d+)?)\s*(?:(?:±|\+-)\s*(\d+(?:[.,]\d+)?))?", roh)
            if not m:
                raise FehlerImFragensatz(f"«{f['titel']}»: Zahl-Lücke {{{{{roh}}}}} nicht lesbar "
                                         "(erwartet z. B. {{#3.5}} oder {{#3,5±0,1}}, ohne Tausender-Trennzeichen)")
            wert, toleranz = m[1].replace(",", "."), (m[2] or "").replace(",", ".")
            decls.append(E("responseDeclaration", {"identifier": resp, "cardinality": "single", "baseType": "float"},
                           E("correctResponse", None, value(zahl(wert)))))
            if toleranz:
                # in OLAT importiert und bewertet: beispiele/importtest.yaml (22.09.2026)
                tol = {"toleranceMode": "absolute", "tolerance": f"{toleranz} {toleranz}"}
            else:
                tol = {"toleranceMode": "exact"}
            bedingungen.append(E("equal", {**tol, "includeLowerBound": "true", "includeUpperBound": "true"},
                                 E("correct", {"identifier": resp}), var(resp)))
            return E("textEntryInteraction", {"responseIdentifier": resp})
        optionen = [o.strip() for o in roh.split("|")]
        richtige = [o for o in optionen if o.startswith("*")]
        if len(richtige) != 1:
            raise FehlerImFragensatz(f"«{f['titel']}»: Dropdown {{{{{roh}}}}} braucht genau eine *-Option")
        oid = {o: ids("inline", 32) for o in optionen}
        decls.append(E("responseDeclaration", {"identifier": resp, "cardinality": "single", "baseType": "identifier"},
                       E("correctResponse", None, value(oid[richtige[0]]))))
        bedingungen.append(ist_richtig(resp))
        return E("inlineChoiceInteraction", {"responseIdentifier": resp, "shuffle": str(f.get("mischen", True)).lower()},
                 *[E("inlineChoice", {"identifier": oid[o]}, text=o.lstrip("*").strip()) for o in optionen])

    body = E("itemBody", {"class": FIB_KLASSE[typ]}, *stamm(f, ids))
    n = 0
    for absatz in absaetze(pflicht(f, "text")):
        el, pos = E("p"), 0
        for m in LUECKE.finditer(absatz):
            anhaengen(el, absatz[pos:m.start()])
            n += 1
            el.append(luecke(m[1], n))
            pos = m.end()
        anhaengen(el, absatz[pos:])
        if len(el) and not el[-1].tail:
            el[-1].tail = None
        body.append(el)
    if n == 0:
        raise FehlerImFragensatz(f"«{f['titel']}»: {typ} ohne {{{{Lücke}}}} im Text")
    return decls, body, alles_oder_nichts(E("and", None, *bedingungen))


HOTTEXT = re.compile(r"\[\[(\*?)(.+?)\]\]")


def bau_hottext(f, ids, typ):
    """Im `text` markiert [[Wort]] anklickbare Stellen, [[*Wort]] die richtigen."""
    inter = E("hottextInteraction", {"responseIdentifier": "RESPONSE_1", "maxChoices": "0"})
    richtige = []
    for absatz in absaetze(pflicht(f, "text")):
        el, pos = E("p"), 0
        for m in HOTTEXT.finditer(absatz):
            anhaengen(el, absatz[pos:m.start()])
            hid = ids("ht", 32)
            if m[1]:
                richtige.append(hid)
            el.append(E("hottext", {"identifier": hid}, text=m[2]))
            pos = m.end()
        anhaengen(el, absatz[pos:])
        if len(el) and not el[-1].tail:
            el[-1].tail = None
        inter.append(el)
    if not richtige:
        raise FehlerImFragensatz(f"«{f['titel']}»: hottext ohne [[*richtige]] Stelle")
    decl = E("responseDeclaration", {"identifier": "RESPONSE_1", "cardinality": "multiple", "baseType": "identifier"},
             E("correctResponse", None, *map(value, richtige)))
    body = E("itemBody", None, *stamm(f, ids), inter)
    return [decl], body, alles_oder_nichts(ist_richtig())


def bau_hotspot(f, ids, typ, bilder):
    bild = bilder.nimm(pflicht(f, "bild"))
    bereiche = pflicht(f, "bereiche")
    hid = [ids("hc", 17) for _ in bereiche]
    richtige = [i for i, b in zip(hid, bereiche) if b.get("richtig")]
    if not richtige:
        raise FehlerImFragensatz(f"«{f['titel']}»: hotspot ohne richtigen Bereich")
    einzeln = len(richtige) == 1
    decl = E("responseDeclaration", {"identifier": "RESPONSE_1", "cardinality": "single" if einzeln else "multiple",
                                     "baseType": "identifier"},
             E("correctResponse", None, *map(value, richtige)))
    b, h = bild.groesse(f)
    inter = E("hotspotInteraction", {"class": "", "responseIdentifier": "RESPONSE_1",
                                     "maxChoices": "1" if einzeln else str(len(bereiche))},
              E("object", {"data": bild.name, "type": bild.mime, "width": b, "height": h}),
              *[E("hotspotChoice", {"identifier": i, "fixed": "false", "shape": ber.get("form", "circle"),
                                    "coords": ber["koord"]}) for i, ber in zip(hid, bereiche)])
    body = E("itemBody", None, *stamm(f, ids), inter)
    return [decl], body, alles_oder_nichts(ist_richtig(), leer_zuerst=True)


def bau_order(f, ids, typ):
    elemente = [str(e) for e in pflicht(f, "elemente")]  # in richtiger Reihenfolge
    oid = [ids("order", 31) for _ in elemente]
    decl = E("responseDeclaration", {"identifier": "RESPONSE_1", "cardinality": "ordered", "baseType": "identifier"},
             E("correctResponse", None, *map(value, oid)))
    inter = E("orderInteraction", {"responseIdentifier": "RESPONSE_1", "shuffle": "true",
                                   "maxChoices": str(len(elemente)), "minChoices": "0", "orientation": "vertical"},
              *[E("simpleChoice", {"identifier": i}, p(t)) for i, t in zip(oid, elemente)])
    body = E("itemBody", None, *stamm(f, ids), inter)
    return [decl], body, alles_oder_nichts(ist_richtig())


def offen_bewertet(mit_und_oder: bool = False) -> ET.Element:
    """Freitext/Upload/Zeichnen: nur «leer» oder «beantwortet», Punkte vergibt die Lehrperson."""
    leer, nicht_leer = ist_leer(), E("not", None, ist_leer())
    if mit_und_oder:  # so exportiert OpenOlat den Upload-Typ
        leer, nicht_leer = E("and", None, leer), E("or", None, nicht_leer)
    return verarbeitung(E("responseCondition", None,
                          E("responseIf", None, leer, setze_feedback("empty")),
                          E("responseElseIf", None, nicht_leer, setze_feedback("answered"))))


def bau_offen(f, ids, typ, bilder):
    base = "string" if typ == "essay" else "file"
    decl = E("responseDeclaration", {"identifier": "RESPONSE_1", "cardinality": "single", "baseType": base})
    if typ == "essay":
        a = {"class": "", "responseIdentifier": "RESPONSE_1", "minStrings": "0"}
        if f.get("zeilen"):
            a["expectedLines"] = str(f["zeilen"])
        inter = E("extendedTextInteraction", a)
    elif typ == "upload":
        inter = E("uploadInteraction", {"responseIdentifier": "RESPONSE_1"})
    else:
        bild = bilder.nimm(f["bild"]) if f.get("bild") else bilder.leer(500, 350)
        b, h = bild.groesse(f)
        inter = E("drawingInteraction", {"responseIdentifier": "RESPONSE_1"},
                  E("object", {"data": bild.name, "type": bild.mime, "width": b, "height": h}))
    body = E("itemBody", None, *stamm(f, ids, pflicht(f, "frage")), inter)
    return [decl], body, offen_bewertet(mit_und_oder=(typ == "upload"))


# --------------------------------------------------------------- Bilder

def png_groesse(daten: bytes) -> tuple[int, int] | None:
    """Pixelgrösse aus dem Dateikopf — PNG, JPEG, GIF; sonst None."""
    if daten[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", daten[16:24])
    if daten[:6] in (b"GIF87a", b"GIF89a"):
        return struct.unpack("<HH", daten[6:10])
    if daten[:2] == b"\xff\xd8":  # JPEG: bis zum SOF-Segment laufen
        i = 2
        while i + 9 < len(daten):
            if daten[i] != 0xFF:
                i += 1
                continue
            marke, laenge = daten[i + 1], struct.unpack(">H", daten[i + 2:i + 4])[0]
            if marke in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, b = struct.unpack(">HH", daten[i + 5:i + 9])
                return b, h
            i += 2 + laenge
    return None


def leeres_png(b: int, h: int) -> bytes:
    zeile = b"\x00" + b"\xff\xff\xff" * b
    roh = zlib.compress(zeile * h)

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", b, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", roh) + chunk(b"IEND", b""))


class Bild:
    MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
            ".svg": "image/svg+xml"}

    def __init__(self, name: str, daten: bytes):
        self.name, self.daten = name, daten
        self.mime = self.MIME.get(Path(name).suffix.lower(), "application/octet-stream")

    def groesse(self, f) -> tuple[int, int]:
        if f.get("breite") and f.get("hoehe"):
            return int(f["breite"]), int(f["hoehe"])
        g = png_groesse(self.daten)
        if not g:
            raise FehlerImFragensatz(f"«{f['titel']}»: breite/hoehe angeben (nur bei PNG/JPEG/GIF automatisch)")
        return g


class Bilder:
    def __init__(self, basis: Path):
        self.basis, self.dateien = basis, {}

    def nimm(self, pfad: str) -> Bild:
        quelle = (self.basis / pfad).resolve()
        if not quelle.is_file():
            raise FehlerImFragensatz(f"Bild nicht gefunden: {quelle}")
        bild = Bild(quelle.name, quelle.read_bytes())
        alt = self.dateien.get(bild.name)
        if alt is not None and alt.daten != bild.daten:
            raise FehlerImFragensatz(f"Zwei verschiedene Bilder heissen {bild.name}")
        self.dateien[bild.name] = bild
        return bild

    def leer(self, b: int, h: int) -> Bild:
        bild = Bild(f"leer_{b}x{h}.png", leeres_png(b, h))
        self.dateien[bild.name] = bild
        return bild


# --------------------------------------------------------------- Test und Paket

BAUER = {"sc": bau_choice, "mc": bau_choice, "kprim": bau_kprim, "match": bau_match,
         "matchdraganddrop": bau_match, "matchtruefalse": bau_truefalse, "fib": bau_luecken,
         "numerical": bau_luecken, "inlinechoice": bau_luecken, "gapmixed": bau_luecken,
         "hottext": bau_hottext, "order": bau_order}
MIT_BILDERN = {"hotspot": bau_hotspot, "essay": bau_offen, "upload": bau_offen, "drawing": bau_offen}
FEEDBACK_ZUERST = {"kprim", "essay", "upload", "drawing"}


MAX_BILDBREITE = 600  # px, Anzeige im Test; das Bild selbst bleibt in voller Auflösung im Paket


def mit_bildern(root: ET.Element, f: dict, bilder: Bilder) -> None:
    """Bilder im Fragetext: je ein <p><img/></p> direkt nach den Absätzen von `frage`.

    In OLAT importiert und angezeigt (22.09.2026, beispiele/bildtest.yaml). Gebaut nach QTI 2.1
    (XHTML-img im itemBody), Datei neben den Fragen im Paket wie hotspot.png im Referenz-Export.
    `bilder: [datei.png, …]` oder `[{datei, alt, breite, hoehe}]`, Pfade relativ zur YAML-Datei."""
    body = root.find(q("itemBody"))
    pos = len(bloecke(f.get("frage")))
    for eintrag in f["bilder"]:
        if isinstance(eintrag, str):
            eintrag = {"datei": eintrag}
        bild = bilder.nimm(pflicht(eintrag, "datei"))
        b, h = bild.groesse({"titel": f["titel"], "breite": eintrag.get("breite"), "hoehe": eintrag.get("hoehe")})
        if b > MAX_BILDBREITE and not eintrag.get("breite"):
            b, h = MAX_BILDBREITE, round(h * MAX_BILDBREITE / b)
        img = E("img", {"src": bild.name, "alt": str(eintrag.get("alt") or "Abbildung"), "width": b, "height": h})
        body.insert(pos, E("p", None, img))
        pos += 1


STEUERZEICHEN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def steuerzeichen(o) -> list[str]:
    """Alle in XML verbotenen Steuerzeichen in beliebig verschachtelten Feldern."""
    if isinstance(o, str):
        return sorted({f"U+{ord(c):04X}" for c in STEUERZEICHEN.findall(o)})
    if isinstance(o, dict):
        o = list(o.values())
    if isinstance(o, list):
        return sorted({z for x in o for z in steuerzeichen(x)})
    return []


def baue_frage(f: dict, ids: Ids, bilder: Bilder):
    typ = str(pflicht(f, "typ")).lower()
    typ = ALIASE.get(typ, typ)
    if typ not in TYPEN:
        raise FehlerImFragensatz(f"Unbekannter Typ «{typ}». Erlaubt: {', '.join(TYPEN)}")
    f.setdefault("titel", typ)
    if (zeichen := steuerzeichen(f)):
        # in XML 1.0 verboten; entsteht, wenn ein Sprachmodell Zeichen verstümmelt (gpt-4.1-mini, 22.09.2026)
        raise FehlerImFragensatz(f"«{f['titel']}»: unzulässige Steuerzeichen im Text ({', '.join(zeichen)}) "
                                 "— Text prüfen, vermutlich verstümmelte Umlaute oder Striche")
    if typ in MIT_BILDERN:
        decls, body, rp = MIT_BILDERN[typ](f, ids, typ, bilder)
    else:
        decls, body, rp = BAUER[typ](f, ids, typ)
    decls += outcomes(f.get("punkte", 1), feedback_zuerst=typ in FEEDBACK_ZUERST)
    datei_id = ids(typ)
    root = item(ids(typ), str(f["titel"]), decls, body, rp)
    if f.get("bilder"):
        mit_bildern(root, f, bilder)
    interaktionen = [TYPEN[typ]]
    for feld in ("hinweis", "musterloesung"):
        if f.get(feld) and typ != "essay":
            # bisher nur beim Freitext an OpenOlat-Exporten verifiziert (referenz/hinweis/, referenz/loesung/)
            raise FehlerImFragensatz(f"«{f['titel']}»: {feld} gibt es vorerst nur bei essay/freitext")
    if f.get("musterloesung"):
        mit_loesung(root, f["musterloesung"], ids)
    if f.get("hinweis"):
        mit_hinweis(root, f["hinweis"])
        interaktionen.append("endAttemptInteraction")
    return typ, f"{datei_id}.xml", datei_id, root, float(f.get("punkte", 1)), interaktionen


def mit_hinweis(root: ET.Element, hinweis) -> None:
    """Hinweis-Knopf unter der Antwort; Klick öffnet den Text als Dialog.
    Genau so schreibt OpenOlat den Reiter Feedback → «Hinweis» (referenz/hinweis/).
    Achtung: Lernende sehen den Hinweis WÄHREND des Tests."""
    if isinstance(hinweis, str):
        hinweis = {"text": hinweis}
    titel, text = str(hinweis.get("titel", "Hinweis")), pflicht(hinweis, "text")
    decls = root.findall(q("responseDeclaration"))
    pos = list(root).index(decls[-1]) + 1
    root.insert(pos, E("responseDeclaration", {"identifier": "HINTREQUEST", "cardinality": "single",
                                               "baseType": "boolean"}))
    letzte_od = root.findall(q("outcomeDeclaration"))[-1]
    root.insert(list(root).index(letzte_od) + 1,
                E("outcomeDeclaration", {"identifier": "HINTFEEDBACKMODAL", "cardinality": "single",
                                         "baseType": "identifier"}))
    root.find(q("itemBody")).append(
        E("p", None, E("endAttemptInteraction", {"responseIdentifier": "HINTREQUEST", "title": titel})))
    root.find(q("responseProcessing")).insert(0, E("responseCondition", None, E("responseIf", None,
        var("HINTREQUEST"),
        E("setOutcomeValue", {"identifier": "HINTFEEDBACKMODAL"},
          E("baseValue", {"baseType": "identifier"}, text="HINT")))))
    root.append(dialog("HINTFEEDBACKMODAL", "HINT", titel, text))


def dialog(outcome: str, ident: str, titel: str, text: str) -> ET.Element:
    mf = E("modalFeedback", {"showHide": "show", "outcomeIdentifier": outcome, "identifier": ident, "title": titel})
    absaetze_ = bloecke(text)
    for a in absaetze_[:-1]:
        a.tail = "\n"  # OpenOlat trennt die Absätze mit Zeilenumbruch
    mf.extend(absaetze_)
    return mf


def mit_loesung(root: ET.Element, loesung, ids) -> None:
    """Reiter Feedback → «Korrekte Lösung», so wie OpenOlat ihn schreibt (referenz/loesung/).
    Kein Knopf und keine Verarbeitung — OLAT zeigt den Text selbst an (Korrektur,
    Resultate). Muss vor mit_hinweis laufen: OpenOlat setzt diesen Dialog zuerst."""
    if isinstance(loesung, str):
        loesung = {"text": loesung}
    titel, text = str(loesung.get("titel", "Korrekte Lösung")), pflicht(loesung, "text")
    fb = next(d for d in root.findall(q("outcomeDeclaration")) if d.get("identifier") == "FEEDBACKBASIC")
    pos = list(root).index(fb) + 1
    root.insert(pos, E("outcomeDeclaration", {"identifier": "FEEDBACKMODAL", "cardinality": "multiple",
                                              "baseType": "identifier", "view": "testConstructor"}))
    root.insert(pos + 1, E("outcomeDeclaration", {"identifier": "SOLUTIONMODAL", "cardinality": "single",
                                                  "baseType": "identifier", "view": "testConstructor"}))
    ident = "Feedback" + str(int(ids("", 16), 16))[:15]
    root.append(dialog("SOLUTIONMODAL", ident, titel, text))


def sektionen(satz: dict) -> list[dict]:
    if "sektionen" in satz:
        return satz["sektionen"]
    return [{"titel": satz.get("sektion", "Sektion"), "fragen": pflicht(satz, "fragen"),
             "mischen": satz.get("mischen", False)}]


def baue_test(titel, items_je_sektion, ids, gesamt) -> ET.Element:
    root = E("assessmentTest", {"identifier": ids("test"), "title": titel, **TOOL})
    root.set(f"{{{XSI}}}schemaLocation", SCHEMA_LOC)
    for ident, default in (("MINSCORE", "0.0"), ("MAXSCORE", zahl(gesamt)), ("SCORE", None)):
        od = E("outcomeDeclaration", {"identifier": ident, "cardinality": "single", "baseType": "float"})
        if default is not None:
            od.append(E("defaultValue", None, value(default)))
        root.append(od)
    tp = E("testPart", {"identifier": ids("tp"), "navigationMode": "nonlinear", "submissionMode": "individual"},
           E("itemSessionControl", {"maxAttempts": "0", "showFeedback": "false", "allowReview": "false",
                                    "showSolution": "false", "allowComment": "true", "allowSkipping": "true"}))
    for sek, items in items_je_sektion:
        s = E("assessmentSection", {"identifier": ids("sect"), "fixed": "true",
                                    "title": sek.get("titel", "Sektion"), "visible": "true"},
              E("itemSessionControl"), E("ordering", {"shuffle": str(sek.get("mischen", False)).lower()}),
              E("rubricBlock", {"view": "candidate"}))
        for datei, datei_id in items:
            s.append(E("assessmentItemRef", {"identifier": datei_id, "href": datei}))
        tp.append(s)
    root.append(tp)
    root.append(E("outcomeProcessing", None,
                  E("setOutcomeValue", {"identifier": "SCORE"}, E("sum", None,
                    E("testVariables", {"variableIdentifier": "SCORE"}))),
                  E("outcomeCondition", None, E("outcomeIf", None,
                    E("lt", None, var("SCORE"), var("MINSCORE")),
                    E("setOutcomeValue", {"identifier": "SCORE"}, var("MINSCORE"))))))
    return root


MANIFEST_KOPF = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<manifest xmlns="http://www.imsglobal.org/xsd/imscp_v1p1" xmlns:ns2="http://www.imsglobal.org/xsd/imsqti_metadata_v2p1" xmlns:ns3="http://www.imsglobal.org/xsd/imsmd_v1p2" xmlns:ns4="http://www.openolat.org/xsd/oomd_v1p1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.imsglobal.org/xsd/imscp_v1p1 http://www.imsglobal.org/xsd/imscp_v1p2.xsd http://www.imsglobal.org/xsd/imsmd_v1p2 http://www.imsglobal.org/xsd/imsmd_v1p2p4.xsd http://www.imsglobal.org/xsd/imsqti_metadata_v2p1 http://www.imsglobal.org/xsd/qti/qtiv2p1/imsqti_metadata_v2p1.xsd">
    <metadata>
        <schema>QTIv2.1 Package</schema>
        <schemaversion>1.0.0</schemaversion>
        <ns3:lom/>
    </metadata>
    <resources>
"""
MANIFEST_ITEM = """        <resource identifier="{rid}" type="imsqti_item_xmlv2p1" href="{href}">
            <metadata>
                <ns3:lom>
                    <ns3:technical>
                        <ns3:format>text/x-imsqti-item-xml</ns3:format>
                    </ns3:technical>
                    <ns3:educational/>
                </ns3:lom>
                <ns2:qtiMetadata>
{interaktionen}
                </ns2:qtiMetadata>
                <ns4:ooMetadata>
                    <ns4:questionType>{typ}</ns4:questionType>
                </ns4:ooMetadata>
            </metadata>
            <file href="{href}"/>
        </resource>
"""
MANIFEST_TEST = """        <resource identifier="{rid}" type="imsqti_test_xmlv2p1" href="{href}">
            <file href="{href}"/>
        </resource>
"""
PAKETKONFIG = (Path(__file__).parent / "vorlagen" / "QTI21PackageConfig.xml")


def xml_bytes(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=False)


def baue_paket(yaml_pfad: Path, ziel: Path) -> dict:
    satz = yaml.safe_load(yaml_pfad.read_text(encoding="utf-8"))
    titel = str(pflicht(satz, "titel"))
    ids = Ids(f"{titel}")
    bilder = Bilder(yaml_pfad.parent)
    dateien: dict[str, bytes] = {}
    manifest = [MANIFEST_KOPF]
    items_je_sektion, gesamt, zaehler = [], 0.0, {}
    for sek in sektionen(satz):
        items = []
        for f in pflicht(sek, "fragen"):
            typ, datei, datei_id, root, punkte, interaktionen = baue_frage(dict(f), ids, bilder)
            dateien[datei] = xml_bytes(root)
            zeilen = "\n".join(f"                    <ns2:interactionType>{i}</ns2:interactionType>"
                                for i in interaktionen)
            manifest.append(MANIFEST_ITEM.format(rid=ids("item"), href=datei, interaktionen=zeilen, typ=typ))
            items.append((datei, datei_id))
            gesamt += punkte
            zaehler[typ] = zaehler.get(typ, 0) + 1
        items_je_sektion.append((sek, items))
    test_datei = f"test{uuid.uuid5(uuid.NAMESPACE_URL, 'olatqti/' + titel)}.xml"
    dateien[test_datei] = xml_bytes(baue_test(titel, items_je_sektion, ids, gesamt))
    manifest.append(MANIFEST_TEST.format(rid=ids("test"), href=test_datei))
    manifest.append("    </resources>\n</manifest>\n")
    dateien["imsmanifest.xml"] = "".join(manifest).encode("utf-8")
    dateien["QTI21PackageConfig.xml"] = PAKETKONFIG.read_bytes()
    for b in bilder.dateien.values():
        dateien[b.name] = b.daten
    ziel.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("imsmanifest.xml", dateien.pop("imsmanifest.xml"))
        for name, daten in dateien.items():
            z.writestr(name, daten)
    return {"titel": titel, "fragen": sum(zaehler.values()), "punkte": gesamt, "typen": zaehler}


# --------------------------------------------------------------- Prüfung

AUSWAHL = ("simpleChoice", "simpleAssociableChoice", "inlineChoice", "hottext", "hotspotChoice")


def pruefe_paket(zip_pfad: Path) -> list[str]:
    """Strukturprüfung vor dem Import. Leere Liste = nichts gefunden."""
    fehler = []
    with zipfile.ZipFile(zip_pfad) as z:
        namen = set(z.namelist())
        if "imsmanifest.xml" not in namen:
            return ["imsmanifest.xml fehlt"]
        man = ET.fromstring(z.read("imsmanifest.xml"))
        ns = {"cp": "http://www.imsglobal.org/xsd/imscp_v1p1"}
        hrefs = [r.get("href") for r in man.iterfind(".//cp:resource", ns)]
        tests = [r.get("href") for r in man.iterfind(".//cp:resource", ns) if r.get("type") == "imsqti_test_xmlv2p1"]
        if len(tests) != 1:
            fehler.append(f"Manifest: {len(tests)} Test-Ressourcen statt 1")
        for h in hrefs:
            if h not in namen:
                fehler.append(f"Manifest verweist auf fehlende Datei {h}")
        for h in hrefs:
            if h not in namen:
                continue
            try:
                root = ET.fromstring(z.read(h))
            except ET.ParseError as e:
                fehler.append(f"{h}: kein wohlgeformtes XML ({e})")
                continue
            if root.tag == q("assessmentTest"):
                for ref in root.iter(q("assessmentItemRef")):
                    if ref.get("href") not in hrefs:
                        fehler.append(f"Test verweist auf {ref.get('href')}, das nicht im Manifest steht")
                continue
            ids_ = [e.get("identifier") for t in AUSWAHL for e in root.iter(q(t))]
            if len(ids_) != len(set(ids_)):
                fehler.append(f"{h}: doppelte Identifikatoren")
            bekannt = set(ids_)
            for rd in root.iter(q("responseDeclaration")):
                if rd.get("baseType") not in ("identifier", "directedPair", "pair"):
                    continue
                for v in rd.iter(q("value")):
                    for teil in (v.text or "").split():
                        if teil not in bekannt:
                            fehler.append(f"{h}: Lösung verweist auf unbekannte Auswahl {teil}")
            for obj in root.iter(q("object")):
                if obj.get("data", "").startswith(("http://", "https://")):
                    if obj.get("class") == "olatFlashMovieViewer" and f"'{obj.get('id')}'" not in obj.get("data-oo-movie", ""):
                        fehler.append(f"{h}: Medien-id {obj.get('id')} fehlt in data-oo-movie")
                elif obj.get("data") not in namen:
                    fehler.append(f"{h}: Bild {obj.get('data')} fehlt im Paket")
            for img in root.iter(q("img")):
                if img.get("src") not in namen:
                    fehler.append(f"{h}: Bild {img.get('src')} fehlt im Paket")
    return fehler


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="befehl", required=True)
    b = sub.add_parser("build", help="YAML-Fragensatz -> QTI-2.1-Zip")
    b.add_argument("yaml", type=Path)
    b.add_argument("-o", "--out", type=Path)
    c = sub.add_parser("check", help="Zip vor dem Import prüfen")
    c.add_argument("zip", type=Path)
    a = ap.parse_args(argv)
    if a.befehl == "build":
        ziel = a.out or a.yaml.with_suffix(".zip")
        try:
            info = baue_paket(a.yaml, ziel)
        except FehlerImFragensatz as e:
            print(f"FEHLER: {e}", file=sys.stderr)
            return 1
        fehler = pruefe_paket(ziel)
        typen = ", ".join(f"{k} {v}" for k, v in info["typen"].items())
        print(f"{ziel}  «{info['titel']}»  {info['fragen']} Fragen, {info['punkte']:g} Punkte  ({typen})")
        for x in fehler:
            print(f"  PRÜFUNG: {x}", file=sys.stderr)
        return 1 if fehler else 0
    fehler = pruefe_paket(a.zip)
    for x in fehler:
        print(x)
    print("ok" if not fehler else f"{len(fehler)} Befund(e)")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
