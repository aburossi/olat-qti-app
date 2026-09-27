"""Formelprüfung nach der Umwandlung (27.09.2026).

Drei Stufen, in dieser Reihenfolge:
1. `reparieren(satz)` — was sicher geht, ohne Rückfrage: doppelte Backslashes, Lücke mitten in einer Formel,
   Unicode-Indizes und -Operatoren in Formeln (p₁ → p_1, 10⁵ → 10^{5}, · → \\cdot).
2. `nachbessern(client, modell, befunde)` — was bleibt, geht Feld für Feld mit der Fehlerliste zurück an das
   Modell. Eine Korrektur gilt nur, wenn Lücken und Wortlaut ausserhalb der Formeln gleich bleiben und sie
   weniger Befunde hat.
3. `markieren(befunde)` — was dann noch falsch ist, landet in `unsicher` (⚠ in der Prüftabelle).

Geprüft werden alle Texte eines Fragensatzes im YAML-Format von olatqti.py, auch Sektionseinleitungen.
"""
from __future__ import annotations

import difflib
import json
import re

STELLE = re.compile(r"\{\{.+?\}\}|\[\[\*?.+?\]\]")              # Lücke oder Hottext-Stelle
MATHE = re.compile(r"(?<!\\)\$([^$\n]+?)(?<!\\)\$")             # wie olatqti.INLINE
DOLLAR = re.compile(r"(?<!\\)\$")
DOPPELT = re.compile(r"\\\\(?=[A-Za-z,;:!{}|])")                # wie umwandeln.DOPPELT
BEFEHL = re.compile(r"\\([A-Za-z]+)")
TIEF, HOCH = "₀₁₂₃₄₅₆₇₈₉₊₋ₐₑₒₓₙₘ", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻ⁿ"
TIEF_ZU, HOCH_ZU = "0123456789+-aeoxnm", "0123456789+-n"
INDEX = re.compile(f"([{TIEF}]+)|([{HOCH}]+)")
OPERATOREN = {"·": r"\cdot ", "×": r"\times ", "−": "-", "≤": r"\leq ", "≥": r"\geq ", "≈": r"\approx ",
              "≠": r"\neq ", "±": r"\pm ", "→": r"\rightarrow ", "∞": r"\infty ", "Δ": r"\Delta ", "√": r"\sqrt "}
ARGUMENTE = {"frac": 2, "dfrac": 2, "tfrac": 2, "sqrt": 1, "text": 1, "mathrm": 1, "textrm": 1, "mathbf": 1,
             "vec": 1, "overline": 1, "underline": 1, "hat": 1, "bar": 1, "operatorname": 1, "unit": 1}
# Befehle, die MathJax in OLAT kennt und die in Schulformeln vorkommen; ein anderer ist meist ein Tippfehler
BEKANNT = set(ARGUMENTE) | set("""
alpha beta gamma delta epsilon varepsilon zeta eta theta vartheta iota kappa lambda mu nu xi pi varpi rho varrho
sigma varsigma tau upsilon phi varphi chi psi omega Gamma Delta Theta Lambda Xi Pi Sigma Upsilon Phi Psi Omega
cdot times div pm mp ast star circ bullet cdots ldots dots vdots ddots
leq le geq ge neq ne approx sim simeq equiv propto ll gg in notin subset subseteq supset cup cap emptyset
rightarrow leftarrow Rightarrow Leftarrow leftrightarrow Leftrightarrow to mapsto longrightarrow uparrow downarrow
rightleftharpoons infty partial nabla sum prod int oint lim log ln lg exp sin cos tan cot arcsin arccos arctan
min max degree prime angle perp parallel triangle square forall exists neg land lor
left right big Big bigg Bigg quad qquad displaystyle textstyle mathit mathsf mathcal boldsymbol textbf textit
overrightarrow underbrace overbrace binom tbinom dbinom begin end hline cline limits nolimits
percent space enspace thinspace mathrm text textrm ce pu cancel color textcolor boxed not
det gcd lcm arg deg dim ker hom sec csc sinh cosh tanh coth Pr sup inf liminf limsup mod bmod pmod
mathbb overset underset stackrel cfrac widehat widetilde tilde dot ddot breve check acute grave
langle rangle lceil rceil lfloor rfloor vert Vert lvert rvert lVert rVert mid backslash setminus colon cdotp
because therefore iff implies impliedby oplus otimes ominus odot wedge vee bigcup bigcap bigoplus iint iiint
hbar ell Re Im aleph wp dagger ddagger surd top bot models vdash leadsto
longleftarrow longleftrightarrow Longrightarrow Longleftarrow nearrow searrow nwarrow swarrow updownarrow
leftrightarrows rightrightarrows hookrightarrow uplus sqcup sqcap preceq succeq prec succ cong asymp doteq
nexists varnothing complement lnot neq leqslant geqslant lesssim gtrsim ngeq nleq subsetneq supseteq ni
mathring textsf texttt mathtt tiny small large Large huge phantom hphantom vphantom mathstrut strut
bigl bigr Bigl Bigr biggl biggr middle overleftarrow overleftrightarrow xrightarrow xleftarrow
""".split())


# --------------------------------------------------------------- Felder

def _sektionen(satz: dict) -> list[dict]:
    teile = satz["teile"] if "teile" in satz else [satz]
    out = []
    for t in teile or []:
        if "sektionen" in t:
            out += t["sektionen"] or []
        elif t.get("fragen"):
            out.append(t)  # Satz ohne Sektionen: die Fragen hängen direkt am Satz
    return out


def felder(satz: dict) -> list[dict]:
    """Jedes Textfeld: {traeger (Frage oder Sektion), behaelter, schluessel, ort (für Meldungen)}.
    `behaelter[schluessel]` ist der Text — so lässt er sich an Ort und Stelle ersetzen."""
    out = []

    def dazu(traeger, behaelter, schluessel, ort):
        if isinstance(behaelter[schluessel], str):
            out.append({"traeger": traeger, "behaelter": behaelter, "schluessel": schluessel, "ort": ort})

    for sek in _sektionen(satz):
        name = sek.get("titel") or "Sektion"
        if "text" in sek and sek is not satz:
            dazu(sek, sek, "text", f"{name} — Einleitung")
        for f in sek.get("fragen") or []:
            titel = f.get("titel") or f.get("typ", "?")
            for feld in ("frage", "text", "hinweis", "musterloesung"):
                if isinstance(f.get(feld), dict):
                    dazu(f, f[feld], "text", f"{titel} — {feld}")
                elif feld in f:
                    dazu(f, f, feld, f"{titel} — {feld}")
            for feld in ("antworten", "aussagen", "elemente") + (
                    ("zeilen", "spalten") if isinstance(f.get("zeilen"), list) else ()):
                for i, a in enumerate(f.get(feld) or []):
                    if isinstance(a, dict):
                        dazu(f, a, "text", f"{titel} — {feld} {i + 1}")
                    else:
                        dazu(f, f[feld], i, f"{titel} — {feld} {i + 1}")
    return out


def _setzen(feld: dict, neu: str) -> None:
    """Text ersetzen; bei Matrix-Zeilen/-Spalten auch die Lösung, die über den Text verweist."""
    alt = feld["behaelter"][feld["schluessel"]]
    feld["behaelter"][feld["schluessel"]] = neu
    f = feld["traeger"]
    if feld["behaelter"] is f.get("zeilen") or feld["behaelter"] is f.get("spalten"):
        loesung = f.get("loesung")
        if isinstance(loesung, list):
            f["loesung"] = [[neu if x == alt else x for x in paar] for paar in loesung]
        elif isinstance(loesung, dict):
            f["loesung"] = {(neu if k == alt else k): ([neu if x == alt else x for x in v] if isinstance(v, list)
                                                       else neu if v == alt else v) for k, v in loesung.items()}


# --------------------------------------------------------------- Stufe 1: reparieren

def _index(m: re.Match) -> str:
    if m[1]:
        z = m[1].translate(str.maketrans(TIEF, TIEF_ZU))
        return f"_{z}" if len(z) == 1 else f"_{{{z}}}"
    z = m[2].translate(str.maketrans(HOCH, HOCH_ZU))
    return f"^{z}" if len(z) == 1 else f"^{{{z}}}"


def _formel_reparieren(inhalt: str) -> str:
    inhalt = DOPPELT.sub(lambda _: "\\", inhalt)
    inhalt = INDEX.sub(_index, inhalt)
    for zeichen, ersatz in OPERATOREN.items():
        inhalt = inhalt.replace(zeichen, ersatz)
    return re.sub(r" {2,}", " ", inhalt)


def text_reparieren(text: str) -> str:
    """Sichere Reparaturen in einem Text. Braucht olatqti.formel_um_stellen (Lücke in Formel)."""
    if "$" not in text:
        return text
    if STELLE.search(text):
        import olatqti
        text = "\n".join(olatqti.formel_um_stellen(z, STELLE) for z in text.split("\n"))
    return MATHE.sub(lambda m: f"${_formel_reparieren(m[1])}$", text)


def reparieren(satz: dict) -> int:
    """Stufe 1 an Ort und Stelle; gibt die Anzahl geänderter Felder zurück."""
    n = 0
    for feld in felder(satz):
        alt = feld["behaelter"][feld["schluessel"]]
        neu = text_reparieren(alt)
        if neu != alt:
            _setzen(feld, neu)
            n += 1
    return n


# --------------------------------------------------------------- Prüfen

def _argument(formel: str, i: int) -> int | None:
    """Ende des Arguments ab Position i ({…}, ein Zeichen oder ein Befehl), None wenn keines da ist."""
    while i < len(formel) and formel[i] == " ":
        i += 1
    if i >= len(formel) or not (formel[i].isalnum() or formel[i] in "{\\"):
        return None  # «\frac{p} = 1»: «=» ist kein Argument
    if formel[i] == "{":
        tiefe = 0
        for j in range(i, len(formel)):
            tiefe += {"{": 1, "}": -1}.get(formel[j], 0) if formel[j - 1:j] != "\\" or j == i else 0
            if tiefe == 0:
                return j + 1
        return None
    if formel[i] == "\\":
        m = BEFEHL.match(formel, i)
        return m.end() if m else i + 2
    return i + 1


def formel_befunde(formel: str) -> list[str]:
    out = []
    ohne_escape = re.sub(r"\\[{}]", "", formel)
    if ohne_escape.count("{") != ohne_escape.count("}"):
        out.append("Klammern { } nicht ausgeglichen")
    if len(re.findall(r"\\left\b", formel)) != len(re.findall(r"\\right\b", formel)):
        out.append("\\left ohne passendes \\right")
    if re.findall(r"\\begin\{(\w+\*?)\}", formel) != re.findall(r"\\end\{(\w+\*?)\}", formel):
        out.append("\\begin ohne passendes \\end")
    for m in BEFEHL.finditer(formel):
        name = m[1]
        if name not in BEKANNT:
            out.append(f"unbekannter Befehl \\{name}")
            continue
        pos = m.end()
        if name == "sqrt" and formel[pos:pos + 1] == "[":
            pos = formel.find("]", pos) + 1 or len(formel)
        for _ in range(ARGUMENTE.get(name, 0)):
            ende = _argument(formel, pos)
            if ende is None:
                out.append(f"\\{name} ohne {'zweites ' if name.endswith('frac') and pos > m.end() else ''}Argument")
                break
            pos = ende
    return out


def befunde(text: str) -> list[str]:
    """Formelfehler in einem Text (Lücken und Hottext-Stellen zählen nicht)."""
    if not text:
        return []
    t = STELLE.sub("▢", text)
    out = []
    if len(DOLLAR.findall(t)) % 2:
        out.append("unpaariges $ — eine Formel ist nicht geschlossen oder nicht geöffnet")
    for m in MATHE.finditer(t):
        out += [f"«${m[1]}$»: {b}" for b in formel_befunde(m[1])]
    draussen = MATHE.sub(" ", t)
    if (m := re.search(f"\\w*[{TIEF}{HOCH}]\\w*", draussen)):
        out.append(f"Formel nicht als LaTeX gesetzt («{m[0]}»)")
    if (m := BEFEHL.search(draussen.replace("\\$", "").replace("\\*", ""))) and m[1] in BEKANNT:
        out.append(f"LaTeX-Befehl ausserhalb von $…$ («\\{m[1]}»)")
    return out


def pruefen(satz: dict) -> list[dict]:
    """Felder mit Befunden: das Feld (siehe felder()) plus `befunde`."""
    out = []
    for feld in felder(satz):
        if (b := befunde(feld["behaelter"][feld["schluessel"]])):
            out.append({**feld, "befunde": b})
    return out


# --------------------------------------------------------------- Stufe 2: nachbessern

SYSTEM = """Du korrigierst LaTeX-Formeln in Texten eines OLAT-Tests (OLAT zeigt Formeln mit MathJax).
Zu jedem Text bekommst du die gefundenen Fehler. Korrigiere NUR die fehlerhaften Formeln:
- Der übrige Wortlaut bleibt Zeichen für Zeichen gleich — nichts umformulieren, nichts ergänzen, nichts kürzen.
- Lücken {{…}} und Stellen [[…]] unverändert lassen und NIE in eine Formel setzen: «$V_2 =$ {{#6}} L».
- Jede Formel steht zwischen einem öffnenden und einem schliessenden $. Ein echtes Dollarzeichen ist \\$.
- Formelgrössen mit Index und Formeln im Klartext («p₁ · V₁») als LaTeX setzen: $p_1 \\cdot V_1$.
- Jeden Backslash genau EINMAL schreiben.
Gib für jede id den ganzen korrigierten Text zurück."""

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["korrekturen"],
          "properties": {"korrekturen": {"type": "array", "items": {
              "type": "object", "additionalProperties": False, "required": ["id", "text"],
              "properties": {"id": {"type": "string"}, "text": {"type": "string"}}}}}}


def _wortlaut(text: str) -> str:
    return " ".join(MATHE.sub(" ", STELLE.sub(" ", text)).replace("$", " ").split())


def annehmbar(alt: str, neu: str) -> bool:
    """Korrektur nur, wenn Lücken gleich bleiben, der Wortlaut ausserhalb der Formeln fast gleich ist
    und sie weniger Befunde hat als vorher."""
    if STELLE.findall(alt) != STELLE.findall(neu):
        return False
    if difflib.SequenceMatcher(None, _wortlaut(alt), _wortlaut(neu)).ratio() < 0.9:
        return False
    return len(befunde(neu)) < len(befunde(alt))


def nachbessern(client, modell: str, liste: list[dict]) -> tuple[int, dict]:
    """Stufe 2: ein Aufruf für alle Felder mit Befunden. Gibt (angenommene Korrekturen, Verbrauch) zurück."""
    if not liste:
        return 0, {"eingabe": 0, "ausgabe": 0}
    auftrag = [{"id": str(i), "text": f["behaelter"][f["schluessel"]], "fehler": f["befunde"]}
               for i, f in enumerate(liste)]
    antwort = client.chat.completions.create(
        model=modell,
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": json.dumps(auftrag, ensure_ascii=False, indent=1)}],
        response_format={"type": "json_schema", "json_schema": {"name": "formeln", "strict": True, "schema": SCHEMA}},
    )
    u = antwort.usage
    verbrauch = {"eingabe": u.prompt_tokens, "ausgabe": u.completion_tokens}
    angenommen = 0
    for k in json.loads(antwort.choices[0].message.content)["korrekturen"]:
        if not k["id"].isdigit() or int(k["id"]) >= len(liste):
            continue
        feld = liste[int(k["id"])]
        alt = feld["behaelter"][feld["schluessel"]]
        neu = DOPPELT.sub(lambda _: "\\", k["text"]) if "$" in k["text"] else k["text"]
        if annehmbar(alt, neu):
            _setzen(feld, neu)
            angenommen += 1
    return angenommen, verbrauch


# --------------------------------------------------------------- Stufe 3: markieren

def markieren(liste: list[dict]) -> int:
    """Stufe 3: Befunde in `unsicher` der Frage bzw. Sektion; gibt die Anzahl markierter Träger zurück."""
    je = {}
    for f in liste:
        je.setdefault(id(f["traeger"]), (f["traeger"], []))[1].extend(f"{f['ort']}: {b}" for b in f["befunde"])
    for traeger, meldungen in je.values():
        hinweis = "Formel prüfen — " + "; ".join(meldungen)
        traeger["unsicher"] = f"{traeger['unsicher']} · {hinweis}" if traeger.get("unsicher") else hinweis
    return len(je)
