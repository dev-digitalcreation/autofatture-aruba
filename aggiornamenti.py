# -*- coding: utf-8 -*-
"""
Controllo aggiornamenti tramite le Release di GitHub.

- controlla(owner, repo, token) -> dict con tag, se e' piu' recente, note, url installer
- scarica_installer(info, token) -> percorso del file .exe scaricato
- avvia_installer(path) -> lancia l'installer

Per repository PRIVATO serve un token GitHub (Personal Access Token, scope 'repo').
Per repository PUBBLICO il token non serve.
"""
import os
import re
import sys
import json
import tempfile
import subprocess
import urllib.request

import version

API_LATEST = "https://api.github.com/repos/{owner}/{repo}/releases/latest"
API_LIST = "https://api.github.com/repos/{owner}/{repo}/releases?per_page=30"


def _parse(v: str):
    """SemVer -> chiave ordinabile. Release > pre-release a parita' di numeri."""
    v = (v or "").lstrip("vV").strip()
    core, _, pre = v.partition("-")
    nums = [int(x) for x in re.findall(r"\d+", core)[:3]]
    nums += [0] * (3 - len(nums))
    if not pre:
        return (tuple(nums), (1,))                    # nessun pre -> versione finale (maggiore)
    parts = []
    for p in pre.split("."):
        parts.append((0, int(p)) if p.isdigit() else (1, p))
    return (tuple(nums), (0, tuple(parts)))            # pre-release (minore della finale)


def e_piu_recente(corrente: str, candidata: str) -> bool:
    """True se 'candidata' e' piu' recente di 'corrente'."""
    try:
        return _parse(corrente) < _parse(candidata)
    except Exception:
        return False


def _fetch(url: str, token: str = ""):
    req = urllib.request.Request(
        url, headers={"Accept": "application/vnd.github+json", "User-Agent": "Reversa"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read().decode("utf-8"))


def controlla(owner: str, repo: str, token: str = "") -> dict:
    if not owner or not repo:
        raise ValueError("Repository non configurato (owner/repo in version.py).")
    # Elenca le release: a differenza di /releases/latest, questo endpoint INCLUDE
    # anche le prerelease (beta). Scegliamo la versione SemVer piu' alta pubblicata,
    # scartando solo le bozze (draft).
    releases = _fetch(API_LIST.format(owner=owner, repo=repo), token)
    if isinstance(releases, dict):                       # difensivo
        releases = [releases]
    rel = None
    for r in releases:
        if r.get("draft"):
            continue
        if rel is None or _parse(r.get("tag_name", "")) > _parse(rel.get("tag_name", "")):
            rel = r
    if rel is None:                                      # nessuna release pubblicata
        return {"tag": "", "nuova": False, "note": "", "html_url": "",
                "asset_download": None, "asset_api": None}
    inst = None
    for a in rel.get("assets", []):
        if a.get("name", "").lower().endswith(".exe"):
            inst = a
            break
    tag = rel.get("tag_name", "")
    return {
        "tag": tag,
        "nuova": bool(tag) and e_piu_recente(version.__version__, tag),
        "note": rel.get("body", "") or "",
        "html_url": rel.get("html_url", ""),
        "asset_download": (inst or {}).get("browser_download_url"),
        "asset_api": (inst or {}).get("url"),
    }


def scarica_installer(info: dict, token: str = "", dest_dir: str = None) -> str:
    dest_dir = dest_dir or tempfile.gettempdir()
    if token and info.get("asset_api"):               # repo privato: API asset + octet-stream
        url = info["asset_api"]
        headers = {"Accept": "application/octet-stream", "Authorization": f"Bearer {token}",
                   "User-Agent": "Reversa"}
    else:                                             # repo pubblico
        url = info.get("asset_download")
        headers = {"User-Agent": "Reversa"}
    if not url:
        raise RuntimeError("Nessun installer (.exe) allegato alla release.")
    dest = os.path.join(dest_dir, "Reversa_Setup.exe")
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        f.write(r.read())
    return dest


def avvia_installer(path: str):
    if sys.platform.startswith("win"):
        os.startfile(path)  # noqa
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


if __name__ == "__main__":
    print(controlla(version.GITHUB_OWNER, version.GITHUB_REPO))
