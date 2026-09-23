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
  `test_referenz.py` braucht lxml — im App-venv fehlt es, mit einem Python mit lxml laufen lassen.

**Nutzungszähler** (`app/zaehler.py`): je Umwandlung eine Zeile in `public.olat_umwandlungen` im
bbw-hko-Supabase — wer, wann, Modell, Tokens, Kosten, Fragen/Seiten/Bilder, Quelle pdf|yaml.
**Nie Inhalte** (keine Fragetexte, keine PDFs). Geschrieben wird mit dem Token der Lehrperson
(RLS: nur eigene Zeilen), gelesen eigene Zeilen bzw. alle für `kt1`/`reviewer`; die Gesamtsicht
liefert `public.olat_nutzung(tage)` (security definer mit Rollencheck). Migration
`olat_umwandlungen_zaehler` vom 22.09.2026. Zählerfehler dürfen die App nie stoppen.

Login = Microsoft über das Supabase-Projekt von bbw-hko (`app/auth.py`), gleiche Konten und Rollen; Zugang für `lp`, `kt1`, `reviewer`, nicht `gast`.
Lokal: Preview `olat-qti-app` (Port 8501, fest — Rücksprung-URL). Tests:
`app/.venv/Scripts/python tests/test_umwandeln.py`, `tests/test_scanseiten.py`, `tests/test_medien.py`, `tests/test_bilder.py`, `tests/test_latex.py`, `tests/test_format.py` und `tests/test_app.py`
(Seiten ohne Text werden erkannt und auf Wunsch als Bild an OpenAI geschickt). Das PDF geht an OpenAI — nur
Fragen/Lösungen, nie Lernendenantworten (Router §4, Hinweis in der App).
