Du hilfst mir, einen Test für OLAT vorzubereiten. Gib den Test im YAML-Format unten aus.
Meine Fragen (oder mein Material) folgen am Ende dieser Nachricht.

## Auftrag

- Liegen Fragen mit Lösungen vor: **übertrage sie wörtlich**. Nichts kürzen, nichts umformulieren,
  keine Distraktoren, Hinweise oder Lösungen dazuerfinden.
- Liegt nur Material vor und ich bitte um neue Fragen: erstelle sie aus dem Material. Jede Frage
  prüft etwas Konkretes aus dem Material; Distraktoren plausibel, gleich lang, aus typischen
  Fehlvorstellungen; kein «alle oben genannten»; Multiple Choice mit 2–3 richtigen von 4.
- Schweizer Rechtschreibung: «ss», nie «ß».
- **Video und Audio:** Steht bei einer Frage ein Link auf YouTube, nanoo.tv (nanoo.tv/link/v/…) oder eine
  mp3-Datei, übernimm
  ihn vollständig und unverändert in `medien:` dieser Frage (siehe A1 im Beispiel) — OLAT zeigt ihn als
  Player unter dem Fragetext. Andere Links bleiben im Fragetext. Keine Links erfinden.
- Fehlt eine Lösung oder ist etwas unklar: trotzdem übertragen und in `unsicher:` einen Satz dazu
  schreiben. Dieses Feld erscheint nicht in OLAT, nur in meiner Kontrolle.
- **Gib ausschliesslich YAML aus, in einem einzigen Codeblock, ohne Text davor oder danach.**

## Format

```yaml
titel: Werkstoffe – Lernkontrolle
sektionen:                      # Teile des Tests; ohne Gliederung genau eine Sektion «Fragen»
  - titel: Teil A – Single Choice
    fragen:
      - typ: sc                 # genau eine richtige Antwort
        titel: A1 Dichte        # kurzer Fragetitel mit Nummer
        punkte: 1
        frage: Welche Aussage beschreibt die Dichte korrekt?
        # medien: ["https://www.youtube.com/watch?v=…"]   # nur wenn ich einen Link angebe: Video/mp3 als Player
        antworten:
          - {text: "Masse eines Werkstoffs pro Volumen", richtig: true}
          - {text: "Widerstand gegen mechanische Belastung", richtig: false}
          - {text: "Temperatur, bei der ein Werkstoff flüssig wird", richtig: false}

      - typ: mc                 # mehrere richtige Antworten
        titel: A2 Leichtmetalle
        punkte: 2
        frage: Welche Metalle sind Leichtmetalle?
        antworten:
          - {text: "Aluminium", richtig: true}
          - {text: "Titan", richtig: true}
          - {text: "Kupfer", richtig: false}
          - {text: "Blei", richtig: false}

      - typ: kprim              # genau 4 Aussagen, je richtig oder falsch
        titel: A3 Stahl
        punkte: 2
        frage: Beurteilen Sie die Aussagen.
        aussagen:
          - {text: "Stahl enthält weniger als 2,06 % Kohlenstoff.", richtig: true}
          - {text: "Stahl ist in der Regel nicht umformbar.", richtig: false}
          - {text: "Baustahl ist gut kaltumformbar.", richtig: true}
          - {text: "Stahl ist ein Leichtmetall.", richtig: false}

      - typ: richtigfalsch      # beliebig viele Aussagen, je richtig oder falsch
        titel: A4 Gusseisen
        punkte: 1
        frage: Richtig oder falsch?
        aussagen:
          - {text: "Gusseisen ist spröde.", richtig: true}
          - {text: "Gusseisen ist gut schmiedbar.", richtig: false}

      - typ: matrix             # Tabelle zum Ankreuzen: Zeile → Spalte
        titel: A5 Werkstoffgruppen
        punkte: 2
        frage: Ordnen Sie zu. Ein Werkstoff kann zu mehreren Gruppen gehören.
        zeilen: [Aluminium, Kupfer]
        spalten: [Leichtmetall, Schwermetall, Nichteisenmetall]
        loesung:                # eine Spalte oder eine Liste von Spalten pro Zeile
          Aluminium: [Leichtmetall, Nichteisenmetall]
          Kupfer: [Schwermetall, Nichteisenmetall]

      - typ: dragdrop           # Begriffe in Kategorien ziehen — gleiche Felder wie matrix
        titel: A5b Beispiele zuordnen
        punkte: 2
        frage: Ziehen Sie die Werkstoffe in die passende Gruppe.
        zeilen: [Baustahl, Polyethylen]
        spalten: [Eisenwerkstoff, Kunststoff]
        loesung: {Baustahl: Eisenwerkstoff, Polyethylen: Kunststoff}

      - typ: reihenfolge        # Elemente in der RICHTIGEN Reihenfolge
        titel: A6 Fertigung
        punkte: 1
        frage: Bringen Sie die Schritte in die richtige Reihenfolge.
        elemente: [Halbzeug zuschneiden, Zerspanen, Biegen]

  - titel: Teil B – Lücken
    fragen:
      - typ: lueckentext        # {{Lösung|Variante}} — jede Variante gilt
        titel: B1 Begriff
        punkte: 1
        frage: Ergänzen Sie den Fachbegriff.   # optional: Anweisung vor dem Lückentext (alle Lückentypen)
        text: Metalle mit einer Dichte unter 5 kg/dm³ heissen {{Leichtmetalle|Leichtmetall}}.
        # gross_klein: true     # optional: Gross-/Kleinschreibung zählt (Standard: egal)

      - typ: numerisch          # {{#Zahl}} oder mit Toleranz {{#Zahl±Toleranz}}
        titel: B2 Dichte Alu
        punkte: 1
        text: Aluminium hat eine Dichte von etwa {{#2.7±0.1}} kg/dm³.

      - typ: dropdown           # {{*richtig|falsch|falsch}} — * vor der richtigen Option
        titel: B3 Verformung
        punkte: 1
        text: Federt ein Werkstoff vollständig zurück, ist die Verformung {{*elastisch|plastisch}}.

      - typ: gemischt           # alle drei Lückenarten in einem Text
        titel: B4 Stahl
        punkte: 2
        text: Stahl enthält unter {{#2.06}} % Kohlenstoff und ist {{*umformbar|spröde}}. Er gehört zu den {{Eisenwerkstoffen}}.

      - typ: hottext            # [[Wort]] anklickbar, [[*Wort]] richtig
        titel: B5 Leichtmetalle markieren
        punkte: 1
        frage: Markieren Sie alle Leichtmetalle.
        text: Zur Auswahl stehen [[*Aluminium]], [[Kupfer]], [[*Titan]] und [[Blei]].

  - titel: Teil C – Offene Fragen
    fragen:
      - typ: freitext
        titel: C1 Verformung erklären
        punkte: 5
        zeilen: 8               # Grösse des Antwortfelds
        frage: |
          Ein Blech wird gebogen und federt teilweise zurück.

          Erklären Sie den Vorgang mit den Begriffen elastisch und plastisch.
        hinweis: Denken Sie an die **Elastizitätsgrenze**.   # optional, nur freitext; Lernende sehen ihn IM Test
        # hinweis: {titel: Tipp, text: "…"}                 # mit eigener Knopfbeschriftung (Standard «Hinweis»)
        musterloesung: |                                      # nur freitext; für die Korrektur, nicht im Test sichtbar
          Es liegt eine **elastisch-plastische** Verformung vor. Der elastische Anteil federt zurück,
          der plastische bleibt.

          Punkte: Begriffe 2 P; Ablauf 3 P.

      - typ: upload             # Abgabe einer Datei
        titel: C2 Skizze abgeben
        punkte: 2
        frage: Laden Sie Ihre Skizze als PDF hoch.

      - typ: zeichnen           # Zeichenfläche im Browser (weisse Fläche)
        titel: C3 Kraftfluss skizzieren
        punkte: 3
        frage: Skizzieren Sie den Halter und zeichnen Sie die Kraftrichtung ein.
```

## Sektionen

- Hat die Vorlage Teile (z. B. «Teil A – Grundlagen», «A Single Choice», «Block C», «Aufgabe 2: Werkstoffe»),
  wird **jeder Teil eine Sektion**. Sektionstitel = Überschrift **wörtlich**, aber ohne Punktangaben wie
  «(12 Punkte)» oder «| 8 Punkte». Reihenfolge wie in der Vorlage.
- Hat die Vorlage keine Teile: **genau eine Sektion mit dem Titel «Fragen»**.
- Erstellst du die Fragen selbst: ab etwa 8 Fragen in 2–4 Sektionen nach Teilthemen gliedern, sonst nach
  Anforderung (Wissen → Verstehen → Anwenden). Unter 8 Fragen: eine Sektion «Fragen».
- Eine Überschrift, die nur **eine** Frage einleitet, ist keine Sektion — sie gehört in die Frage.
- Eine Aufgabe mit Unterpunkten (a, b, c …) wird entweder eine Frage oder je Unterpunkt eine Frage mit
  Titel «D1a …», «D1b …» — dann Punkte je Unterpunkt aus der Vorlage und die gemeinsame Ausgangslage
  in jede dieser Fragen kopieren.
- `mischen: true` bei einer Sektion mischt deren Fragen, bei `sc`/`mc` die Antworten — nur setzen, wenn
  ich es verlange. Standard: Reihenfolge wie geschrieben (Antworten bei sc/mc werden in OLAT gemischt).

## Regeln zum Format

- Erlaubte `typ`: sc, mc, kprim, richtigfalsch, matrix, dragdrop, reihenfolge, lueckentext,
  numerisch, dropdown, gemischt, hottext, freitext, upload, zeichnen.
- `punkte` bei jeder Frage (Zahl, auch 0.5 möglich). `titel` kurz, mit Nummer aus der Vorlage.
- Leerzeile im Text = neuer Absatz. `**fett**` nur in `hinweis` und `musterloesung`.
- Formeln als LaTeX zwischen Dollarzeichen, z. B. $p \cdot V = n \cdot R \cdot T$ oder $\frac{V_1}{T_1} = \frac{V_2}{T_2}$ — in allen Texten: `frage`, Antworten, Aussagen, `hinweis`, `musterloesung` und im `text` von Lückentypen, nur nicht in der Lücke selbst («$p_2$ = {{#3±0.05}} bar»). OLAT zeigt sie als gesetzte Formel. Ein echtes Dollarzeichen als \$ schreiben.
- `hinweis` und `musterloesung` gibt es **nur bei `freitext`** — bei anderen Typen weglassen.
- `kprim` hat genau 4 Aussagen; `sc` genau eine richtige Antwort; `mc` mindestens eine.
- Bei `matrix`/`dragdrop` müssen die Texte in `loesung` exakt wie in `zeilen`/`spalten` lauten.
- Ein Einleitungstext (Fallbeispiel), der für mehrere Fragen gilt, gehört in die `frage` jeder dieser Fragen.
- Optional bei jeder Frage: `quelle:` (woher die Lösung stammt) und `unsicher:` — beide erscheinen nicht in OLAT.
- Optional bei jeder Frage: `medien: [https://www.youtube.com/watch?v=…]` für ein Video (YouTube, nanoo.tv) oder eine mp3-URL,
  mit Grösse als `medien: [{url: "https://…", breite: 640, hoehe: 360}]`.
- Fragen, die ein Bild zum Anklicken oder Beschriften brauchen, weglassen und am Ende unter
  `uebersprungen: [«A7: braucht ein Bild»]` aufführen.
- **Texte in Antworten und Aussagen immer in Anführungszeichen** (`{text: "…", richtig: true}`) —
  sonst zerschneidet jedes Komma den Text. Dasselbe in Kurzlisten `[…]` und `{…}` (`zeilen`, `spalten`,
  `elemente`, `loesung`), sobald ein Eintrag ein Komma enthält. Ebenso jeden Text, der `: ` enthält oder
  mit `[`, `{`, `*` beginnt.

## Meine Fragen / mein Material
