"""Lettura di config/parametri.yaml senza dipendenze esterne.

Il file dei parametri usa un sottoinsieme ristretto di YAML: sezioni al primo livello, chiavi
al secondo, valori scalari (anche tra doppi apici) oppure liste, in linea ``[a, b]`` o a blocco
con righe ``- voce``. Il vincolo di progetto ammette solo ``requests`` come dipendenza esterna,
quindi PyYAML non è disponibile: questo modulo legge quel sottoinsieme e rifiuta con il numero
di riga qualunque struttura che non riconosce, invece di interpretarla a caso.

Un valore vuoto significa "non ancora noto" (intestazione di parametri.example.yaml): chi lo
richiede con ``require`` riceve un errore che nomina la chiave, mai un valore inventato.
"""

from __future__ import annotations

import re
from pathlib import Path

Value = str | list[str]
Params = dict[str, dict[str, Value]]

_SECTION = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):$")
_KEY = re.compile(r"^  ([A-Za-z_][A-Za-z0-9_]*):(?: (.*))?$")
_ITEM = re.compile(r"^    - (.*)$")


class ParamsError(Exception):
    """Errore di lettura o di valore mancante nel file dei parametri."""


def _strip_comment(line: str) -> str:
    """Toglie un commento ``#`` che non stia dentro doppi apici."""
    in_quotes = False
    for i, ch in enumerate(line):
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == "#" and not in_quotes and (i == 0 or line[i - 1] in " \t"):
            return line[:i].rstrip()
    return line.rstrip()


def _scalar(text: str, lineno: int) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        inner = text[1:-1]
        if '"' in inner or "\\" in inner:
            raise ParamsError(f"riga {lineno}: apici o escape dentro una stringa non gestiti")
        return inner
    if text.startswith(("'", "{", "&", "*", "|", ">")):
        raise ParamsError(f"riga {lineno}: sintassi YAML non gestita: {text!r}")
    return text


def _inline_list(text: str, lineno: int) -> list[str]:
    inner = text.strip()[1:-1].strip()
    if not inner:
        return []
    return [_scalar(part, lineno) for part in inner.split(",")]


def parse(text: str) -> Params:
    """Legge il testo del file dei parametri e restituisce ``{sezione: {chiave: valore}}``."""
    params: Params = {}
    section: str | None = None
    key: str | None = None
    for lineno, raw in enumerate(text.splitlines(), start=1):
        if "\t" in raw:
            raise ParamsError(f"riga {lineno}: tabulazione nell'indentazione")
        line = _strip_comment(raw)
        if not line.strip():
            continue
        if m := _SECTION.match(line):
            section, key = m.group(1), None
            if section in params:
                raise ParamsError(f"riga {lineno}: sezione {section!r} ripetuta")
            params[section] = {}
            continue
        if m := _KEY.match(line):
            if section is None:
                raise ParamsError(f"riga {lineno}: chiave fuori da una sezione")
            key, value = m.group(1), (m.group(2) or "").strip()
            if key in params[section]:
                raise ParamsError(f"riga {lineno}: chiave {section}.{key} ripetuta")
            if value.startswith("["):
                if not value.endswith("]"):
                    raise ParamsError(f"riga {lineno}: lista in linea non chiusa")
                params[section][key] = _inline_list(value, lineno)
            elif value:
                params[section][key] = _scalar(value, lineno)
            else:
                # Vuoto: resta stringa vuota salvo righe "- voce" che lo trasformano in lista.
                params[section][key] = ""
            continue
        if m := _ITEM.match(line):
            if section is None or key is None:
                raise ParamsError(f"riga {lineno}: voce di lista senza chiave")
            current = params[section][key]
            if current == "":
                current = []
                params[section][key] = current
            if not isinstance(current, list):
                raise ParamsError(f"riga {lineno}: voce di lista sotto un valore scalare")
            current.append(_scalar(m.group(1), lineno))
            continue
        raise ParamsError(f"riga {lineno}: struttura non riconosciuta: {raw.strip()!r}")
    return params


def load(path: str | Path) -> Params:
    """Legge il file dei parametri da disco."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ParamsError(
            f"{path}: file assente; copiarlo da config/parametri.example.yaml e compilarlo"
        ) from None
    return parse(text)


def lookup(params: Params, dotted: str) -> Value:
    """Valore di ``sezione.chiave``, vuoto compreso; errore se la chiave non esiste."""
    section, _, key = dotted.partition(".")
    if not key or section not in params or key not in params[section]:
        raise ParamsError(f"{dotted}: chiave inesistente in parametri.yaml")
    return params[section][key]


def is_empty(value: Value) -> bool:
    return value == "" or value == []


def require(params: Params, dotted: str) -> Value:
    """Come ``lookup``, ma un valore vuoto è un errore: non si inventano valori dell'ambiente."""
    value = lookup(params, dotted)
    if is_empty(value):
        raise ParamsError(f"{dotted}: valore vuoto in parametri.yaml, va compilato")
    return value
