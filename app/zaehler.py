"""Nutzungszähler in Supabase (Tabelle `olat_umwandlungen` im bbw-hko-Projekt).

Gespeichert werden nur Zahlen — wer, wann, Modell, Tokens, Kosten, Anzahl Fragen/Seiten/Bilder.
Kein Fragetext, kein PDF, keine Datei. Geschrieben wird mit dem Token der angemeldeten Person;
die Datenbank erlaubt per RLS nur eigene Zeilen. Lesen: eigene Zeilen, kt1/reviewer alle.

Fehler hier dürfen die App nie stoppen — der Zähler ist Nebensache, das Zip ist die Hauptsache.
"""
from __future__ import annotations

import httpx
import streamlit as st

ADMIN_ROLLEN = {"kt1", "reviewer"}


def _rest(nutzer: dict) -> tuple[str, dict] | tuple[None, None]:
    """REST-Adresse und Kopfzeilen; (None, None) ohne Token — dann wird nicht gezählt."""
    if not nutzer.get("token"):
        return None, None
    s = st.secrets["supabase"]
    return s["url"].rstrip("/") + "/rest/v1", {"apikey": s["anon_key"],
                                               "Authorization": f"Bearer {nutzer['token']}"}


def protokolliere(nutzer: dict, quelle: str, verbrauch: dict | None = None, kosten: float | None = None,
                  fragen: int = 0, seiten: int = 0, bilder: int = 0) -> None:
    """Eine Zeile pro Umwandlung. `quelle`: 'pdf' (mit OpenAI) oder 'yaml' (eingefügt)."""
    url, kopf = _rest(nutzer)
    if url is None:
        return
    zeile = {"user_id": nutzer["id"], "quelle": quelle, "modell": (verbrauch or {}).get("modell"),
             "eingabe_tokens": (verbrauch or {}).get("eingabe", 0), "ausgabe_tokens": (verbrauch or {}).get("ausgabe", 0),
             "kosten_usd": round(kosten or 0, 5), "fragen": fragen, "seiten": seiten, "bilder": bilder}
    try:
        r = httpx.post(f"{url}/olat_umwandlungen", headers={**kopf, "Prefer": "return=minimal"}, json=zeile, timeout=10)
        if r.status_code >= 300:
            st.session_state["zaehler_fehler"] = f"Zähler nicht geschrieben ({r.status_code})"
        else:
            st.session_state.pop("zaehler_fehler", None)
            st.session_state.pop("meine_nutzung", None)  # neu laden
    except httpx.HTTPError as e:
        st.session_state["zaehler_fehler"] = f"Zähler nicht erreichbar ({type(e).__name__})"


def meine(nutzer: dict) -> dict | None:
    """Summen der eigenen Umwandlungen: {anzahl, kosten, tokens, seit}."""
    if "meine_nutzung" in st.session_state:
        return st.session_state["meine_nutzung"]
    url, kopf = _rest(nutzer)
    if url is None:
        return None
    try:
        r = httpx.get(f"{url}/olat_umwandlungen", headers=kopf, timeout=10, params={
            "select": "erstellt,eingabe_tokens,ausgabe_tokens,kosten_usd", "user_id": f"eq.{nutzer['id']}",
            "order": "erstellt.asc", "limit": 5000})
        if r.status_code != 200:
            return None
        zeilen = r.json()
    except httpx.HTTPError:
        return None
    summe = {"anzahl": len(zeilen),
             "kosten": sum(float(z["kosten_usd"]) for z in zeilen),
             "tokens": sum(z["eingabe_tokens"] + z["ausgabe_tokens"] for z in zeilen),
             "seit": zeilen[0]["erstellt"][:10] if zeilen else None}
    st.session_state["meine_nutzung"] = summe
    return summe


def alle(nutzer: dict, tage: int = 365) -> list[dict] | None:
    """Eine Zeile pro Person (nur kt1/reviewer; die Datenbank prüft die Rolle selbst)."""
    url, kopf = _rest(nutzer)
    if url is None:
        return None
    try:
        r = httpx.post(f"{url}/rpc/olat_nutzung", headers=kopf, json={"tage": tage}, timeout=15)
        return r.json() if r.status_code == 200 else None
    except httpx.HTTPError:
        return None
