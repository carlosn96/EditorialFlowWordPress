#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deploy_all.py — Despliega en lote todas las entradas ya generadas
(entradas/<slug>/<slug>.wp.json) al sitio WordPress local via deploy_wp.py.

Uso:
  py deploy_all.py [--entradas entradas] [--wp ruta/wp.ps1] [--dry-run]
                   [--author ID] [--author-name login] [--production]

Respeto a volumen: itera cada subfolder y llama al script de despliegue por cada
uno. Por defecto usa deploy_wp.py (sitio local); con --production usa
deploy_prod_ssh.py (produccion via SSH/paramiko). Los flags --author /
--author-name solo aplican al modo local (en produccion el autor se toma del
.env WP_AUTHOR_ID).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    ap = argparse.ArgumentParser(description="Despliega en lote entradas WP.")
    ap.add_argument("--entradas", default="workspace/draft-entradas/generados")
    ap.add_argument("--wp", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--author", default="")
    ap.add_argument("--author-name", default="")
    ap.add_argument("--production", action="store_true")
    args = ap.parse_args()

    entradas = os.path.abspath(args.entradas)
    if not os.path.isdir(entradas):
        sys.exit(f"No existe: {entradas}")

    jobs = []
    for name in sorted(os.listdir(entradas)):
        j = os.path.join(entradas, name, f"{name}.wp.json")
        if os.path.isfile(j):
            jobs.append(j)

    if not jobs:
        print("No hay entradas para desplegar en entradas/.")
        return 0

    ok = 0
    for j in jobs:
        print(f"\n=== Deploy {j} ===")
        # --production usa el script de produccion (paramiko/SSH); si no,
        # el de local (deploy_wp.py).
        script = "deploy_prod_ssh.py" if args.production else "deploy_wp.py"
        cmd = [sys.executable, os.path.join(HERE, script), "--json", j]
        if args.wp and not args.production:
            cmd += ["--wp", args.wp]
        if args.dry_run:
            cmd += ["--dry-run"]
        if args.author and not args.production:
            cmd += ["--author", args.author]
        if args.author_name and not args.production:
            cmd += ["--author-name", args.author_name]
        proc = subprocess.run(cmd)
        if proc.returncode == 0:
            ok += 1

    print(f"\n[OK] {ok}/{len(jobs)} despliegues finalizados (dry-run={args.dry_run}, production={args.production}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
