#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install.py — Instala el pipeline editorial (skill + perfil de marca) en un
proyecto WordPress.

Copia en el proyecto destino:
  1. El SKILL y los scripts en `<project-root>/.agents/skills/<skill-name>/`
     (ajusta el `name:` del frontmatter al nombre de la carpeta).
  2. Los perfiles de marca en `<project-root>/brands/`.

Uso:
  py install.py --project-root "C:\\ruta\\al\\proyecto" ^
      [--skill-name comfil-draft-entradas] [--brand comfil | --all-brands]

Sin `--brand` copia todos los perfiles de `brands/`.
El script es idempotente: se puede volver a ejecutar para actualizar.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLE = os.path.dirname(HERE)  # raiz de EditorialFlow
SRC_SKILL = os.path.join(BUNDLE, "skill", "SKILL.md")
SRC_SCRIPTS = HERE
SRC_REFS = os.path.join(BUNDLE, "references")
SRC_BRANDS = os.path.join(BUNDLE, "brands")


def _copy_files(src, dst, pattern=None):
    os.makedirs(dst, exist_ok=True)
    for name in os.listdir(src):
        s = os.path.join(src, name)
        if not os.path.isfile(s):
            continue
        if pattern and not re.search(pattern, name):
            continue
        shutil.copy2(s, os.path.join(dst, name))


def install(project_root: str, skill_name: str, brand: str | None) -> int:
    pr = os.path.abspath(project_root)
    if not os.path.isdir(pr):
        sys.exit(f"No existe el proyecto destino: {pr}")

    # 1) Skill + scripts + references
    skill_dir = os.path.join(pr, ".agents", "skills", skill_name)
    os.makedirs(skill_dir, exist_ok=True)

    # SKILL.md con el `name:` del frontmatter ajustado al nombre de la carpeta.
    if not os.path.isfile(SRC_SKILL):
        sys.exit(f"No encuentro el SKILL en {SRC_SKILL}")
    skill_txt = open(SRC_SKILL, encoding="utf-8-sig").read()
    skill_txt = re.sub(r"(?m)^name:\s*.*$", f"name: {skill_name}", skill_txt, count=1)
    with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as fh:
        fh.write(skill_txt)

    # Scripts (*.py) y references; excluye el propio instalador.
    _copy_files(SRC_SCRIPTS, os.path.join(skill_dir, "scripts"), r"\.py$")
    inst_self = os.path.join(skill_dir, "scripts", "install.py")
    if os.path.isfile(inst_self):
        os.remove(inst_self)
    if os.path.isdir(SRC_REFS):
        _copy_files(SRC_REFS, os.path.join(skill_dir, "references"))

    # 2) Perfiles de marca
    brands_dst = os.path.join(pr, "brands")
    os.makedirs(brands_dst, exist_ok=True)
    if brand:
        src = os.path.join(SRC_BRANDS, brand)
        if not os.path.isdir(src):
            sys.exit(f"No existe el perfil de marca: {src}")
        shutil.copytree(src, os.path.join(brands_dst, brand), dirs_exist_ok=True)
        instaladas = [brand]
    else:
        if os.path.isdir(SRC_BRANDS):
            for b in os.listdir(SRC_BRANDS):
                if os.path.isdir(os.path.join(SRC_BRANDS, b)):
                    shutil.copytree(os.path.join(SRC_BRANDS, b),
                                    os.path.join(brands_dst, b), dirs_exist_ok=True)
        instaladas = [b for b in os.listdir(brands_dst)
                      if os.path.isdir(os.path.join(brands_dst, b))]

    # 3) Verificacion de señales del proyecto
    señales = [f for f in ("wp.ps1", ".env", os.path.join("app", "public", "wp-config.php"))
               if os.path.exists(os.path.join(pr, f))]

    print(f"[OK] Skill instalado en: {skill_dir}")
    print(f"[OK] Perfiles de marca en: {brands_dst} ({', '.join(instaladas) or 'ninguno'})")
    print(f"[i] Señales de proyecto encontradas: {', '.join(señales) or 'ninguna'}")
    print("\nPasos siguientes:")
    print(f"  1) Define la marca activa:  EDITORIALFLOW_BRAND={instaladas[0] if instaladas else '<slug>'}")
    print("     (en el .env del proyecto o en el entorno)")
    print("  2) Requisitos: Python 3 + WP-CLI (wrapper `wp.ps1` o `wp` en PATH);")
    print("     para produccion: `pip install paramiko` y las variables WP_PROD_* en el .env.")
    print("  3) Crea/edita entradas y ejecuta:")
    print(f"     py .agents/skills/{skill_name}/scripts/build_wp_entry.py --help")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Instala el pipeline editorial en un proyecto WordPress.")
    ap.add_argument("--project-root", required=True, help="Ruta del proyecto destino (raiz de WordPress/AGENTS.md).")
    ap.add_argument("--skill-name", default="editorial-flow",
                    help="Nombre de la carpeta del skill en .agents/skills/ (default: editorial-flow).")
    ap.add_argument("--brand", default=None, help="Copiar solo este perfil de marca (default: todos).")
    ap.add_argument("--all-brands", action="store_true", help="Copiar todos los perfiles de marca (default).")
    args = ap.parse_args()
    return install(args.project_root, args.skill_name, args.brand)


if __name__ == "__main__":
    raise SystemExit(main())
