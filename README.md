# olat-qti

YAML-Fragensatz → QTI-2.1-Paket, das OpenOlat importiert. Dazu eine Streamlit-App, die aus einem
PDF mit Fragen und Lösungen (oder aus eingefügtem YAML) denselben Fragensatz erzeugt.

## Was nicht in diesem Repo liegt

- **Schlüssel.** `app/.streamlit/secrets.toml` ist ausgeschlossen; Vorlage: `secrets.toml.example`.
  Auf Streamlit Cloud stehen die Schlüssel in den App-Settings. Der Supabase-Schlüssel ist der
  öffentliche `anon`-Schlüssel (geschützt wird über RLS), nie `service_role`.
- **Echte Prüfungen.** `referenz/` (OLAT-Exporte) und `saetze/` bleiben lokal. Darum überspringt
  `tests/test_referenz.py` in einem Klon seine Vergleiche — alle anderen Tests laufen.
- **Gebaute Pakete** (`ausgabe/`) und die virtuelle Umgebung.

Bilder für die Beispiel-PDFs erzeugt `beispiele/bilder_gasgesetze.py`.
Veröffentlichen: `DEPLOY.md`.

```
python olatqti.py build fragen.yaml -o ausgabe/test.zip   # baut und prüft
python olatqti.py check ausgabe/test.zip                  # nur prüfen
python tests/test_referenz.py                             # Abgleich mit OpenOlat-Export
```

Import in OpenOlat: Autorenbereich → Importieren → Zip wählen → «Test».

## Warum kein Fork von ExamCraft

`talent-factory/examcraft` exportiert QTI **1.2.1 für ILIAS**, nicht 2.1 für
OpenOlat, und ist eine SaaS-Plattform (FastAPI, Postgres, Celery, Stripe). Kein Code
übernommen. Übernommen als Ideen in die Qualitätsregeln der Skill `olat-test`
(22.09.2026, aus `backend/utils/seed_prompts.py`, MIT-Lizenz): konkrete statt
generischer Fragen, Distraktoren aus Fehlvorstellungen, MC mit 2–3 richtigen von 4,
falsche Aussagen durch Ändern eines Details, Quellenverweis und Zeitschätzung je
Frage. Bewusst nicht übernommen: LLM-Bewertung von Freitextantworten — das wäre
Übermittlung von Lernendentexten an Dritte (Router §4).

Notizfelder `quelle`, `niveau`, `zeit`, `erklaerung` (und alle anderen unbekannten
Felder) ignoriert der Konverter; sie landen nie im Paket.

## Grundlage

`referenz/allefragen/` ist ein echter Export aus OpenOlat 21.0.2 mit allen 16
Fragetypen (22.09.2026). Das Skript baut diesen Export nach; der Test vergleicht
jede Frage nach Normalisierung der Identifikatoren — derzeit 35/35 identisch (16 Typen + Hinweis + Musterlösung
+ LaTeX + derselbe Satz mit «Punkte pro Antwort», `referenz/punkte_pro_antwort/`, 23.09.2026).
Die Normalisierung ignoriert, was nur der OLAT-Editor zufällig hinterlässt: Leerraum wie im Browser,
die Reihenfolge der Deklarationen je Lücke, die Kennung neu eingefügter Lücken, die Reihenfolge
gemischter Dropdown-Optionen.
OpenOlat-Eigenheiten, die bewusst übernommen sind: Klasse `match_krpim` (sic),
das `-1.0`-Mapping bei Lücken, die Spalte «Unbeantwortet» bei Richtig/Falsch,
`ooMetadata/questionType` im Manifest, Bilder nicht im Manifest aufgeführt.

## Format

```yaml
titel: LK Staatskunde 4PK25a
mischen: false            # Fragen innerhalb der Sektion mischen
bewertung: antwort        # Standard für alle Fragen (auch je Sektion), einzelne Fragen überschreiben
fragen:                   # oder: sektionen: [{titel, mischen, fragen: [...]}]
  - typ: sc               # Typ, siehe Tabelle
    titel: Hauptstadt     # erscheint in OLAT als Fragetitel
    punkte: 1             # Standard 1; Summe der Frage, auch bei Punkten pro Antwort
    bewertung: antwort    # Standard; «alles» = volle Punkte nur, wenn alles richtig ist
    frage: Was ist die Hauptstadt der Schweiz?   # Leerzeile = neuer Absatz
    antworten:
      - {text: Bern, richtig: true}
      - Zürich
```

| typ (OpenOlat) | Alias | Felder |
|---|---|---|
| `sc` / `mc` | einfachauswahl / mehrfachauswahl | `antworten`, `mischen` (Std. ja) |
| `kprim` | | genau 4 `aussagen` mit `richtig` |
| `match` / `matchdraganddrop` | matrix / dragdrop | `zeilen`, `spalten`, `loesung: {Zeile: Spalte}` oder `{Zeile: [Sp1, Sp2]}` |
| `matchtruefalse` | richtigfalsch | `aussagen` mit `richtig` |
| `fib` | lueckentext | `text` mit `{{Bern\|Berne}}` — jede Variante gilt; `gross_klein: true` |
| `numerical` | numerisch | `text` mit `{{#100}}` oder `{{#100±0.5}}` |
| `inlinechoice` | dropdown | `text` mit `{{*Sonne\|Mond}}` — `*` = richtig; `optionen: [Mars, Venus]` hängt Optionen an jedes Dropdown |
| `gapmixed` | gemischt | alle drei Lückenarten gemischt |
| `hottext` | | `text` mit `[[Wort]]`, richtige als `[[*Wort]]`; Stellen dürfen direkt aneinander stehen |
| `hotspot` | | `bild`, `bereiche: [{form: circle\|rect\|poly, koord: "x,y,r", richtig}]`, `breite`/`hoehe` (bei PNG automatisch) |
| `order` | reihenfolge | `elemente` in richtiger Reihenfolge |
| `essay` | freitext | `frage`, optional `zeilen` |
| `upload` | | `frage` |
| `drawing` | zeichnen | `frage`, optional `bild` (sonst weisse Fläche 500×350) |

**Bewertung — Punkte pro Antwort (Standard seit 23.09.2026).** In OLAT importiert, Teilpunkte stimmen
(23.09.2026, `beispiele/punkte_pro_antwort.yaml` und `beispiele/importtest.yaml`). Nachgebaut aus
`referenz/punkte_pro_antwort/` (OpenOlat → Bewertung → «Punkte pro Antwort»). `punkte` bleibt die Summe
der Frage und wird gleichmässig verteilt:

| Typ | richtige Antwort | falsche Antwort |
|---|---|---|
| mc, hottext | `punkte` / Anzahl richtige | −½ davon |
| matrix, dragdrop | `punkte` / Anzahl richtiger Zuordnungen | −½ davon (jede falsche Zelle) |
| richtigfalsch | `punkte` / Anzahl Aussagen | −½ davon; unbeantwortet 0 |
| lueckentext, numerisch, dropdown | `punkte` / Anzahl Lücken, je Lücke für sich | 0 |

`abzug: 0.5` setzt die Punkte je falsche Antwort fest (0 = kein Abzug), bei der Frage, der Sektion
oder oben für den ganzen Test. **In der App** wählt die Lehrperson vor dem Bauen «Punkte pro richtige
Antwort» oder «nur, wenn alles richtig ist» und ob falsche Antworten abziehen; die App schreibt das als
`bewertung:`/`abzug:` oben ins YAML (`umwandeln.mit_bewertung()`), Angaben bei einzelnen Fragen gehen vor. Die Frage fällt nie unter 0.
Beispiel mc mit 2 richtigen und 1 falschen, 1 Punkt: eine richtige gewählt = 0.5, alles angekreuzt = 0.75.
`bewertung: alles` schaltet zurück auf OpenOlats Standard (volle Punkte nur bei ganz richtig).
sc, kprim (eigene Halbpunkt-Regel), freitext/upload/zeichnen sind davon nicht betroffen. **gemischt,
hotspot, reihenfolge bleiben bei alles oder nichts**, bis ein Export zeigt, wie OpenOlat sie pro Antwort schreibt;
`bewertung: antwort` direkt an einer solchen Frage bricht den Build ab.

**Globale Dropdown-Optionen:** `optionen: [Mars, Venus]` bei dropdown/gemischt — OpenOlats «globale
Antworten»: die Optionen stehen zusätzlich in jedem Dropdown der Frage (`templateDeclaration`).
Zeilenumbruch in Lückentext und Hottext wie überall: Zeile mit `\` beenden.

**Medien, bei jedem Typ:** `medien: [URL, …]` oder `[{url, breite, hoehe}]` (Std. 640×480).
YouTube-, nanoo.tv- (in OLAT getestet 22.09.2026) und mp3-Links erscheinen nach dem Fragetext im OLAT-Player — dasselbe
Markup wie «Medien einfügen» im OLAT-Editor (`olatFlashMovieViewer`, auch Audio als
`type="video"`). Nur verlinkt, nicht ins Paket kopiert.

**Bilder im Fragetext, bei jedem Typ:** `bilder: [pfad.png, …]` oder `[{datei, alt, breite, hoehe}]`
(Pfad relativ zur YAML-Datei; PNG, JPEG, GIF). Je Bild ein Absatz `<p><img/></p>` direkt nach `frage`,
die Datei neben den Fragen im Paket. Anzeige auf 600 px Breite begrenzt, Datei in voller Auflösung.
Aufbau nach QTI-Standard, **in OLAT importiert und angezeigt am 22.09.2026** (`beispiele/bildtest.yaml`).
Die App holt Bilder aus dem PDF (Logos auf mehr als der Hälfte der Seiten und Bilder unter 80 px fallen
weg), setzt an ihrer Stelle «[Bild: s2_bild1.jpg]» in den Text, und das Modell ordnet sie den Fragen zu.

**Fragetyp aus dem PDF:** Steht der Typ in der Überschrift einer Aufgabe («Aufgabe 3 – Lückentext»), gilt er
vor der Form. Das Modell meldet die Angabe in `typ_im_pdf`; weicht der gewählte Typ ab, markiert
`umwandeln.typ_aus_angabe()` die Frage mit ⚠. Roter Text (Lösungsfarbe) kommt als `<rot>…</rot>` ans
Modell und wird danach entfernt. Probe: `beispiele/pdf_typangaben.py` (14 Aufgaben mit Fallen, `ERWARTET`),
23.09.2026 mit gpt-5.6-luna: 13, 13, 13, 14, 14, 14 von 14 über sechs Läufe (die letzten zwei mit dem
nachgeschärften Prompt).

**Formatierung (Markdown-Teilmenge)** in allen Texten (`frage`, Antworten, Aussagen, `text`, `hinweis`,
`musterloesung`): `**fett**` → `<strong>`, `*kursiv*` → `<em>` (`\*` = echter Stern); je Zeile eines Absatzes
`### Titel` → `<h3>` (`####` → `<h4>`), `- Punkt` → `<ul>`, `1. Punkt` → `<ol>`, `| a | b |` (mit `|---|`
nach der Kopfzeile) → `<table>`. Zeilen eines Absatzes werden zu Fliesstext verbunden, ausser eine Zeile endet
mit `\` (→ `<br/>`) oder **jede** Zeile beginnt mit einer Nummer (Text mit Zeilennummern: jede Zeile bleibt).
In Antworten/Aussagen/Lückentext nur fett, kursiv, Formeln. Alles an OLAT-Exporten verifiziert
(23.09.2026): `referenz/formatierung/` (Pietros Nachformatierung einer echten Umwandlung) und
`referenz/formatierung_demo/` (Demo, in OLAT importiert und nachformatiert). Tabellen bekommen dort wie im
OLAT-Editor `class="b_grid"` und Rahmenstile, sonst zeigt OLAT sie ohne Gitter. Die App liefert dem Modell den PDF-Text schon
mit `**fett**`, `*kursiv*`, `- ` (auch gezeichnete Aufzählungspunkte) und Markdown-Tabellen; Zeilennummern am
Rand stehen vor ihrer Zeile. Schriftgrösse und Farbe gehen nicht mit.

**Formeln (LaTeX):** `$…$` in `frage`, Antworten, Aussagen, `hinweis`, `musterloesung` →
`<span class="math" title="…">…</span>` wie der OLAT-Formeleditor (title = Formel mit JavaScript-`escape()`
kodiert). Nachgebaut aus `referenz/latex/` (Frage A2 aus `referenz/FOTOSINTESI.zip`). `\$` = echtes
Dollarzeichen. Auch im `text` von Lücken- und Hottext-Typen (zwischen den Lücken, nicht darin).

**Hinweis, nur Freitext:** `hinweis: "Text"` oder `{titel: Knopfbeschriftung, text: …}`
(Std.-Titel «Hinweis», Formatierung wie oben). Unter dem Antwortfeld
erscheint ein Knopf, der den Text als Dialog öffnet — **während des Tests sichtbar**.
Nachgebaut aus `referenz/hinweis/` (Frage C1 aus `referenz/TestFachkunde.zip`).

**Musterlösung, nur Freitext:** `musterloesung: "Text"` oder `{titel, text}` (Std.-Titel
«Korrekte Lösung», Formatierung wie oben). Entspricht in OLAT Feedback → «Korrekte Lösung»:
kein Knopf im Test; OLAT zeigt sie bei der Korrektur und — nur wenn in den
Testeinstellungen freigegeben — in den Resultaten der Lernenden. Die Pakete dieses
Skripts geben sie nicht frei (`showSolution="false"`). Nachgebaut aus `referenz/loesung/`
(Frage C5 aus `referenz/TestFachkunde_hinweis_loesung.zip`). Feldname bewusst nicht
`loesung` — das ist bei Matrix/Drag and Drop die Zuordnung.

Bewertung wie in OpenOlat voreingestellt: alles oder nichts; Kprim 4 richtig = voll,
3 richtig = halb. Freitext, Upload, Zeichnen bewertet die Lehrperson.
Bildpfade sind relativ zur YAML-Datei.

## Import-Stand

Der Referenz-Export hat pro Frage nur eine Lücke, 1 Punkt und eine Sektion.
`beispiele/importtest.yaml` deckt den Rest ab — **am 22.09.2026 in OLAT importiert,
funktioniert.** Abgedeckt:

- mehrere Lücken in einer Frage, Varianten pro Lücke (T1)
- Zahl mit Toleranz — `toleranceMode="absolute"` ist geraten (T2)
- gemischte Lücken mit Dropdown und Zahl (T3)
- Punkte ≠ 1, v. a. Kprim-Halbpunkte (T4)
- Matrix mit ungenutzter Spalte, Hottext und Hotspot mit mehreren richtigen (T5–T7)
- mehrere Sektionen, Sektion gemischt; `expectedLines`; Zeichnen ohne Bild (T8–T9)

Nicht unterstützt: Feedback-Texte ausser Hinweis und Musterlösung bei Freitext, Punkte pro Antwort bei gemischt/hotspot/reihenfolge,
Fragenpools. Kommt, wenn ein Export zeigt, wie OpenOlat es schreibt.
