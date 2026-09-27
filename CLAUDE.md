# CLAUDE.md

> **Sektion:** olat-qti — eigenständiges Projekt in `dev\` (eigenes git-Remote, keine PII) · **Übergeordnet:** `D:\OS\CLAUDE.md` (Router — Karte der Sektionen, Vorrangregeln, Session-Start).
> **Register:** `D:\OS\pendenzen.yaml` gilt auch hier — offene Verpflichtungen und Termine gehören dorthin, nicht in eine lokale Liste. Briefing: `python D:\OS\os_brief.py` · Schreiben: `python D:\OS\register_cli.py`.

Was das Projekt ist und wie das Format aussieht: `README.md`.
Die Skill dazu, **`olat-test`**, liegt persönlich unter `~\.claude\skills\olat-test\`
(überall verfügbar, ruft `olatqti.py` hier per absolutem Pfad auf). Ändert sich das
YAML-Format, die Skill mitziehen.

## Regeln

1. **OpenOlat ist die Wahrheit, nicht der QTI-Standard.** Jede Änderung an
   `olatqti.py` muss `python tests/test_referenz.py` fehlerfrei bestehen (alle Fragen identisch). Neue
   Features erst bauen, wenn ein OpenOlat-Export zeigt, wie OpenOlat sie schreibt —
   den Export nach `referenz/` legen und in den Test aufnehmen.
2. **Keine Lernendendaten.** Fragensätze und Tests ja; Resultate, Namen, Noten
   aus OLAT nie in dieses Repo (Router §4).
3. **Ausgabe gehört nicht ins Repo.** Gebaute Zips landen in `ausgabe/` (ignoriert).
4. Nur Standardbibliothek + PyYAML im Skript; lxml nur im Test.
5. **Schlüssel nie ins Repo.** `app/.streamlit/secrets.toml` ist ignoriert; Vorlage
   `secrets.toml.example`. Nur den öffentlichen Supabase-Schlüssel (anon) verwenden,
   nie den service_role-Schlüssel von bbw-hko.
6. **Veröffentlichung:** `DEPLOY.md` (Streamlit Community Cloud). `requirements.txt` liegt in der
   Wurzel (Cloud liest nur dort), Secrets kommen auf der Cloud aus den Streamlit-Settings, nie aus
   dem Repo. `app/.streamlit/config.toml` nur mit relativen Pfaden — sonst bricht der Start unter Linux.

## App (`app/`)

Streamlit, zwei Wege zum selben YAML → `olatqti.py` → Zip:
- **Aus PDF:** OpenAI (Structured Outputs, `app/umwandeln.py`), fest `gpt-5.6-luna` (`MODELL` in
  `streamlit_app.py`). Vergleich vom 22.09.2026 (Werkstoff-Prüfung, je 3 Läufe): luna und gpt-4.1
  gleich zuverlässig, luna rund 7× günstiger; `gpt-4.1-mini` unbrauchbar (falsche Punkte,
  verstümmelte Zeichen). Ein zweites Modell braucht einen Eintrag in `PREISE` und eine Auswahl im UI.
  Preise pro Million Tokens stehen nur in `PREISE` in `app/umwandeln.py` (Preisrechner nach der
  Umwandlung); ein neues Modell braucht dort einen Eintrag, sonst zeigt der Rechner «–».
- **YAML einfügen:** Lehrperson kopiert `app/prompt_extern.md` in die eigene KI und fügt die
  Antwort ein. Kein OpenAI-Aufruf. Das Beispiel im Prompt muss baubar bleiben (`tests/test_app.py`).
  Ändert sich das Format, Prompt und Skill `olat-test` mitziehen.
- **Formatierung** (23.09.2026): Texte sind eine Markdown-Teilmenge (`bloecke()` in `olatqti.py`);
  `umwandeln.seitentext()` liefert dem Modell den PDF-Text schon markiert. Beschreibung: README.
  Zwei Prompt-Stufen (Häkchen in der App): `SYSTEM` = einfach (fett, kursiv, Listen, Zeilen mit Nummer),
  `SYSTEM_ERWEITERT` = zusätzlich Tabellen und ### Zwischentitel. Gemeinsamer Teil in `SYSTEM_VORLAGE`.
  `test_referenz.py` braucht lxml — im App-venv fehlt es, mit einem Python mit lxml laufen lassen.

**Bewertung** (23.09.2026): Standard «Punkte pro Antwort» mit halbem Abzug je falsche Antwort, nachgebaut
aus `referenz/punkte_pro_antwort/`. In der App vor dem Bauen wählbar (pro Antwort / alles richtig, Abzug ja/nein),
`umwandeln.mit_bewertung()` setzt es oben ins YAML. gemischt, hotspot, reihenfolge: noch alles oder nichts.

**Nutzungszähler** (`app/zaehler.py`): je Umwandlung eine Zeile in `public.olat_umwandlungen` im
bbw-hko-Supabase — wer, wann, Modell, Tokens, Kosten, Fragen/Seiten/Bilder, Quelle pdf|yaml.
**Nie Inhalte** (keine Fragetexte, keine PDFs). Geschrieben wird mit dem Token der Lehrperson
(RLS: nur eigene Zeilen), gelesen eigene Zeilen bzw. alle für `kt1`/`reviewer`; die Gesamtsicht
liefert `public.olat_nutzung(tage)` (security definer mit Rollencheck). Migration
`olat_umwandlungen_zaehler` vom 22.09.2026, seit Migration `olat_nutzung_quelle_aufschluesselung`
vom 25.09.2026 zusätzlich mit `pdf`/`yaml`-Spalten (Anzahl je Quelle pro Lehrperson), in der
Admin-Übersicht in `streamlit_app.py` angezeigt. Zählerfehler dürfen die App nie stoppen.

**Testaufbau** (27.09.2026): Box «Testaufbau und Einstellungen» — mehrere Sektionen (Std. an), mehrere Teile
(Std. aus, Lehrperson wählt die Sektion, mit der ein Teil beginnt), Konfiguration neutral/formativ/summativ,
Zeitlimit und Bestehensgrenze (Std. aus). `umwandeln.mit_aufbau()` / `mit_einstellungen()` schreiben das
ins YAML; ein YAML mit eigenen `teile:` bleibt unverändert. Sektionseinleitungen liefert das Modell selbst
(`einleitung` im Schema). Prompt-Änderungen an Sektionen oder Typwahl mit `beispiele/probe_layout.py` (braucht
den Schlüssel in `secrets.toml`, ~½ Rappen je Lauf) gegenprüfen, bei Typregeln auch mit der Typangaben-Probe.

**Formelprüfung** (`app/formelcheck.py`, 27.09.2026), nach jeder PDF-Umwandlung: (1) sicher reparieren
(doppelte Backslashes, Lücke in Formel, Unicode-Indizes/-Operatoren in Formeln), (2) was bleibt — unpaariges $,
Klammern, `\frac` ohne Argument, unbekannter Befehl, Formel im Klartext — Feld für Feld in EINEM Aufruf mit
Fehlerliste zurück ans Modell; angenommen nur, wenn Lücken und Wortlaut ausserhalb der Formeln gleich bleiben und
es weniger Befunde sind, (3) Rest als «Formel prüfen» in `unsicher`. Kosten des zweiten Aufrufs zählen mit.
Beim YAML-Weg nur Meldung, keine Änderung. Meldet `formelcheck` einen gültigen Befehl als unbekannt, ihn in
`BEKANNT` ergänzen — sonst «korrigiert» das Modell eine richtige Formel (so am 27.09.2026 mit `\det`).

**Prüftabelle** (`streamlit_app.py`, `tabelle_mit_umbruch()`): eigene HTML-Tabelle statt
`st.dataframe`, seit 25.09.2026 — `st.dataframe` (glide-data-grid) kann Zellen nicht umbrechen und
schneidet lange Titel/Lösungen ab. `Titel`, `Lösung` und `Unsicher` sind als breite Spalten markiert;
`umwandeln.loesung_kurz()` kürzt entsprechend erst bei 400 statt 160 Zeichen.

Login = Microsoft über das Supabase-Projekt von bbw-hko (`app/auth.py`), gleiche Konten und Rollen; Zugang für `lp`, `kt1`, `reviewer`, nicht `gast`.
Ausnahme: Konten ausserhalb der bbw in `[zugang] gastkonten` (Secrets) — in bbw-hko mit Rolle `gast`,
damit sie dort keine Lehrpersonen-Rechte haben (neue Konten bekommen sonst automatisch `lp`, `handle_new_user`).
Eigener OpenAI-Schlüssel je Schule: `[schluessel.<kürzel>]` mit `konten` (Secrets), `openai_zugang()` in
`streamlit_app.py`; mit `rueckfall = true` bei leerem Guthaben oder ungültigem Schlüssel weiter über bbw
(nicht bei Rate-Limit oder Netzfehler). Seit 23.09.2026: BMS (noch ohne Guthaben, Rückfall an), Konto `testuser@bms-w.ch` (Rolle `gast`).
Lokal: Preview `olat-qti-app` (Port 8501, fest — Rücksprung-URL). Tests:
`python tests/test_sektionen.py` (Teile, Sektionen, Konfiguration; braucht referenz/), `app/.venv/Scripts/python tests/test_formeln.py`, `tests/test_umwandeln.py`, `tests/test_scanseiten.py`, `tests/test_medien.py`, `tests/test_bilder.py`, `tests/test_latex.py`, `tests/test_format.py` und `tests/test_app.py`
(Seiten ohne Text werden erkannt und auf Wunsch als Bild an OpenAI geschickt). Das PDF geht an OpenAI — nur
Fragen/Lösungen, nie Lernendenantworten (Router §4, Hinweis in der App).
