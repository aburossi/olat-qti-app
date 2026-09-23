"""PDF mit Fragen und Lösungen -> Fragensatz (dict im YAML-Format von olatqti.py).

OpenAI liefert über Structured Outputs garantiert gültiges JSON nach SCHEMA; zu_fragensatz()
macht daraus das YAML-Format. Kein Streamlit-Import: testbar ohne App.
"""
from __future__ import annotations

import base64
import json
import re

import pymupdf

TYPEN = ["sc", "mc", "kprim", "match", "matchdraganddrop", "matchtruefalse", "fib", "numerical",
         "inlinechoice", "gapmixed", "hottext", "order", "essay", "upload"]


def _nullbar(schema: dict) -> dict:
    t = schema["type"]
    return {**schema, "type": [t, "null"]}


_WAHR = {"type": "object", "additionalProperties": False, "required": ["text", "richtig"],
         "properties": {"text": {"type": "string"}, "richtig": {"type": "boolean"}}}
_LISTE = {"type": "array", "items": {"type": "string"}}

FRAGE = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "typ": {"type": "string", "enum": TYPEN},
        "titel": {"type": "string"},
        "punkte": {"type": "number"},
        "frage": {"type": ["string", "null"]},
        "antworten": _nullbar({"type": "array", "items": _WAHR}),
        "aussagen": _nullbar({"type": "array", "items": _WAHR}),
        "zeilen": _nullbar(_LISTE),
        "spalten": _nullbar(_LISTE),
        "zuordnung": _nullbar({"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["zeile", "spalte"],
            "properties": {"zeile": {"type": "string"}, "spalte": {"type": "string"}}}}),
        "text": {"type": ["string", "null"]},
        "elemente": _nullbar(_LISTE),
        "antwortzeilen": {"type": ["integer", "null"]},
        "medien": _nullbar(_LISTE),
        "bilder": _nullbar({"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["datei", "alt"],
            "properties": {"datei": {"type": "string"}, "alt": {"type": "string"}}}}),
        "hinweis": {"type": ["string", "null"]},
        "musterloesung": {"type": ["string", "null"]},
        "quelle": {"type": ["string", "null"]},
        "unsicher": {"type": ["string", "null"]},
    },
}
FRAGE["required"] = list(FRAGE["properties"])

SEKTION = {
    "type": "object", "additionalProperties": False, "required": ["titel", "fragen"],
    "properties": {"titel": {"type": "string"}, "fragen": {"type": "array", "items": FRAGE}},
}

SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["titel", "sektionen", "uebersprungen"],
    "properties": {"titel": {"type": "string"}, "sektionen": {"type": "array", "items": SEKTION},
                   "uebersprungen": _LISTE},
}

SYSTEM_VORLAGE = """Du überträgst einen Test aus einem PDF in ein strukturiertes Format für OLAT.
Das PDF enthält Fragen UND Lösungen. Deine Aufgabe ist Übertragen, nicht Erfinden.

GRUNDREGELN
- Jede Frage des PDFs wird genau eine Frage, in der Reihenfolge des PDFs.
- Texte wörtlich übernehmen (Fragetext, Antwortoptionen, Lösungen). Nichts kürzen, nichts umformulieren,
  keine Rechtschreibung ändern. Nummerierungen wie «1.», «a)» weglassen. «Wörtlich» gilt für den Wortlaut —
  Formeln werden trotzdem in LaTeX gesetzt (siehe FORMELN), das ist Formatierung, keine Umformulierung.
- Nichts dazuerfinden: keine zusätzlichen Distraktoren, keine Hinweise, keine Lösungen, die nicht im PDF stehen.
- Fehlt die Lösung einer geschlossenen Frage im PDF oder ist etwas unklar: trotzdem übertragen, deine
  beste Lösung einsetzen und im Feld `unsicher` in einem Satz sagen, was fehlt. Sonst `unsicher` = null.
- Punkte aus dem PDF übernehmen; stehen keine da: 1 (Freitext: 2).
- `titel`: kurzer Fragetitel, 2–6 Wörter, mit Fragenummer aus dem PDF, z. B. «3 Dichte von Aluminium».
- `quelle`: Seite und Nummer im PDF, z. B. «S. 2, Aufgabe 3».
- Fragen, bei denen man IM Bild klicken, zeichnen oder beschriften muss: nicht übertragen, sondern in
  `uebersprungen` mit Nummer und Grund aufführen. Fragen, zu denen nur ein Bild gezeigt wird (Diagramm lesen,
  Schema deuten), werden normal übertragen — steht das Bild als «[Bild: …]» im Text, siehe BILDER IM TEXT;
  fehlt es, in `unsicher` vermerken.
- Test-`titel`: der Titel des PDFs.
- Nicht benutzte Felder einer Frage: null.

SEKTIONEN
- Gliedert das PDF die Fragen in Teile (z. B. «Teil A – Grundlagen», «A Single Choice», «Aufgabe 2:
  Werkstoffe», «Block C»), wird jeder Teil eine Sektion. `titel` der Sektion = Überschrift wörtlich
  (ohne Punktangaben wie «(12 Punkte)»); die Fragen des Teils in `fragen`, in der Reihenfolge des PDFs.
- Hat das PDF keine solche Gliederung: genau eine Sektion mit dem Titel «Fragen».
- Eine Überschrift, die nur eine einzige Frage einleitet, ist keine Sektion, sondern gehört zur Frage.
- Einleitungstext eines Teils (z. B. ein Fallbeispiel), der für mehrere Fragen gilt: in der `frage`
  jeder betroffenen Frage voranstellen, damit jede Frage in OLAT für sich lesbar ist.
- Alles, was zwischen Fragetext und Antwortoptionen steht — Formeln, Gleichungen, Matrizen, Tabellen,
  Angaben —, gehört in `frage` (als eigener Absatz). Nichts davon weglassen, auch nicht, wenn es im
  Text zerstückelt über mehrere Zeilen steht (gestapelte Brüche: Zähler und Nenner auf eigenen Zeilen).

FRAGETYP WÄHLEN — nach der Form im PDF
- sc: Auswahl, genau eine richtig → `antworten` [{text, richtig}]
- mc: Auswahl, mehrere richtig → `antworten`
- kprim: genau 4 Aussagen, die im PDF je einzeln als richtig ODER falsch zu beurteilen sind (Spalten
  «richtig/falsch», «R/F», «trifft zu») → `aussagen` [{text, richtig}]. Bei genau 4 solchen Aussagen immer kprim,
  nie matchtruefalse. Eine Auswahlfrage mit Ankreuzkästchen A–D («Welche … sind korrekt?») bleibt sc/mc,
  auch wenn sie 4 Optionen hat.
- matchtruefalse: richtig/falsch-Aussagen, deren Anzahl NICHT 4 ist → `aussagen`
- match: Zuordnung in einer Tabelle/Matrix → `zeilen`, `spalten`, `zuordnung` [{zeile, spalte}]
  (Texte in `zuordnung` exakt wie in `zeilen`/`spalten`); matchdraganddrop, wenn Begriffe in Kategorien sortiert werden
- order: Reihenfolge → `elemente` in der RICHTIGEN Reihenfolge
- Rechenaufgabe mit einem eindeutigen Zahlenergebnis («Berechnen Sie …») OHNE Antwortoptionen zum Ankreuzen
  → numerical, auch wenn die Lösung einen Rechenweg zeigt. Stehen im PDF Optionen A–D zum Ankreuzen, bleibt sie
  sc/mc — die Form im PDF geht vor. Für numerical: `frage` = Aufgabe, `text` = Antwortsatz mit Lücke, z. B. «p2 = {{#3±0.05}} bar».
  Toleranz aus dem PDF; fehlt sie, ±1 % des Ergebnisses. Nur wenn das PDF ausdrücklich Punkte für den
  Rechenweg vergibt, oder die Aufgabe zusätzlich eine Erklärung verlangt: essay mit Musterlösung.
- essay: offene Frage → `frage`, `musterloesung` = Lösung aus dem PDF, `antwortzeilen` = Linienzahl im PDF oder
  geschätzt; `hinweis` nur, wenn das PDF einen Tipp für Lernende enthält
- upload: Abgabe einer Datei → `frage`
- Lückentexte → `text` mit Lücken-Markup, Einleitung in `frage`:
    fib           Texteingabe: {{Lösung|Variante2}} — alle im PDF genannten Varianten
    numerical     Zahl: {{#26}} oder mit Toleranz {{#200±2}} — Dezimalkomma oder -punkt, aber nie Leerzeichen
                  oder Tausender-Trennzeichen in der Lücke ({{#101300±100}}, nicht {{#101 300}})
    inlinechoice  Auswahl in der Lücke: {{*richtig|falsch1|falsch2}} — * vor der richtigen. Steht die Auswahl im
                  PDF in Klammern («(steigt / sinkt)»), wird die Klammer samt Inhalt zur Lücke — ohne Klammern.
    gapmixed      verschiedene Lückenarten gemischt
  Eine Frage mit Zahl- oder Kurzantwort OHNE Lücke im PDF («Antwort in klx», «Nennen Sie den Fachbegriff»)
  wird trotzdem ein Lückentyp: `frage` = die Frage, `text` = ein kurzer Antwortsatz mit genau einer Lücke,
  z. B. «Antwort: {{#20±2}} klx» oder «Fachbegriff: {{Chlorophyll}}». Die Toleranz aus der Lösung ableiten
  («akzeptiert: 18 bis 22» → {{#20±2}}). Bei allen Lückentypen darf `text` nie null sein.
- hottext: Wörter im Text anklicken → `text` mit [[Wort]], richtige [[*Wort]]

VIDEO UND AUDIO
- Steht bei einer Frage ein Link auf ein YouTube-Video (youtube.com/watch?v=…, youtu.be/…), ein nanoo.tv-Video
  (nanoo.tv/link/v/…) oder eine mp3-Datei (URL endet auf .mp3), gehört er in `medien` dieser Frage — OLAT bettet
  ihn dann als Player ein.
  Die URL vollständig und unverändert übernehmen, den Link-Text aus der Frage weglassen
  (z. B. «Video: https://…» oder «Hören Sie hier»).
- Links, die im PDF hinter einem Wort liegen, stehen am Seitenende unter «Links auf dieser Seite»
  mit dem Wort, hinter dem sie liegen — so ordnest du sie der richtigen Frage zu.
- Andere Links (Webseiten, Dokumente) nicht in `medien`, sondern im Fragetext lassen.
- Keine Medien-Links erfinden; ohne Link `medien` = null.

{format}FORMELN
- JEDE Formel und jede Formelgrösse mit Index wird LaTeX zwischen Dollarzeichen — in allen Texten, auch im
  `text` von Lückentypen (nur nicht in der Lücke selbst). Im PDF stehen sie meist als Klartext; so setzt du sie um:
    «p1 · V1 = p2 · V2»        → $p_1 \\cdot V_1 = p_2 \\cdot V_2$
    «p / T = konstant»         → $\\frac{p}{T} = \\text{konstant}$
    «V2» im Fliesstext         → $V_2$
    «R = 8,314 J/(mol · K)»    → $R = 8{,}314\\,\\frac{\\text{J}}{\\text{mol} \\cdot \\text{K}}$
    «V1 = 6 L»                 → $V_1 = 6\\,\\text{L}$
  Zahlen mit Einheit ohne Formelzeichen («22 °C», «3 bar» allein) bleiben Text.
- In einer Lücke {{…}} nie LaTeX: «$p_2$ = {{#3±0.05}} bar» ist richtig.
- Jeden Backslash in LaTeX genau EINMAL schreiben: \\cdot, nicht \\\\cdot.
- Ein echtes Dollarzeichen als \\$ schreiben."""


# Zwei Stufen (23.09.2026): «einfach» wie bisher bewährt, «erweitert» auf Wunsch der Lehrperson
# für Texte mit Zeilennummern, Tabellen, Zwischentitel. Der Konverter versteht beides.
FORMAT_EINFACH = """FORMAT IN TEXTEN
Der PDF-Text kommt mit seiner Formatierung: **fett**, *kursiv*, «- » vor Aufzählungspunkten.
- Die Marker **…** und *…* im PDF-Text sind echte Hervorhebungen des PDFs: in allen Texten mitkopieren,
  genau wo sie stehen (z. B. «**nicht**», ein kursives Zitat, eine fette Frage im Interview).
  Weglassen nur bei Fettdruck, der zum Layout gehört — Fragenummern («**S1a)**»), Punktangaben,
  Kopf- und Fusszeilen. Ein Zwischentitel bleibt ein eigener Absatz in **fett**.
- Aufzählungen: jeder Punkt eine Zeile mit «- » (nummeriert: «1. »), umbrochene Punkte zu einer Zeile verbinden.
- Absätze durch eine Leerzeile trennen. Zeilen des PDFs innerhalb eines Absatzes zu Fliesstext verbinden —
  ausser bei einem Text mit Zeilennummern: dort bleibt jede Zeile eine eigene Zeile, mit ihrer Nummer vorne.
- Tabellen mit Inhalt als Aufzählung übertragen: je Tabellenzeile ein Punkt «- Zelle: Zelle, Zelle».
  Ankreuztabellen (richtig/falsch, Zuordnung) werden der passende Fragetyp.
- Ein echtes Sternchen als \\* schreiben.
- Jede Stelle des PDFs genau einmal: keinen Satz zusätzlich als Titel oder eigenen Absatz wiederholen.

"""

FORMAT_ERWEITERT = """FORMAT IN TEXTEN (Markdown)
Der PDF-Text kommt mit seiner Formatierung: **fett**, *kursiv*, «- » vor Aufzählungspunkten, Tabellen als
| Zelle | Zelle |. Übernimm die Formatierung in alle Texte (`frage`, Antworten, Aussagen, `text`, `hinweis`,
`musterloesung`) — sie ist Teil des Wortlauts:
- **fett** und *kursiv* genau dort, wo sie im PDF stehen (z. B. hervorgehobene Wörter wie «**nicht**»).
  Nicht übernehmen: Fettdruck, der nur zum Layout gehört — Fragenummern («**S1a)**»), Punktangaben
  («**(2 Punkte)**»), Kopf- und Fusszeilen, Tabellenköpfe von Ankreuztabellen.
- Zwischentitel (eine fett gesetzte Zeile, die allein steht und einen Text oder Abschnitt einleitet, z. B.
  «Die Situation» oder der Titel eines Zeitungstexts) als eigene Zeile «### Titel», ohne ** darum.
- Absätze durch eine Leerzeile trennen. Innerhalb eines Absatzes Zeilen des PDFs zu Fliesstext verbinden —
  AUSSER bei Texten mit Zeilennummern, Gedichten, Liedtexten, Adressen, Dialogen: dort bleibt jede Zeile
  eine eigene Zeile, genau wie im PDF, mit der Zeilennummer am Zeilenanfang («1 Was ist …»); Fragen verweisen
  auf diese Zeilen. Eine andere einzelne Zeile, die umbrechen soll, endet mit «\\».
- Aufzählungen: jeder Punkt eine Zeile mit «- » (nummeriert: «1. »), über mehrere PDF-Zeilen umbrochene
  Punkte zu einer Zeile verbinden.
- Tabellen mit Inhalt (Werte, Angaben) als Markdown-Tabelle übernehmen: | Kopf | Kopf |, |---|---|,
  | Zelle | Zelle |. Jede Tabellenzeile auf einer Zeile, jede Zeile mit gleich vielen Zellen; leere Zelle = | |.
  Ohne Kopfzeile im PDF die Zeile |---|---| weglassen. Ankreuztabellen (richtig/falsch, Zuordnung) werden der
  passende Fragetyp, keine Tabelle. Eine Tabelle, die Lernende ausfüllen sollen, als leere Tabelle in `frage`.
- Ein echtes Sternchen als \\* schreiben.
- Jede Stelle des PDFs genau einmal: keinen Satz zusätzlich als Titel oder eigenen Absatz wiederholen.

"""

SYSTEM = SYSTEM_VORLAGE.replace("{format}", FORMAT_EINFACH)
SYSTEM_ERWEITERT = SYSTEM_VORLAGE.replace("{format}", FORMAT_ERWEITERT)


SCAN_ZUSATZ = """

SEITEN ALS BILD
Einige Seiten liegen zusätzlich oder nur als Bild vor (Scan, Foto, eingefügte Grafik) — jeweils
angekündigt mit «Seite n als Bild». Lies sie genauso wie den Text und übertrage die Fragen darauf.
Steht eine Seite als Text UND als Bild da, gilt der Text; das Bild ergänzt nur, was im Text fehlt —
keine Frage doppelt übertragen. Unleserliche oder abgeschnittene Stellen: nicht raten, sondern im Feld
`unsicher` benennen. In `quelle` bei solchen Fragen «(Bild)» anfügen, z. B. «S. 3 (Bild), Aufgabe 5»."""

BILD_ZUSATZ = """

BILDER IM TEXT
Im Text steht an der Stelle jedes Bildes eine Marke «[Bild: s1_bild1.png]». Ordne jedes Bild der Frage zu,
zu der es gehört — meist steht es direkt unter oder über dem Fragetext, oder die Frage verweist darauf
(«im Diagramm», «Abbildung», «Schema»). Trage es in `bilder` dieser Frage ein: `datei` = der Name aus der
Marke, genau so; `alt` = kurze sachliche Beschreibung des Bildinhalts für Screenreader (5–12 Wörter), ohne
die Lösung zu verraten. Ein Bild gehört zu einer weiteren Frage nur, wenn diese ausdrücklich darauf
verweist («im Diagramm», «der Abbildung») oder ohne das Bild nicht beantwortbar ist — dann bei jeder dieser
Fragen eintragen.
Bilder, die zu keiner Frage gehören (Logo, Dekoration), weglassen. Keine Dateinamen erfinden.
Ohne Bild `bilder` = null. Die Marken selbst nie in Fragetexte übernehmen."""

MIN_TEXT = 50          # Zeichen: darunter gilt eine Seite als «ohne Text»
BILD_ANTEIL = 0.3      # Bildfläche/Seitenfläche, ab der eine textarme Seite als Bild mitgeht
TEXTARM = 400          # Zeichen: darunter ist eine Seite mit grossem Bild «textarm»
MAX_BILDSEITEN = 20
DPI = 150


def _linkliste(s) -> str:
    """Links hinter Wörtern stehen nicht im Text — mit Ankertext anhängen, damit das Modell sie zuordnen kann."""
    links = []
    for l in s.get_links():
        if l.get("uri"):
            anker = " ".join(s.get_textbox(l["from"]).split())
            links.append(f"- {l['uri']}" if anker in ("", l["uri"]) else f"- {anker}: {l['uri']}")
    return "\nLinks auf dieser Seite:\n" + "\n".join(dict.fromkeys(links)) + "\n" if links else ""


def analysiere_pdf(daten: bytes) -> list[dict]:
    """Je Seite: nr, text, zeichen, bild_anteil, art ∈ {text, ohne_text, bild_mit_wenig_text}."""
    seiten = []
    with pymupdf.open(stream=daten, filetype="pdf") as doc:
        for i, s in enumerate(doc, 1):
            text = s.get_text()
            zeichen = len("".join(text.split()))  # vor den Links zählen: sie machen aus einem Scan keine Textseite
            text += _linkliste(s)
            flaeche = abs(s.rect) or 1
            bilder = sum(abs(pymupdf.Rect(b["bbox"]) & s.rect) for b in s.get_image_info())
            anteil = min(bilder / flaeche, 1.0)
            if zeichen < MIN_TEXT:
                art = "ohne_text"
            elif anteil >= BILD_ANTEIL and zeichen < TEXTARM:
                art = "bild_mit_wenig_text"
            else:
                art = "text"
            seiten.append({"nr": i, "text": text, "zeichen": zeichen, "bild_anteil": round(anteil, 2), "art": art})
    return seiten


MIN_BILD_PX = 80  # kleinere Bilder sind Symbole, Aufzählungszeichen, Ankreuzkästchen


def bilder_aus_pdf(daten: bytes) -> list[dict]:
    """Eingebettete Bilder je Seite, in Leserichtung: {seite, name, daten, ext, breite, hoehe, oben}.

    Ausgelassen: Bilder unter MIN_BILD_PX und Bilder, die auf mehr als der Hälfte der Seiten
    (mind. 2) vorkommen — Logos und Kopfzeilen. Gleiche Bilder auf einer Seite nur einmal."""
    import hashlib
    funde, vorkommen = [], {}
    with pymupdf.open(stream=daten, filetype="pdf") as doc:
        seiten = doc.page_count
        for nr, s in enumerate(doc, 1):
            gesehen = set()
            bloecke = [b for b in s.get_text("dict")["blocks"] if b.get("type") == 1]
            for b in sorted(bloecke, key=lambda b: (round(b["bbox"][1]), b["bbox"][0])):
                roh, ext = b["image"], b.get("ext", "png")
                if b["width"] < MIN_BILD_PX or b["height"] < MIN_BILD_PX:
                    continue
                if abs(pymupdf.Rect(b["bbox"]) & s.rect) > 0.8 * abs(s.rect):
                    continue  # ganze Seite als Bild = Scan; läuft über seiten_als_bild()
                h = hashlib.sha1(roh).hexdigest()
                if h in gesehen:
                    continue
                gesehen.add(h)
                vorkommen[h] = vorkommen.get(h, 0) + 1
                if ext not in ("png", "jpeg", "jpg", "gif"):
                    roh, ext = pymupdf.Pixmap(roh).tobytes("png"), "png"  # z. B. jpx, tiff
                funde.append({"seite": nr, "daten": roh, "ext": "jpg" if ext == "jpeg" else ext, "hash": h,
                              "breite": b["width"], "hoehe": b["height"], "oben": round(b["bbox"][1])})
    wiederkehrend = {h for h, n in vorkommen.items() if seiten > 1 and n >= 2 and n > seiten / 2}
    funde = [f for f in funde if f["hash"] not in wiederkehrend]
    zaehler: dict[int, int] = {}
    for f in funde:
        zaehler[f["seite"]] = zaehler.get(f["seite"], 0) + 1
        f["name"] = f"s{f['seite']}_bild{zaehler[f['seite']]}.{f['ext']}"
    return funde


FETT = re.compile(r"bold|black|heavy|semibold|demi", re.I)
KURSIV = re.compile(r"italic|oblique", re.I)


def _stil(sp: dict) -> tuple[bool, bool]:
    """(fett, kursiv) — aus den Flags oder, wo das PDF sie nicht setzt, aus dem Schriftnamen (Arial-Black)."""
    return (bool(sp["flags"] & 16 or FETT.search(sp["font"])),
            bool(sp["flags"] & 2 or KURSIV.search(sp["font"])))


def _markiert(spans: list[dict]) -> str:
    """Spans einer Zeile -> Text mit **fett** und *kursiv*; gleiche Stile werden zusammengefasst."""
    gruppen: list[list] = []
    for sp in spans:
        stil = _stil(sp) if sp["text"].strip() else None
        if gruppen and (stil is None or gruppen[-1][0] == stil):
            gruppen[-1][1] += sp["text"]
        else:
            gruppen.append([stil, sp["text"]])
    out = ""
    for stil, t in gruppen:
        m = {(True, True): "***", (True, False): "**", (False, True): "*"}.get(stil or (False, False), "")
        kern = t.strip()
        if not m or not kern:
            out += t
            continue
        out += t[:len(t) - len(t.lstrip())] + m + kern + m + t[len(t.rstrip()):]
    return out


def _punkte(s) -> list:
    """Gezeichnete Aufzählungspunkte (kleine gefüllte Kreise/Quadrate) — sie stehen nicht im Text."""
    return [d["rect"] for d in s.get_drawings()
            if d.get("fill") and d["rect"].width <= 8 and d["rect"].height <= 8
            and abs(d["rect"].width - d["rect"].height) < 2]


def _zeilen(block: dict, punkte: list) -> list[str]:
    """Zeilen eines Textblocks. Teile auf gleicher Höhe werden nach x sortiert zu einer Zeile —
    sonst landet eine Zeilennummer am Rand hinter ihrer Zeile statt davor (23.09.2026)."""
    gruppen: list[list[dict]] = []
    for l in sorted(block.get("lines", []), key=lambda l: l["bbox"][1]):
        y0, y1 = l["bbox"][1], l["bbox"][3]
        if gruppen:
            g0, g1 = min(x["bbox"][1] for x in gruppen[-1]), max(x["bbox"][3] for x in gruppen[-1])
            if min(y1, g1) - max(y0, g0) > 0.5 * min(y1 - y0, g1 - g0):
                gruppen[-1].append(l)
                continue
        gruppen.append([l])
    out = []
    for g in gruppen:
        g.sort(key=lambda l: l["bbox"][0])
        text = " ".join(_markiert(l["spans"]).strip() for l in g if "".join(sp["text"] for sp in l["spans"]).strip())
        if not text:
            continue
        x0, y0, y1 = g[0]["bbox"][0], min(l["bbox"][1] for l in g), max(l["bbox"][3] for l in g)
        if any(0 <= x0 - r.x1 < 15 and y0 <= (r.y0 + r.y1) / 2 <= y1 for r in punkte):
            text = "- " + text
        out.append(text)
    return out


def _tabellen(s) -> list[tuple]:
    """Tabellen mit mind. 2×2 Zellen als (Rechteck, Markdown) — ein Rahmen um eine Frage ist keine Tabelle."""
    try:
        gefunden = s.find_tables().tables
    except Exception:  # Tabellensuche ist Zugabe, darf die Umwandlung nie stoppen
        return []
    return [(pymupdf.Rect(t.bbox), t.to_markdown().replace("<br>", " ").strip())
            for t in gefunden if t.row_count >= 2 and t.col_count >= 2]


def seitentext(s, name_zu: dict | None = None, nr: int = 0) -> str:
    """Text einer Seite in Leserichtung mit Formatierung als Markdown — **fett**, *kursiv*,
    - Aufzählung, | Tabelle | — und an jeder Bildstelle «[Bild: name]»."""
    import hashlib
    punkte, tabellen = _punkte(s), _tabellen(s)
    gesetzt: set[int] = set()
    zeilen = []
    for b in s.get_text("dict", sort=True)["blocks"]:
        x0, y0, x1, y1 = b["bbox"]
        mitte = pymupdf.Point((x0 + x1) / 2, (y0 + y1) / 2)
        drin = next((i for i, (r, _) in enumerate(tabellen) if mitte in r), None)
        if drin is not None:
            if drin not in gesetzt:
                gesetzt.add(drin)
                zeilen += ["", tabellen[drin][1], ""]
            continue
        if b.get("type") == 1:
            name = (name_zu or {}).get((nr, hashlib.sha1(b["image"]).hexdigest()))
            if name:
                zeilen.append(f"[Bild: {name}]")
        else:
            zeilen += _zeilen(b, punkte)
    return "\n".join(zeilen)


def pdf_text_mit_bildern(daten: bytes, funde: list[dict]) -> str:
    """Seitentext mit Formatierung, an jeder Bildstelle «[Bild: name]» — so ordnet das Modell zu."""
    name_zu = {(f["seite"], f["hash"]): f["name"] for f in funde}
    teile = []
    with pymupdf.open(stream=daten, filetype="pdf") as doc:
        for nr, s in enumerate(doc, 1):
            teile.append(f"--- Seite {nr} ---\n{seitentext(s, name_zu, nr)}\n{_linkliste(s)}")
    return "\n".join(teile)


def seiten_als_bild(daten: bytes, nummern: list[int]) -> list[tuple[int, bytes]]:
    """Gerenderte PNGs der genannten Seiten (1-basiert)."""
    with pymupdf.open(stream=daten, filetype="pdf") as doc:
        return [(n, doc[n - 1].get_pixmap(dpi=DPI).tobytes("png")) for n in nummern]


def pdf_text(daten: bytes) -> tuple[str, int]:
    """Text aller Seiten mit Seitenmarken und Formatierung; zweiter Wert = Seitenzahl."""
    with pymupdf.open(stream=daten, filetype="pdf") as doc:
        anzahl = doc.page_count
    return pdf_text_mit_bildern(daten, []), anzahl


def nachricht(text: str, bilder: list[tuple[int, bytes]]) -> str | list[dict]:
    """User-Nachricht: nur Text, oder Text + Seitenbilder (OpenAI-Bildeingabe)."""
    if not bilder:
        return text
    teile: list[dict] = [{"type": "text", "text": text}]
    for n, png in bilder:
        teile.append({"type": "text", "text": f"--- Seite {n} als Bild ---"})
        teile.append({"type": "image_url", "image_url": {
            "url": "data:image/png;base64," + base64.b64encode(png).decode(), "detail": "high"}})
    return teile


def frage_openai(client, modell: str, text: str, bilder: list[tuple[int, bytes]] | None = None,
                 erweitert: bool = False) -> tuple[dict, dict]:
    antwort = client.chat.completions.create(
        model=modell,
        messages=[{"role": "system", "content": (SYSTEM_ERWEITERT if erweitert else SYSTEM) + (SCAN_ZUSATZ if bilder else "")
                   + (BILD_ZUSATZ if "[Bild: " in text else "")},
                  {"role": "user", "content": nachricht(text, bilder or [])}],
        response_format={"type": "json_schema",
                         "json_schema": {"name": "olat_test", "strict": True, "schema": SCHEMA}},
    )
    wahl = antwort.choices[0]
    if wahl.finish_reason == "length":
        raise RuntimeError("Antwort abgeschnitten — das PDF ist zu lang für einen Durchgang.")
    if getattr(wahl.message, "refusal", None):
        raise RuntimeError(f"Modell verweigert: {wahl.message.refusal}")
    u = antwort.usage
    return json.loads(wahl.message.content), {"eingabe": u.prompt_tokens, "ausgabe": u.completion_tokens}


def zu_fragensatz(roh: dict, erweitert: bool = False) -> dict:
    """JSON aus dem Modell -> Fragensatz im YAML-Format von olatqti.py (immer mit `sektionen`)."""
    sektionen = [{"titel": s["titel"], "fragen": [_frage(q, erweitert) for q in s["fragen"]]}
                 for s in roh["sektionen"] if s["fragen"]]
    satz = {"titel": roh["titel"], "sektionen": sektionen}
    if roh.get("uebersprungen"):
        satz["uebersprungen"] = roh["uebersprungen"]
    return satz


def alle_fragen(satz: dict) -> list[tuple[str, dict]]:
    """(Sektionstitel, Frage) über alle Sektionen — auch für Sätze ohne `sektionen`."""
    if "sektionen" in satz:
        return [(s.get("titel", ""), f) for s in satz["sektionen"] or [] for f in s.get("fragen") or []]
    return [("", f) for f in satz.get("fragen") or []]


STEUERZEICHEN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _saeubern(o):
    """Verstümmelte Zeichen (Steuerzeichen statt Umlaut/Strich) sichtbar als □ markieren."""
    if isinstance(o, str):
        return STEUERZEICHEN.sub("□", o)
    if isinstance(o, list):
        return [_saeubern(x) for x in o]
    if isinstance(o, dict):
        return {k: _saeubern(v) for k, v in o.items()}
    return o


MATHE = re.compile(r"(?<!\\)\$[^$\n]+?(?<!\\)\$")
DOPPELT = re.compile(r"\\\\(?=[A-Za-z,;:!{}|])")


def _latex_reparieren(o):
    r"""In $…$: «\\cdot» → «\cdot». gpt-5.6-luna schreibt im JSON-Modus Backslashes teils doppelt
    (22.09.2026); in OLAT würde daraus ein Zeilenumbruch plus Text. Echte Zeilenumbrüche «\\ »
    (Backslash-Backslash-Leerzeichen) bleiben."""
    if isinstance(o, str):
        return MATHE.sub(lambda m: DOPPELT.sub(lambda _: "\\", m[0]), o)
    if isinstance(o, list):
        return [_latex_reparieren(x) for x in o]
    if isinstance(o, dict):
        return {k: _latex_reparieren(v) for k, v in o.items()}
    return o


ALLEIN_FETT = re.compile(r"\*\*([^*\n]{1,80}?)\*\*")


def _zwischentitel(text: str | None) -> str | None:
    """Ein Absatz, der nur aus einer kurzen fetten Zeile besteht («**Die Situation**»), wird «### …» —
    das Modell lässt die Fettung oft stehen, statt einen Titel zu setzen (23.09.2026)."""
    if not text:
        return text
    absaetze = re.split(r"(\n\s*\n)", text)
    for i, a in enumerate(absaetze):
        m = ALLEIN_FETT.fullmatch(a.strip())
        if m and not m[1].rstrip().endswith((".", ":", "!", "?")):
            absaetze[i] = f"### {m[1].strip()}"
    return "".join(absaetze)


def _norm(absatz: str) -> str:
    """Absatz ohne Marker, Zeilennummern und Leerraum — zum Vergleichen."""
    zeilen = [re.sub(r"^\d{1,3}\s+", "", z.strip()) for z in absatz.splitlines()]
    return " ".join(re.sub(r"[*#]", " ", " ".join(zeilen)).split())


def _ohne_doppel(text: str | None) -> str | None:
    """Entfernt Absätze, deren Text schon in einem anderen Absatz steht — gpt-5.6-luna setzte eine fette
    Interviewfrage zusätzlich als eigenen Absatz vor die nummerierten Zeilen, die sie schon enthielten (23.09.2026)."""
    if not text:
        return text
    absaetze = [a for a in re.split(r"\n\s*\n", text) if a.strip()]
    norm = [_norm(a) for a in absaetze]
    # nur gegen Texte mit Zeilennummern prüfen: ein Titel, der in der Quellenangabe wiederkehrt, bleibt
    nummeriert = [len(z := a.strip().splitlines()) > 1 and all(re.match(r"\d{1,3}\s", x.strip()) for x in z)
                  for a in absaetze]
    weg = {i for i, n in enumerate(norm) if len(n) >= 20 and not nummeriert[i]
           and any(j != i and nummeriert[j] and n in m for j, m in enumerate(norm))}
    return "\n\n".join(a for i, a in enumerate(absaetze) if i not in weg)


def _frage(q: dict, erweitert: bool = False) -> dict:
    q = _latex_reparieren(q)
    q["frage"] = _ohne_doppel(q.get("frage"))
    if erweitert:
        q["frage"] = _zwischentitel(q.get("frage"))
    sauber = _saeubern(q)
    if sauber != q:
        q = sauber
        hinweis = "Zeichensalat vom Modell: □ steht für ein verlorenes Zeichen (meist Umlaut oder «–»)"
        q["unsicher"] = f"{q['unsicher']} · {hinweis}" if q.get("unsicher") else hinweis
    typ = q["typ"]
    if typ in ("fib", "numerical", "inlinechoice", "gapmixed", "hottext") and not q.get("text"):
        # Modell hat den Lückentyp gewählt, aber keine Lücke geliefert (gpt-5.6-luna, 22.09.2026):
        # als Freitext übernehmen statt das ganze Zip scheitern zu lassen
        hinweis = f"{typ} ohne Lückentext geliefert — als Freitext übernommen, Typ bitte prüfen"
        q = {**q, "typ": "essay", "unsicher": f"{q['unsicher']} · {hinweis}" if q.get("unsicher") else hinweis}
        typ = "essay"
    f = {"typ": typ, "titel": q["titel"], "punkte": q["punkte"]}
    if q.get("frage"):
        f["frage"] = q["frage"]
    if typ in ("sc", "mc"):
        f["antworten"] = q["antworten"] or []
    elif typ in ("kprim", "matchtruefalse"):
        f["aussagen"] = q["aussagen"] or []
    elif typ in ("match", "matchdraganddrop"):
        f["zeilen"], f["spalten"] = q["zeilen"] or [], q["spalten"] or []
        f["loesung"] = [[z["zeile"], z["spalte"]] for z in q["zuordnung"] or []]
    elif typ in ("fib", "numerical", "inlinechoice", "gapmixed", "hottext"):
        f["text"] = q["text"] or ""
    elif typ == "order":
        f["elemente"] = q["elemente"] or []
    elif typ == "essay":
        if q.get("antwortzeilen"):
            f["zeilen"] = q["antwortzeilen"]
        for feld in ("hinweis", "musterloesung"):
            if q.get(feld):
                f[feld] = q[feld]
    # Notizfelder: ignoriert der Konverter, landen nie in OLAT
    if q.get("bilder"):
        f["bilder"] = [{"datei": f"bilder/{b['datei']}", "alt": b["alt"]} for b in q["bilder"]]
    if q.get("medien"):
        f["medien"] = q["medien"]
    for feld in ("quelle", "unsicher"):
        if q.get(feld):
            f[feld] = q[feld]
    return f


# USD pro 1 Million Tokens (Eingabe, Ausgabe) — Stand 22.09.2026, Angaben von Pietro.
# Bei Preisänderung nur hier anpassen; die App rechnet damit nach jeder Umwandlung.
PREISE = {
    "gpt-5.6-luna": (0.20, 1.20),
}


def kosten(verbrauch: dict, modell: str) -> float | None:
    """Kosten einer Umwandlung in USD aus den Tokenzahlen; None, wenn das Modell keinen Preis hat."""
    if modell not in PREISE:
        return None
    ein, aus = PREISE[modell]
    return (verbrauch["eingabe"] * ein + verbrauch["ausgabe"] * aus) / 1_000_000


def pruefe_medien(satz: dict, pdf_text: str) -> int:
    """Markiert Fragen, deren Medien-URL nicht wörtlich im PDF steht (verändert oder erfunden)."""
    markiert = 0
    for _, f in alle_fragen(satz):
        fremd = [u for u in f.get("medien") or [] if isinstance(u, str) and u not in pdf_text]
        if fremd:
            hinweis = f"Medien-Link steht so nicht im PDF: {', '.join(fremd)}"
            f["unsicher"] = f"{f['unsicher']} · {hinweis}" if f.get("unsicher") else hinweis
            markiert += 1
    return markiert


def pruefe_bilder(satz: dict, namen: set[str]) -> list[str]:
    """Entfernt Bilder mit unbekanntem Namen (markiert die Frage); gibt nicht zugeordnete Bilder zurück."""
    benutzt = set()
    for _, f in alle_fragen(satz):
        gut, fremd = [], []
        for b in f.get("bilder") or []:
            name = b["datei"].removeprefix("bilder/")
            (gut if name in namen else fremd).append(b)
            benutzt.add(name)
        if fremd:
            hinweis = f"Bild nicht im PDF: {', '.join(b['datei'] for b in fremd)} — entfernt"
            f["unsicher"] = f"{f['unsicher']} · {hinweis}" if f.get("unsicher") else hinweis
        if gut:
            f["bilder"] = gut
        else:
            f.pop("bilder", None)
    return sorted(namen - benutzt)


def als_yaml(satz: dict) -> str:
    """Fragensatz als YAML; mehrzeilige Texte als |-Block, damit Zeilen und Absätze lesbar bleiben."""
    import yaml

    class Dumper(yaml.SafeDumper):
        pass

    def text(d, s):
        s = "\n".join(z.rstrip() for z in s.split("\n")) if "\n" in s else s
        return d.represent_scalar("tag:yaml.org,2002:str", s, style="|" if "\n" in s else None)
    Dumper.add_representer(str, text)
    return yaml.dump(satz, Dumper=Dumper, allow_unicode=True, sort_keys=False, width=100)


def yaml_aus_antwort(antwort: str) -> str:
    """YAML aus einer KI-Antwort: Inhalt des (ersten) Codeblocks, sonst der ganze Text."""
    m = re.search(r"```(?:ya?ml)?[ \t]*\r?\n(.*?)```", antwort or "", re.S)
    return (m[1] if m else antwort or "").strip() + "\n"


def dateiname(titel: str) -> str:
    """«Werkstoffe – Lernkontrolle» -> «werkstoffe-lernkontrolle»."""
    t = str(titel).lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:60] or "test"


def loesung_kurz(f: dict) -> str:
    """Eine Zeile «richtige Lösung» für die Prüftabelle."""
    t = f.get("typ")
    if t in ("sc", "mc"):
        return " · ".join(a["text"] for a in f.get("antworten", []) if isinstance(a, dict) and a.get("richtig"))
    if t in ("kprim", "matchtruefalse"):
        return " · ".join(("✓ " if a.get("richtig") else "✗ ") + a["text"] for a in f.get("aussagen", []))
    if t in ("match", "matchdraganddrop"):
        l = f.get("loesung", [])
        paare = l.items() if isinstance(l, dict) else l
        return " · ".join(f"{z} → {s}" for z, s in paare)
    if t == "order":
        return " → ".join(f.get("elemente", []))
    if t == "essay":
        return (f.get("musterloesung") or "— keine Musterlösung —")[:160]
    if t == "upload":
        return "— Datei-Abgabe, Bewertung durch Lehrperson —"
    return f.get("text", "")[:160]
