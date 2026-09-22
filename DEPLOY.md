# Veröffentlichen auf Streamlit Community Cloud

Kurzfassung: Repo auf GitHub, App auf share.streamlit.io, Schlüssel in die Streamlit-Secrets,
neue Adresse in Supabase freischalten. Reihenfolge einhalten — sonst scheitert der Login.

## 1. GitHub

- **Privates Repo empfohlen.** Der Code enthält keine Schlüssel, aber die Supabase-Projektadresse,
  die Prompts und die Prüfungsbeispiele der bbw. Streamlit Cloud kann private Repos deployen.
- Nie committen: `app/.streamlit/secrets.toml` (steht in `.gitignore`), `.venv/`, `ausgabe/`.
- Vor dem ersten Push prüfen, dass nichts Geheimes mitgeht:

  ```bash
  git status --short | grep -i secret     # muss leer sein
  git check-ignore -v app/.streamlit/secrets.toml
  ```

## 2. App anlegen

Auf share.streamlit.io → «New app»:

| Feld | Wert |
|---|---|
| Repository | dein Repo |
| Branch | `main` |
| Main file path | `app/streamlit_app.py` |
| Python version | 3.11 oder 3.12 |

`requirements.txt` liegt im Wurzelverzeichnis und wird automatisch installiert.

## 3. Secrets in Streamlit eintragen

App → Settings → Secrets, Inhalt von `app/.streamlit/secrets.toml.example` einfügen und ausfüllen:

```toml
[supabase]
url = "https://mbslkjxkleiudzsbjqau.supabase.co"
anon_key = "sb_publishable_…"                   # öffentlicher Schlüssel, NIE service_role

[openai]
api_key = "sk-…"
```

Mehr braucht es nicht: Die App erkennt ihre eigene Adresse selbst und benutzt sie als Rücksprungziel
nach dem Microsoft-Login. Ein Abschnitt `[app] url = "…"` ist nur nötig, wenn die App unter einem
anderen Namen erreichbar sein soll (eigene Domain, Reverse Proxy).

## 4. Supabase freischalten

Dashboard → Authentication → URL Configuration → Redirect URLs ergänzen:

```
https://<deine-app>.streamlit.app/**
```

Die Site URL (`https://bbw-hko.ch`) bleibt unverändert. Ohne diesen Eintrag landet der Login
wieder auf bbw-hko.ch statt in der App.

## 5. Prüfen

1. App öffnen, mit Microsoft anmelden → Name und Rolle stehen oben.
2. Ein kleines PDF umwandeln → Kostenbox erscheint, Zähler zählt hoch.
3. In OLAT importieren.
4. Als `kt1` den Bereich «Nutzung aller Lehrpersonen» aufklappen.

## Betrieb

- **Kosten:** Der OpenAI-Schlüssel der Schule hängt an der App. Wer sich anmelden kann, kann ihn
  brauchen — Zugang haben nur Konten mit Rolle `lp`, `kt1`, `reviewer` (nicht `gast`,
  nicht `@lernende.bbw.ch`). Verbrauch siehe Zählerbereich.
- **Schlüssel wechseln:** nur in den Streamlit-Secrets, nie im Repo.
- **Konverter ändern:** `olatqti.py` anpassen, `python tests/test_referenz.py` muss fehlerfrei
  durchlaufen, dann pushen. Streamlit Cloud startet nach jedem Push neu.
- **Lokal weiterarbeiten:** `cd app && .venv/Scripts/python -m streamlit run streamlit_app.py`;
  die lokale `app/.streamlit/secrets.toml` bleibt unberührt.
