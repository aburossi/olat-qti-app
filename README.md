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
jede Frage nach Normalisierung der Identifikatoren — derzeit 54/54 identisch (16 Typen + Hinweis + Musterlösung
+ LaTeX + derselbe Satz mit «Punkte pro Antwort», `referenz/punkte_pro_antwort/`, 23.09.2026, + derselbe in Teilen und Sektionen, `referenz/sektionen_neutral/`, 27.09.2026, + gemischt mit Punkten je Lückenart und Freitext mit gesperrtem Einfügen, `referenz/gemischt_pro_antwort/`, `referenz/essay_nocopypaste/`, 27.09.2026).
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

**Teile, Sektionen, Testeinstellungen** (27.09.2026, nachgebaut aus `referenz/sektionen_{neutral,formativ,summativ}/`,
Nachbau `beispiele/sektionen_teile.yaml`, geprüft von `tests/test_sektionen.py`; Demo `beispiele/teile_demo.yaml`):

```yaml
titel: LK Werkstoffe
konfig: neutral          # neutral (Standard) | formativ | summativ — siehe unten
zeitlimit: 45            # Minuten für den ganzen Test (optional)
bestehen: 12             # bestanden ab so vielen Punkten (optional)
teile:                   # optional; ohne teile: ist alles ein Teil
  - sektionen:           # oder direkt fragen:
      - titel: A – Diagramm
        mischen: false
        text: Einleitung, **Markdown** wie bei frage     # steht über jeder Frage der Sektion
        medien: [https://www.youtube.com/watch?v=…]    # wie bei Fragen
        bilder: [{datei: bilder/diagramm.png, alt: …}]  # wie bei Fragen
        fragen: [...]
  - sektionen: [...]     # Teil 2: in OLAT erst nach Abschluss von Teil 1
```

Die Einleitung (`rubricBlock`) zeigt OLAT über jeder Frage der Sektion; Reihenfolge Text → Medien → Bilder.
`bewertung`/`abzug` gehen vom Test über den Teil und die Sektion zur Frage. `konfig` wählt die
Testeinstellungen (`QTI21PackageConfig.xml`, Vorlagen in `vorlagen/konfig/`, je ein OLAT-Export):

| konfig | Pausieren | Abbrechen | Versuche | Feedback | Resultate nach Abschluss |
|---|---|---|---|---|---|
| `neutral` (Std.) | ja | nein | unbegrenzt | aus | keine |
| `formativ` | ja | ja | unbegrenzt | an, Punktestand sichtbar | mit eigenen und korrekten Lösungen |
| `summativ` | nein | nein | 1 | aus | nur Punktzahl |

Ohne `bestehen` fällt `passedType` aus der Vorlage weg (wie bisher). Achtung `neutral`/`summativ` blenden
Feedback aus (`hideFeedbacks`) — ob das auch den Hinweis-Knopf bei Freitext verbirgt, ist in OLAT noch nicht geprüft.

| typ (OpenOlat) | Alias | Felder |
|---|---|---|
| `sc` / `mc` | einfachauswahl / mehrfachauswahl | `antworten`, `mischen` (Std. ja) |
| `kprim` | | genau 4 `aussagen` mit `richtig`; `mischen` (Std. ja seit 27.09.2026 — nur die Aussagen, die Spalten +/− bleiben) |
| `match` / `matchdraganddrop` | matrix / dragdrop | `zeilen`, `spalten`, `loesung: {Zeile: Spalte}` oder `{Zeile: [Sp1, Sp2]}` |
| `matchtruefalse` | richtigfalsch | `aussagen` mit `richtig` |
| `fib` | lueckentext | `text` mit `{{Bern\|Berne}}` — jede Variante gilt; `gross_klein: true`; `laenge: 150`, `platzhalter` |
| `numerical` | numerisch | `text` mit `{{#100}}` oder `{{#100±0.5}}` |
| `inlinechoice` | dropdown | `text` mit `{{*Sonne\|Mond}}` — `*` = richtig; `optionen: [Mars, Venus]` hängt Optionen an jedes Dropdown |
| `gapmixed` | gemischt | alle drei Lückenarten gemischt; `laenge`, `platzhalter` für die Textlücken; `punkte_dropdown`/`punkte_text`/`punkte_zahl` |
| `hottext` | | `text` mit `[[Wort]]`, richtige als `[[*Wort]]`; Stellen dürfen direkt aneinander stehen |
| `hotspot` | | `bild`, `bereiche: [{form: circle\|rect\|poly, koord: "x,y,r", richtig}]`, `breite`/`hoehe` (bei PNG automatisch) |
| `order` | reihenfolge | `elemente` in richtiger Reihenfolge |
| `essay` | freitext | `frage`, optional `zeilen`; `einfuegen: false` sperrt Kopieren/Einfügen |
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
| lueckentext, numerisch, dropdown, gemischt | `punkte` / Anzahl Lücken, je Lücke für sich — oder je Lückenart `punkte_dropdown`/`punkte_text`/`punkte_zahl` | 0 |

`abzug: 0.5` setzt die Punkte je falsche Antwort fest (0 = kein Abzug), bei der Frage, der Sektion
oder oben für den ganzen Test. **In der App** wählt die Lehrperson vor dem Bauen «Punkte pro richtige
Antwort» oder «nur, wenn alles richtig ist» und ob falsche Antworten abziehen; die App schreibt das als
`bewertung:`/`abzug:` oben ins YAML (`umwandeln.mit_bewertung()`), Angaben bei einzelnen Fragen gehen vor. Die Frage fällt nie unter 0.
Beispiel mc mit 2 richtigen und 1 falschen, 1 Punkt: eine richtige gewählt = 0.5, alles angekreuzt = 0.75.
`bewertung: alles` schaltet zurück auf OpenOlats Standard (volle Punkte nur bei ganz richtig).
sc, kprim (eigene Halbpunkt-Regel), freitext/upload/zeichnen sind davon nicht betroffen. **Hotspot und
reihenfolge bleiben bei alles oder nichts**, bis ein Export zeigt, wie OpenOlat sie pro Antwort schreibt;
`bewertung: antwort` direkt an einer solchen Frage bricht den Build ab.

**Punkte je Lückenart** (27.09.2026, nachgebaut aus `referenz/gemischt_pro_antwort/`, Frage S6 der LK 4PG24a,
`beispiele/gemischt_pro_antwort.yaml`, Regeln in `tests/test_gewichte.py`): `punkte_dropdown: 1`, `punkte_text: 2`,
`punkte_zahl: …` = Punkte **je Lücke** dieser Art. Dann gilt für die Frage immer Punkte pro Antwort (auch wenn
oben `bewertung: alles` steht; `bewertung: alles` an der Frage selbst ist ein Fehler), und `punkte` ist die Summe —
weglassen oder richtig angeben, sonst bricht der Build ab. Jede Lückenart, die vorkommt, braucht ihre Zahl.
Typischer Fall: je Aussage ein Dropdown «Tatsache/Bewertung» (1 P.), darunter «Begründung: {{…}}» (2 P.).
Richtiges Dropdown = seine Punkte, falsches = 0, kein Abzug. Geht auch bei lueckentext, dropdown, numerisch.
**Seit 27.09.2026 auch `gemischt` pro Antwort** (vorher immer alles oder nichts): ohne Gewichte gleichmässig
verteilt wie bei lueckentext; `bewertung: alles` schaltet zurück. **Ungeprüft in OLAT:** Zahl-Lücken in `gemischt`
mit Punkten pro Antwort — gebaut nach dem Muster von `numerical` (dort in OLAT geprüft), der Export zeigt nur
Dropdown- und Textlücken.

**Einfügen sperren** (27.09.2026, `referenz/essay_nocopypaste/`, Frage S8, `beispiele/essay_nocopypaste.yaml`):
`einfuegen: false` bei `freitext` → `class="essay-nocopypaste"`, Lernende können nichts ins Antwortfeld einfügen.
Wie `bewertung` auch oben für den ganzen Test, am Teil oder an der Sektion; eine Frage mit `einfuegen: true`
bleibt offen. Standard: Einfügen erlaubt (`class=""`). In der App: Häkchen «Einfügen in Freitexten sperren».

**Länge und Platzhalter von Textlücken** (27.09.2026, nachgebaut aus `referenz/laenge/`, OpenOLAT 21.0.3,
Test `tests/test_laenge.py`, Demo `beispiele/laenge.yaml`): `laenge: 150` setzt `expectedLength` («Erwartete
Länge»), `platzhalter: "Ihre Antwort hier"` den `placeholderText` — für **alle Textlücken** der Frage, bei
`lueckentext` und `gemischt`. Gedacht für kurze Antworten in einer Lücke, z. B. je Aussage ein Dropdown
«Tatsache/Bewertung» und darunter «Begründung: {{…}}». Die Variante in der Lücke ist dann die Musterlösung:
OLAT zeigt sie in den Resultaten, sobald die Testeinstellungen Lösungen freigeben (`formativ`). Eine frei
formulierte Antwort trifft sie nie — solche Lücken von Hand bewerten. Zahl-Lücken und Dropdowns bleiben unverändert.

**Globale Dropdown-Optionen:** `optionen: [Mars, Venus]` bei dropdown/gemischt — OpenOlats «globale
Antworten»: die Optionen stehen zusätzlich in jedem Dropdown der Frage (`templateDeclaration`).
Zeilenumbruch in Lückentext und Hottext wie überall: Zeile mit `\` beenden.

**Medien, bei jedem Typ:** `medien: [URL, …]` oder `[{url, breite, hoehe}]` (Std. 640×480).
YouTube-, nanoo.tv- (in OLAT getestet 22.09.2026) und mp3-Links erscheinen nach dem Fragetext im OLAT-Player — dasselbe
Markup wie «Medien einfügen» im OLAT-Editor (`olatFlashMovieViewer`, auch Audio als
`type="video"`). Nur verlinkt, nicht ins Paket kopiert.
**SRF-Audio** (27.09.2026 in OLAT geprüft): `srf.ch/play/embed?urn=…` spielt der Player **nicht** (HTML-Seite). Die mp3
über die URN holen: `https://il.srgssr.ch/integrationlayer/2.0/mediaComposition/byUrn/<urn>.json` → in `chapterList`
das Kapitel mit genau dieser URN → `resourceList[].url` mit Protokoll HTTPS und Encoding MP3 (z. B.
`https://download-media.srf.ch/world/audio/Rendez-vous_radio/2026/09/….mp3`) — das spielt, auch an der Sektion.
Das macht **`python olatqti.py srf-mp3 <Link oder URN>`** (27.09.2026, nur Standardbibliothek): nimmt eine URN, einen
Play-Link mit `?urn=…` oder eine Audio-Seite `srf.ch/audio/…?id=AUDI…` — dort steht die URN nur im HTML der Seite
(die `AUDI…`-ID selbst kennt die Schnittstelle nicht); bei mehreren Beiträgen auf einer Seite gilt der, dessen mp3 die
ID im Namen trägt. Gibt die mp3-URL aus (Titel und Dauer auf stderr). **Die App** ersetzt SRF/SRG-Seiten in `medien:`
beim Bauen automatisch (Häkchen «SRF-Links in abspielbare mp3 umwandeln», Standard an; Links im Fragetext bleiben).
Test `tests/test_srf.py` (ohne Netz), `tests/test_srf.py --live` gegen den Beitrag «Gredig direkt» vom 25.09.2026.
Sendungsseiten wie «Echo der Zeit» gehören zur ganzen Sendung (SRF benennt sie nach dem ersten Beitrag); gibt es darin
einen Beitrag mit demselben Titel, nimmt die App den Beitrag (z. B. 3.7 statt 41 Min.) und sagt es; `&partId=…` wählt
einen bestimmten Beitrag. Seiten ohne Audio (Folge nur angekündigt) ergeben eine Warnung, der Link bleibt.
Probe-PDF: `beispiele/pdf_srf.py` (Link hinter einem Wort, ausgeschriebener umbrechender Link, Folge ohne Audio).
**Rückgängig:** Häkchen aus (pro Umwandlung), oder die beiden Commits «SRF-Links …» mit `git revert` zurücknehmen — sie ändern
nur die SRG-Funktionen in `olatqti.py`/`umwandeln.py`, das Häkchen und `tests/test_srf.py`.

**Hinweisfrage** (27.09.2026 geprüft): `sc` mit `punkte: 0` und nur einer Antwort «Ja» baut und erscheint sauber —
z. B. «Beitrag gehört? Achtung, der nächste Teil hat kein Audio».

**Bilder im Fragetext, bei jedem Typ:** `bilder: [pfad.png, …]` oder `[{datei, alt, breite, hoehe}]`
(Pfad relativ zur YAML-Datei; PNG, JPEG, GIF). Je Bild ein Absatz `<p><img/></p>` direkt nach `frage`,
die Datei neben den Fragen im Paket. Anzeige auf 600 px Breite begrenzt, Datei in voller Auflösung.
Aufbau nach QTI-Standard, **in OLAT importiert und angezeigt am 22.09.2026** (`beispiele/bildtest.yaml`).
Die App holt Bilder aus dem PDF (Logos auf mehr als der Hälfte der Seiten und Bilder unter 80 px fallen
weg), setzt an ihrer Stelle «[Bild: s2_bild1.jpg]» in den Text, und das Modell ordnet sie den Fragen zu.

**Einleitung und Antwortform aus dem PDF** (27.09.2026): Das Modell liefert je Sektion `einleitung`, `medien`,
`bilder` — Stoff für ALLE Fragen eines Teils (Fallbeispiel, Diagramm, Video) steht einmal an der Sektion statt in
jeder Frage; Stoff nur für einige Fragen bleibt in diesen Fragen. Den Typ bestimmt die Antwortform (Block
«ANTWORTFORM IM PDF» im Prompt): nummerierte Antwortlinien → Lückentext mit einer Zeile je Linie (im Konverter:
ein Absatz, in dem jede Zeile ein Listenpunkt ist, behält seine Zeilen), Zahl auf der Linie → numerisch,
Wortkasten → Dropdown, Paare verbinden → Matrix, Kästchen nummerieren → Reihenfolge. Die Prüftabelle zeigt
Einleitungen als eigene Zeile. Legt die Lehrperson die Sektionen zusammen, wandert jede Einleitung in die
Fragen ihrer Sektion zurück. Ligaturen aus dem PDF («ﬀ», «ﬁ») werden beim Auslesen aufgelöst.
Probe: `beispiele/pdf_layout.py` + `beispiele/probe_layout.py` (11 Aufgaben mit Fallen); mit gpt-5.6-luna
0, 0, 0, 1, 0 Abweichungen über fünf Läufe (die eine: Lesetext für C1/C2 nur in C2). Dieselbe Prompt-Fassung
in der Typangaben-Probe 14/14 dreimal.
Video/Audio: wohin, entscheidet der Bezug, nicht die Stelle des Links — bezieht sich ein ganzer Teil darauf, an die
Sektion. Hat der Test genau einen Medien-Link, bekommt ihn danach jede Frage, die auf «Video»/«Audio» verweist und
ihn nicht schon über ihre Sektion zeigt (`umwandeln.medien_verteilen()`; das Modell wiederholt den Link sonst
nicht). Beispiel-PDF der App (`probe_layout.py 3 gase`): Video an Teil A und bei B1, B3, C3, dreimal richtig.
**Formelprüfung nach der Umwandlung** (`app/formelcheck.py`, Test `tests/test_formeln.py`): sicher reparieren →
Rest mit Fehlerliste gezielt ans Modell (ein Aufruf, nur die betroffenen Textfelder, Korrektur nur bei gleichem
Wortlaut und gleichen Lücken) → was bleibt, als ⚠ «Formel prüfen». Probe am 27.09.2026 mit gpt-5.6-luna über
Mathematik-, Gasgesetze- und Fotosynthese-PDF (je 2–3 Läufe): alles repariert oder sauber, nichts offen;
zweiter Aufruf kostet rund 0,03 Rappen.
**Lücke in einer Formel** («$V_2 = {{#6}}\,\text{L}$», schreibt luna in zwei von drei Läufen): der Konverter
schliesst die Formel vor der Lücke und öffnet sie danach wieder (`olatqti.formel_um_stellen()`), sonst zeigte
OLAT den LaTeX-Code.

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
- gemischte Lücken mit Dropdown und Zahl (T3) — seit 27.09.2026 pro Antwort, so noch nicht neu importiert
- Punkte ≠ 1, v. a. Kprim-Halbpunkte (T4)
- Matrix mit ungenutzter Spalte, Hottext und Hotspot mit mehreren richtigen (T5–T7)
- mehrere Sektionen, Sektion gemischt; `expectedLines`; Zeichnen ohne Bild (T8–T9)

Nicht unterstützt: Feedback-Texte ausser Hinweis und Musterlösung bei Freitext, Punkte pro Antwort bei hotspot/reihenfolge,
Fragenpools. Kommt, wenn ein Export zeigt, wie OpenOlat es schreibt.
