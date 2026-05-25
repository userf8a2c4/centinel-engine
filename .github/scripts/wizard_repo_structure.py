#!/usr/bin/env python3
"""
Wizard step: create organized folder structure in centinel-data repo.

Uses the Git Trees API to push all folders in a single commit.
Reads country/department data from centinel/countries.py.

Environment variables required:
  DATA_REPO_TOKEN   — PAT with repo scope for the data repo
  REPO_OWNER        — GitHub username
  CENTINEL_COUNTRY  — country code (HN, GT, ...)
  CENTINEL_YEAR     — election year
"""

import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

TOKEN   = os.environ["DATA_REPO_TOKEN"]
OWNER   = os.environ["REPO_OWNER"]
COUNTRY = os.environ.get("CENTINEL_COUNTRY", "HN")
YEAR    = os.environ.get("CENTINEL_YEAR", "2025")
REPO    = "centinel-data"
API     = "https://api.github.com"

HEADERS = {
    "Authorization":        f"Bearer {TOKEN}",
    "Content-Type":         "application/json",
    "Accept":               "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


# ── HTTP helpers ───────────────────────────────────────────────────────────────

def gh(method, path, data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(
        f"{API}{path}", data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"GitHub API {method} {path} → {e.code}: {body[:200]}")


def gh_safe(method, path, data=None):
    """Same as gh() but returns None on 422 (already exists)."""
    try:
        return gh(method, path, data)
    except RuntimeError as e:
        if "422" in str(e):
            return None
        raise


# ── Department slugs ───────────────────────────────────────────────────────────

def slugify(name):
    n = unicodedata.normalize("NFD", name)
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-")


def get_departments():
    """Return list of (cne_code, slug) for the selected country."""
    # Try to load from centinel.countries (repo is checked out)
    try:
        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "src"))
        from centinel.countries import LATAM_COUNTRIES
        preset = LATAM_COUNTRIES.get(COUNTRY)
        if preset:
            cne_map = preset.build_cne_map()
            return [
                (code, slugify(name))
                for code, name in sorted(cne_map.items())
                if code != preset.national_cne_code
            ]
    except Exception as e:
        print(f"Warning: countries.py not available ({e}), using HN fallback")

    # HN hardcoded fallback
    return [
        ("01", "atlantida"), ("02", "choluteca"), ("03", "colon"),
        ("04", "comayagua"), ("05", "copan"), ("06", "cortes"),
        ("07", "el-paraiso"), ("08", "francisco-morazan"),
        ("09", "gracias-a-dios"), ("10", "intibuca"),
        ("11", "islas-de-la-bahia"), ("12", "la-paz"),
        ("13", "lempira"), ("14", "ocotepeque"), ("15", "olancho"),
        ("16", "santa-barbara"), ("17", "valle"), ("18", "yoro"),
    ]


# ── Build file tree ────────────────────────────────────────────────────────────

GITKEEP = ""   # empty file — GitHub needs content to track folder
README_DEPT = "# {name}\n\nDatos electorales del departamento {name} ({code}).\n"

def build_tree(depts):
    """Return list of {path, content} dicts for the full repo structure."""
    files = []

    def add(path, content=""):
        files.append({"path": path, "content": content})

    # ── snapshots/ ──────────────────────────────────────────────────────────
    add("snapshots/nacional/.gitkeep")
    for code, slug in depts:
        add(f"snapshots/departamentos/{code}-{slug}/.gitkeep")

    # ── hashes/ ─────────────────────────────────────────────────────────────
    add("hashes/nacional/.gitkeep")
    for code, slug in depts:
        add(f"hashes/departamentos/{code}-{slug}/.gitkeep")

    # ── checkpoints/ ────────────────────────────────────────────────────────
    add("checkpoints/.gitkeep")
    add("checkpoints/latest.json", json.dumps({
        "country": COUNTRY, "year": YEAR,
        "merkle_root": None, "chain_length": 0,
        "generated_at": None,
    }, indent=2))

    # ── reports/ ────────────────────────────────────────────────────────────
    add("reports/anomalias/.gitkeep")
    add("reports/resumen/.gitkeep")
    add("reports/alertas/.gitkeep")

    # ── observer-packs/ ─────────────────────────────────────────────────────
    add("observer-packs/.gitkeep")

    # ── web/ ────────────────────────────────────────────────────────────────
    add("web/data/snapshot.json", json.dumps({
        "country": COUNTRY, "year": YEAR,
        "timestamp_utc": None, "actas": {},
        "votos_totales": {}, "candidatos": [],
        "hash": None,
    }, indent=2))
    add("web/data/departments/.gitkeep")

    # ── README ──────────────────────────────────────────────────────────────
    dept_list = "\n".join(
        f"| `{code}` | {slug.replace('-', ' ').title()} | "
        f"`snapshots/departamentos/{code}-{slug}/` |"
        for code, slug in depts
    )
    readme = (
        f"# centinel-data — {COUNTRY} {YEAR}\n\n"
        f"Datos públicos de auditoría electoral.\n"
        f"Publicados automáticamente por [Centinel](https://github.com/VectisDev/centinel).\n\n"
        f"## Estructura\n\n"
        f"```\n"
        f"snapshots/\n"
        f"  nacional/          ← JSON del CNE nivel nacional\n"
        f"  departamentos/\n"
        f"    01-atlantida/    ← JSON del CNE por departamento\n"
        f"    ...\n"
        f"hashes/              ← Hash chain SHA-256 por nivel\n"
        f"checkpoints/         ← Merkle roots para federación P2P\n"
        f"reports/             ← Análisis estadístico de anomalías\n"
        f"observer-packs/      ← Paquetes para observadores\n"
        f"web/data/            ← JSON consolidado para el panel público\n"
        f"```\n\n"
        f"## Departamentos / Estados\n\n"
        f"| Código CNE | Nombre | Ruta |\n"
        f"|---|---|---|\n"
        f"| `00` | Nacional (TODOS) | `snapshots/nacional/` |\n"
        f"{dept_list}\n\n"
        f"---\n"
        f"*Generado automáticamente por el Setup Wizard de Centinel.*\n"
    )
    add("README.md", readme)

    return files


# ── Push via Git Trees API (single commit) ────────────────────────────────────

def push_tree(files):
    base = f"/repos/{OWNER}/{REPO}"

    # 1. Get current HEAD
    ref = gh("GET", f"{base}/git/refs/heads/main")
    head_sha = ref["object"]["sha"]
    base_tree = gh("GET", f"{base}/git/commits/{head_sha}")["tree"]["sha"]

    # 2. Build tree blobs
    tree_items = []
    for f in files:
        blob = gh("POST", f"{base}/git/blobs", {
            "content":  f["content"],
            "encoding": "utf-8",
        })
        tree_items.append({
            "path": f["path"],
            "mode": "100644",
            "type": "blob",
            "sha":  blob["sha"],
        })

    # 3. Create tree
    new_tree = gh("POST", f"{base}/git/trees", {
        "base_tree": base_tree,
        "tree":      tree_items,
    })

    # 4. Create commit
    commit = gh("POST", f"{base}/git/commits", {
        "message": f"init: estructura organizada por departamentos ({COUNTRY} {YEAR})",
        "tree":    new_tree["sha"],
        "parents": [head_sha],
    })

    # 5. Update HEAD
    gh("PATCH", f"{base}/git/refs/heads/main", {
        "sha": commit["sha"],
    })

    print(f"✓ {len(files)} archivos commiteados en un solo commit: {commit['sha'][:10]}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    depts = get_departments()
    print(f"País: {COUNTRY} — {len(depts)} departamentos/estados")
    for code, slug in depts:
        print(f"  {code} → {slug}")

    files = build_tree(depts)
    print(f"\nCreando {len(files)} archivos en {OWNER}/{REPO}…")
    push_tree(files)
    print("✓ Estructura del repo de datos creada correctamente.")


if __name__ == "__main__":
    main()
