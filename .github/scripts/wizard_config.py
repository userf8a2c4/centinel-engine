#!/usr/bin/env python3
"""
Wizard step: write country config, generate endpoints/sources, and
produce web/data/departments.json for the UI panels.

Called by setup-wizard.yml with CENTINEL_COUNTRY env var set.
Reads src/centinel/countries.py as the single source of truth.
"""
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
    _use_yaml = True
except ImportError:
    _use_yaml = False

COUNTRY = os.environ.get("CENTINEL_COUNTRY", "HN")
YEAR    = os.environ.get("CENTINEL_YEAR", "2025")

# ── Load country preset ────────────────────────────────────────────────────
repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root / "src"))

preset = None
try:
    from centinel.countries import LATAM_COUNTRIES
    preset = LATAM_COUNTRIES.get(COUNTRY)
    if preset:
        print(f"✓ Loaded preset for {COUNTRY}: {preset.name} ({len(preset.divisions)} divisions)")
    else:
        print(f"WARNING: No preset for {COUNTRY}, using bare config")
except Exception as e:
    print(f"WARNING: countries.py not available ({e}), using bare config")


def _slugify(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")


def _abbr(name: str, iso: str | None) -> str:
    """Return 2-3 char abbreviation: use ISO suffix if available, else initials."""
    if iso and "-" in iso:
        return iso.split("-", 1)[1].upper()
    # initials of "significant" words (skip: de, la, las, los, el, a, y)
    skip = {"de", "la", "las", "los", "el", "a", "y", "del"}
    words = [w for w in name.split() if w.lower() not in skip]
    if len(words) >= 2:
        return "".join(w[0] for w in words[:3]).upper()
    return name[:2].upper()


# ── Build departments list ─────────────────────────────────────────────────
def build_departments():
    if not preset:
        return [{"code": "00", "name": "TODOS", "abbr": "NAC", "iso": None, "url": None}]

    cne_map = preset.build_cne_map()   # {"00": "TODOS", "01": "Atlántida", ...}
    isos    = preset.division_iso_codes or []
    pattern = preset.url_pattern or ""
    nat_url = preset.national_url or ""

    depts = []
    # National first
    depts.append({
        "code":  preset.national_cne_code,
        "name":  "TODOS",
        "abbr":  "NAC",
        "iso":   None,
        "url":   nat_url,
        "label": preset.divisions_label,
    })
    # Divisions
    for i, (div_name, cne_code) in enumerate(
        sorted((name, code) for code, name in cne_map.items() if code != preset.national_cne_code)
    ):
        # find iso by matching division name
        iso = None
        try:
            idx = preset.divisions.index(div_name)
            iso = isos[idx] if idx < len(isos) else None
        except ValueError:
            pass

        url = pattern.replace("{cne_code}", cne_code) if pattern else ""
        depts.append({
            "code": cne_code,
            "name": div_name,
            "abbr": _abbr(div_name, iso),
            "iso":  iso,
            "url":  url,
        })
    return depts


# ── 1. Write web/data/departments.json ────────────────────────────────────
depts = build_departments()
dept_json = {
    "country":        COUNTRY,
    "country_name":   preset.name        if preset else COUNTRY,
    "flag":           preset.flag        if preset else "",
    "authority":      preset.authority   if preset else "",
    "divisions_label": preset.divisions_label if preset else "Divisiones",
    "year":           YEAR,
    "generated_at":   datetime.now(timezone.utc).isoformat(),
    "departments":    depts,
}

dept_path = Path("web/data/departments.json")
dept_path.parent.mkdir(parents=True, exist_ok=True)
dept_path.write_text(json.dumps(dept_json, ensure_ascii=False, indent=2))
print(f"✓ web/data/departments.json — {len(depts)} entries")


# ── 2. Update command_center/config.yaml ─────────────────────────────────
cfg_path = Path("command_center/config.yaml")

if _use_yaml and cfg_path.exists():
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
else:
    cfg = {}

# centinel metadata
cfg.setdefault("centinel", {})
cfg["centinel"]["country"]      = COUNTRY
cfg["centinel"]["year"]         = YEAR
cfg["centinel"]["setup_at"]     = datetime.now(timezone.utc).isoformat()
cfg["centinel"]["setup_source"] = "github-actions-wizard"

if preset:
    # cne_domains — extract host from url_pattern or national_url
    base = preset.national_url or preset.url_pattern or ""
    m = re.search(r"https?://([^/]+)", base)
    if m:
        cfg["cne_domains"] = [m.group(1)]

    # base_url
    cfg["base_url"] = preset.national_url or ""

    # endpoints block
    endpoints = {}
    if preset.national_url:
        endpoints["nacional"] = preset.national_url
    for d in depts:
        if d["code"] != preset.national_cne_code and d["url"]:
            endpoints[d["code"]] = d["url"]
    cfg["endpoints"] = endpoints

    # sources block
    sources = [{"name": "Nacional", "source_id": "NACIONAL",
                "level": "PRES", "scope": "NATIONAL"}]
    for d in depts:
        if d["code"] == preset.national_cne_code:
            continue
        slug = _slugify(d["name"])
        sources.append({
            "name":            d["name"],
            "source_id":       f"{d['code']}_{slug}",
            "department_code": d["code"],
            "level":           "PRES",
            "scope":           "DEPARTMENT",
        })
    cfg["sources"] = sources
    print(f"✓ config.yaml — {len(endpoints)} endpoints, {len(sources)} sources")

cfg_path.parent.mkdir(parents=True, exist_ok=True)
if _use_yaml:
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    print(f"✓ command_center/config.yaml updated")
else:
    existing = cfg_path.read_text() if cfg_path.exists() else ""
    if "centinel:" not in existing:
        cfg_path.write_text(existing + f"\ncentinel:\n  country: {COUNTRY}\n")


# ── 3. Update config/prod/endpoints.yaml ─────────────────────────────────
ep_path = Path("config/prod/endpoints.yaml")
if _use_yaml and ep_path.exists():
    ep_cfg = yaml.safe_load(ep_path.read_text()) or {}
else:
    ep_cfg = {}

ep_cfg.setdefault("cne", {})
if preset:
    if preset.national_url:
        ep_cfg["cne"]["main_url"] = preset.national_url
    # presidential_endpoints list for the OPS panel
    ep_cfg["cne"]["presidential_endpoints"] = [
        {"department_code": int(d["code"]), "url": d["url"]}
        for d in depts
        if d["code"] != preset.national_cne_code and d["url"]
    ]
    print(f"✓ config/prod/endpoints.yaml — {len(ep_cfg['cne']['presidential_endpoints'])} dept endpoints")

if _use_yaml:
    ep_path.write_text(yaml.safe_dump(ep_cfg, sort_keys=False, allow_unicode=True))

print(f"✓ All config files updated for {COUNTRY}")
