"""Microsoft-Login über das Supabase-Projekt von bbw-hko — gleiche Konten, gleiche Rollen.

Ablauf wie in bbw-hko (`/api/auth/microsoft` → `/auth/callback`), nur als PKCE ohne
Browser-Speicher: Den code_verifier hält der Server, adressiert über eine Einmal-Nonce
in der Rücksprung-URL. Streamlit verliert beim Redirect die Session, deshalb geht das
nicht über st.session_state.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
import time
import urllib.parse

import httpx
import streamlit as st

# bbw-hko: lp = Lehrperson, kt1 = Admin, reviewer = Prüfende, gast = geteiltes Gastkonto
ERLAUBTE_ROLLEN = {"lp", "kt1", "reviewer"}
# Zusätzlich zu bbw-hko: Lernendenkonten nie, auch wenn bbw-hko ihnen «lp» gibt
# (gefunden 22.09.2026) — hier hängt der OpenAI-Schlüssel der Schule dran.
GESPERRTE_DOMAINS = ("@lernende.bbw.ch",)
GUELTIGKEIT_S = 600


def gastkonten() -> set[str]:
    """Konten ausserhalb der bbw (z. B. test@olat.ch) mit Rolle «gast» in bbw-hko — dort ohne Rechte einer
    Lehrperson, hier trotzdem zugelassen. Liste in den Secrets, nicht im Code (23.09.2026):
        [zugang]
        gastkonten = ["test@olat.ch"]"""
    try:
        return {str(e).strip().lower() for e in st.secrets.get("zugang", {}).get("gastkonten", [])}
    except Exception:  # keine Secrets-Datei (Tests)
        return set()


def app_url() -> str:
    """Rücksprungziel nach dem Login: aus den Secrets, sonst die Adresse, unter der die App läuft.

    Automatisch heisst: lokal http://localhost:8501, auf Streamlit Cloud die App-Adresse. Diese Adresse
    muss in Supabase unter Redirect URLs freigeschaltet sein, sonst landet der Login auf bbw-hko.ch."""
    if eingetragen := st.secrets.get("app", {}).get("url"):
        return str(eingetragen).rstrip("/")
    try:
        teile = urllib.parse.urlsplit(st.context.url)
        if teile.scheme and teile.netloc:
            return f"{teile.scheme}://{teile.netloc}"
    except Exception:  # ältere Streamlit-Version oder Aufruf ausserhalb einer Sitzung
        pass
    st.error("Die Adresse der App ist unbekannt. In den Secrets ergänzen:\n\n"
             "```toml\n[app]\nurl = \"https://<deine-app>.streamlit.app\"\n```")
    st.stop()


def _cfg() -> tuple[str, str, str]:
    s = st.secrets
    if not s.get("supabase", {}).get("anon_key") or not s.get("supabase", {}).get("url"):
        st.error("In den Secrets fehlt der Supabase-Zugang. Ergänzen (Werte aus dem bbw-hko-Projekt, "
                 "öffentlicher anon-Schlüssel, **nie** service_role):\n\n"
                 "```toml\n[supabase]\nurl = \"https://mbslkjxkleiudzsbjqau.supabase.co\"\n"
                 "anon_key = \"sb_publishable_…\"\n```")
        st.stop()
    return s["supabase"]["url"].rstrip("/"), s["supabase"]["anon_key"], app_url()


def _grund(r: httpx.Response) -> str:
    """Supabase-Fehlermeldung statt nur Statuscode."""
    try:
        j = r.json()
        return j.get("error_description") or j.get("msg") or j.get("message") or j.get("error") or str(r.status_code)
    except ValueError:
        return str(r.status_code)


@st.cache_resource
def _offene_logins() -> dict[str, tuple[str, float]]:
    """nonce -> (code_verifier, zeitpunkt); prozessweit, überlebt den Redirect."""
    return {}


def login_url() -> str:
    url, _, app_url = _cfg()
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    nonce = secrets.token_urlsafe(16)
    offen = _offene_logins()
    jetzt = time.time()
    for n in [n for n, (_, t) in offen.items() if jetzt - t > GUELTIGKEIT_S]:
        offen.pop(n, None)
    offen[nonce] = (verifier, jetzt)
    q = urllib.parse.urlencode({
        "provider": "azure",
        "redirect_to": f"{app_url}/?login={nonce}",
        "scopes": "email profile",  # wie bbw-hko
        "code_challenge": challenge,
        "code_challenge_method": "s256",
    })
    return f"{url}/auth/v1/authorize?{q}"


def _tausche_code(code: str, nonce: str) -> dict:
    url, key, _ = _cfg()
    eintrag = _offene_logins().pop(nonce, None)
    if not eintrag or time.time() - eintrag[1] > GUELTIGKEIT_S:
        raise PermissionError("Login abgelaufen oder schon benutzt — bitte neu anmelden.")
    r = httpx.post(f"{url}/auth/v1/token", params={"grant_type": "pkce"},
                   headers={"apikey": key}, json={"auth_code": code, "code_verifier": eintrag[0]}, timeout=20)
    if r.status_code != 200:
        raise PermissionError(f"Anmeldung fehlgeschlagen: {_grund(r)}")
    return _nutzer_aus(r.json())


def _mit_passwort(email: str, passwort: str) -> dict:
    """Wie das E-Mail/Passwort-Formular auf bbw-hko.ch/login — für Admin- und Testkonten."""
    url, key, _ = _cfg()
    r = httpx.post(f"{url}/auth/v1/token", params={"grant_type": "password"},
                   headers={"apikey": key}, json={"email": email.strip(), "password": passwort}, timeout=20)
    if r.status_code != 200:
        raise PermissionError("E-Mail oder Passwort falsch.")
    return _nutzer_aus(r.json())


def _nutzer_aus(sitzung: dict) -> dict:
    url, key, _ = _cfg()
    user = sitzung["user"]
    p = httpx.get(f"{url}/rest/v1/profiles", params={"id": f"eq.{user['id']}", "select": "role,full_name"},
                  headers={"apikey": key, "Authorization": f"Bearer {sitzung['access_token']}"}, timeout=20)
    profil = (p.json() or [{}])[0] if p.status_code == 200 else {}
    return {"id": user["id"], "email": user.get("email", ""),
            "name": profil.get("full_name") or user.get("email", ""),
            "rolle": profil.get("role") or "lp",
            # für den Nutzungszähler: die App schreibt mit dem Token der Lehrperson, nie mit service_role
            "token": sitzung["access_token"]}


def anmeldung() -> dict | None:
    """Gibt den angemeldeten Nutzer zurück oder zeigt die Anmeldung und stoppt den Lauf."""
    qp = st.query_params
    if "code" in qp and "login" in qp:
        try:
            st.session_state["nutzer"] = _tausche_code(qp["code"], qp["login"])
        except PermissionError as e:
            st.session_state["login_fehler"] = str(e)
        st.query_params.clear()
        st.rerun()
    if "error_description" in qp:
        st.session_state["login_fehler"] = qp["error_description"]
        st.query_params.clear()

    nutzer = st.session_state.get("nutzer")
    if nutzer:
        gesperrt = nutzer["email"].lower().endswith(GESPERRTE_DOMAINS)
        freigegeben = nutzer["rolle"] in ERLAUBTE_ROLLEN or nutzer["email"].lower() in gastkonten()
        if not freigegeben or gesperrt:
            st.error("Dieses Konto hat keinen Zugang. Die App ist für Lehrpersonen der bbw — "
                     "bitte mit dem persönlichen Lehrpersonen-Konto anmelden.")
            if st.button("Abmelden"):
                abmelden()
            st.stop()
        return nutzer

    st.title("OLAT-Test erstellen")
    st.write("Anmeldung für Lehrpersonen der bbw mit dem Microsoft-Konto (wie bbw-hko.ch).")
    if fehler := st.session_state.pop("login_fehler", None):
        st.error(fehler)
    # Immer in einem neuen Tab: Streamlit Cloud betreibt die App in einem abgeschotteten Rahmen
    # (sandbox ohne allow-top-navigation). Darin kann weder _self noch _top zu Microsoft führen —
    # Microsoft verbietet das Einbetten, und das Hauptfenster darf der Rahmen nicht umlenken.
    # Im neuen Tab läuft die Anmeldung frei; er wird danach zur angemeldeten App (22.09.2026).
    ziel = login_url()
    st.markdown(f'<a href="{ziel}" target="_blank" rel="noopener" '
                f'style="display:inline-block;padding:.6em 1.2em;background:#2f2f2f;color:#fff;'
                f'border-radius:6px;text-decoration:none">Mit Microsoft anmelden ↗</a>',
                unsafe_allow_html=True)
    st.caption("Die Anmeldung öffnet sich in einem neuen Tab. Nach dem Anmelden arbeiten Sie dort weiter — "
               "dieses Fenster können Sie schliessen.")
    with st.expander("Mit E-Mail und Passwort (Admin- und Testkonten)"):
        with st.form("passwort"):
            email = st.text_input("E-Mail")
            passwort = st.text_input("Passwort", type="password")
            if st.form_submit_button("Anmelden"):
                try:
                    st.session_state["nutzer"] = _mit_passwort(email, passwort)
                    st.rerun()
                except PermissionError as e:
                    st.error(str(e))
    st.stop()


def abmelden() -> None:
    st.session_state.clear()
    st.rerun()
