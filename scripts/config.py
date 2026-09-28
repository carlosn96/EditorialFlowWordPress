#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config.py — Resolución de MARCA y SITIO para el pipeline (agnóstico).

Separa el MOTOR (scripts) del PERFIL de marca/sitio. Un perfil vive en:

    brands/<slug>/
        brand.json      # identidad (nombre, full_name, aliases, audiencia)
        site.json       # internal_domains, author, default_schema_article_type
        brand-voice.md  # voz/tono de la marca

Orden de resolución del slug:
    --brand (CLI)  >  env EDITORIALFLOW_BRAND  >  DEFAULT_BRAND

Orden de resolución de la carpeta `brands/`:
    env EDITORIALFLOW_BRANDS_DIR  >  <project_root>/brands  >  <skill_dir>/brands

Overrides por entorno (opcionales):
    SITE_DOMAINS      dominios internos separados por coma
    WP_AUTHOR_NAME    autor por defecto
"""
from __future__ import annotations

import json
import os

DEFAULT_BRAND = "comfil"  # fallback de compatibilidad; define EDITORIALFLOW_BRAND para cambiarlo


def find_project_root(start: str) -> str:
    """Sube desde `start` hasta encontrar la raiz del proyecto WordPress.

    Señales: `wp.ps1`, `.env` o `app/public/wp-config.php`. Si no encuentra,
    devuelve `start` tal cual."""
    d = os.path.abspath(start)
    for _ in range(10):
        if (os.path.isfile(os.path.join(d, "wp.ps1"))
                or os.path.isfile(os.path.join(d, ".env"))
                or os.path.isfile(os.path.join(d, "app", "public", "wp-config.php"))):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return os.path.abspath(start)


def find_brands_dir(script_dir: str) -> str:
    env = os.environ.get("EDITORIALFLOW_BRANDS_DIR")
    if env:
        return env
    root = find_project_root(script_dir)
    cand = os.path.join(root, "brands")
    if os.path.isdir(cand):
        return cand
    cand2 = os.path.join(os.path.dirname(os.path.abspath(script_dir)), "brands")
    if os.path.isdir(cand2):
        return cand2
    return cand


def brand_slug(explicit: str | None = None) -> str:
    return explicit or os.environ.get("EDITORIALFLOW_BRAND") or DEFAULT_BRAND


def load_config(script_dir: str, brand: str | None = None) -> dict:
    """Devuelve la config resuelta de la marca activa (con defaults sensatos)."""
    slug = brand_slug(brand)
    brands_dir = find_brands_dir(script_dir)
    bdir = os.path.join(brands_dir, slug)
    cfg = {
        "brand": slug,
        "brands_dir": brands_dir,
        "brand_dir": bdir,
        "name": slug,
        "full_name": slug,
        "aliases": [],
        "audience": "",
        "internal_domains": [],
        "author": "",
        "default_schema_article_type": "Article",
        "brand_voice": os.path.join(bdir, "brand-voice.md"),
    }

    bj = os.path.join(bdir, "brand.json")
    if os.path.isfile(bj):
        try:
            d = json.load(open(bj, encoding="utf-8"))
            for k in ("name", "full_name", "aliases", "audience"):
                if k in d:
                    cfg[k] = d[k]
        except Exception:
            pass

    sj = os.path.join(bdir, "site.json")
    if os.path.isfile(sj):
        try:
            d = json.load(open(sj, encoding="utf-8"))
            for k in ("internal_domains", "author", "default_schema_article_type"):
                if k in d:
                    cfg[k] = d[k]
        except Exception:
            pass

    # Overrides por entorno
    if os.environ.get("SITE_DOMAINS"):
        cfg["internal_domains"] = [x.strip() for x in os.environ["SITE_DOMAINS"].split(",") if x.strip()]
    if os.environ.get("WP_AUTHOR_NAME"):
        cfg["author"] = os.environ["WP_AUTHOR_NAME"]

    if not os.path.isfile(cfg["brand_voice"]):
        cfg["brand_voice"] = None
    return cfg


if __name__ == "__main__":
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    print(json.dumps(load_config(here), ensure_ascii=False, indent=2))
