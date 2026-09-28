#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_all.py — Procesa en lote todas las carpetas de borradores y genera una
entrada WordPress por cada una, cada una en su propio subfolder
(entradas/<slug>/), ademas de un indice manifest.json.

Uso:
  py build_all.py [--root workspace/draft-entradas] [--out entradas]

Por carpeta se espera:
  - un borrador en <carpeta>/reunion/informacion/borrador.md (o <carpeta>/borrador.md)
  - opcionalmente <carpeta>/meta.json (o reunion/informacion/meta.json) con:
      title, slug, excerpt, categories, tags, featured_image, status,
      author, seo_title, seo_description, og_image

Si no hay meta.json, se derivan slug (del nombre de carpeta) y titulo (primer H1).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_wp_entry as be  # reusa la logica de conversion

SKIP_DIRS = {"entradas", "scripts", "reunion", ".agents"}


def _as_csv(value) -> str:
    """Normaliza un valor de meta.json a CSV: acepta string o lista."""
    if isinstance(value, (list, tuple)):
        return ",".join(str(v) for v in value)
    return str(value)


def find_drafts(root: str):
    found = []
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if not os.path.isdir(d) or name in SKIP_DIRS:
            continue
        candidates = [
            os.path.join(d, "informacion", "borrador.md"),
            os.path.join(d, "borrador.md"),
        ]
        draft = next((c for c in candidates if os.path.isfile(c)), None)
        if not draft:
            continue
        meta = {}
        for mp in (os.path.join(d, "meta.json"),
                   os.path.join(d, "informacion", "meta.json")):
            if os.path.isfile(mp):
                meta = json.load(open(mp, encoding="utf-8"))
                break
        found.append((name, d, draft, meta))
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description="Convierte en lote borradores a entradas WP.")
    ap.add_argument("--root", default="workspace/draft-entradas/borradores")
    ap.add_argument("--out", default="workspace/draft-entradas/generados")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        sys.exit(f"No existe el root: {root}")

    entries = find_drafts(root)
    if not entries:
        print("No se encontraron carpetas con borrador.md.")
        return 0

    manifest = {"generated_at": "", "entries": []}
    ok = 0
    for name, d, draft, meta in entries:
        slug = meta.get("slug") or be._slugify(name)
        out_dir = os.path.join(args.out, slug)
        cmd = [sys.executable, os.path.join(HERE, "build_wp_entry.py"),
               "--draft", draft, "--out", args.out, "--slug", slug]
        if meta.get("title"):
            cmd += ["--title", meta["title"]]
        if meta.get("excerpt"):
            cmd += ["--excerpt", meta["excerpt"]]
        if meta.get("categories"):
            cmd += ["--categories", _as_csv(meta["categories"])]
        if meta.get("tags"):
            cmd += ["--tags", _as_csv(meta["tags"])]
        if meta.get("featured_image"):
            cmd += ["--featured-image", meta["featured_image"]]
        if meta.get("schedule"):
            cmd += ["--schedule", _as_csv(meta["schedule"])]
        if meta.get("status"):
            cmd += ["--status", meta["status"]]
        if meta.get("author"):
            cmd += ["--author", meta["author"]]
        if meta.get("seo_title"):
            cmd += ["--seo-title", meta["seo_title"]]
        if meta.get("seo_description"):
            cmd += ["--seo-description", meta["seo_description"]]
        if meta.get("og_image"):
            cmd += ["--og-image", meta["og_image"]]
        # Campos Yoast SEO (desde meta.json; opcionales)
        if meta.get("focus_keyword"):
            cmd += ["--focuskw", meta["focus_keyword"]]
        if meta.get("schema_article_type"):
            cmd += ["--schema-article-type", meta["schema_article_type"]]
        if meta.get("breadcrumb_title"):
            cmd += ["--bctitle", meta["breadcrumb_title"]]
        if meta.get("is_cornerstone"):
            cmd += ["--cornerstone"]
        if meta.get("og_title"):
            cmd += ["--og-title", meta["og_title"]]
        if meta.get("og_description"):
            cmd += ["--og-description", meta["og_description"]]
        if meta.get("twitter_title"):
            cmd += ["--twitter-title", meta["twitter_title"]]
        if meta.get("twitter_description"):
            cmd += ["--twitter-description", meta["twitter_description"]]
        if meta.get("canonical"):
            cmd += ["--canonical", meta["canonical"]]

        print(f"\n=== [{name}] -> {slug} ===")
        proc = subprocess.run(cmd)
        if proc.returncode == 0:
            ok += 1
            manifest["entries"].append({
                "slug": slug,
                "source_folder": d,
                "json": os.path.join(out_dir, f"{slug}.wp.json"),
                "title": meta.get("title", ""),
                "status": meta.get("status", "draft"),
                "categories": meta.get("categories", ""),
                "tags": meta.get("tags", ""),
            })

    # Indice
    import datetime
    manifest["generated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    manifest_path = os.path.join(args.out, "manifest.json")
    os.makedirs(args.out, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    print(f"\n[OK] {ok}/{len(entries)} entradas generadas. Indice: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
