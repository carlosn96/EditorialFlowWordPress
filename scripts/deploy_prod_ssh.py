#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deploy_prod_ssh.py — Autodespliegue de una entrada WordPress a PRODUCCION
(vía SSH con paramiko + WP-CLI remoto).

A diferencia de deploy_wp.py (que apunta al sitio Local), este script conecta
por SSH al hosting y ejecuta el wp-cli del servidor con `cd <WP_ROOT> && wp
--url=<URL> …`. Así se aplican TODOS los metas de Yoast, sin depender de la
REST API ni de mu-plugins.

Uso:
  py deploy_prod_ssh.py --json workspace/draft-entradas/generados/<slug>/<slug>.wp.json
                       [--dry-run]

Lee del .env de la raiz:
  WP_PROD_HOST, WP_PROD_USER, WP_PROD_PORT, WP_PROD_PASS,
  WP_PROD_KEY_PASSPHRASE, WP_PROD_KEY_FILE, WP_PROD_WP_ROOT, WP_PROD_URL,
  WP_PROD_WP, WP_AUTHOR_ID, WP_PROD_STATUS.

Crea el post en producción con:
  - titulo, slug, extracto, contenido HTML
  - categorías y tags (crea las que falten por nombre)
  - imagen destacada (si es URL publica; import y _thumbnail_id)
  - TODOS los meta de Yoast (bloque "yoast" del .wp.json o defaults):
    title, metadesc (truncada ~156), focuskw, bctitle, is_cornerstone,
    schema_article_type, canonical, OG/Twitter (title/description/image)
  - autor (WP_AUTHOR_ID del .env, no hardcodeado)
  - status (WP_PROD_STATUS)

Devuelve POST_ID y POST_URL.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shlex
import sys
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import paramiko

# La raiz del proyecto se detecta subiendo desde este script hasta encontrar las
# señales del proyecto (wp.ps1, .env o app/public/wp-config.php).
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import config as pipeline_config  # noqa: E402

ROOT = pipeline_config.find_project_root(HERE)


def load_env(path: str) -> dict:
    env = {}
    if not os.path.isfile(path):
        return env
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip("'\"")
    return env


def trim_metadesc(text: str, limit: int = 156) -> str:
    """Recorta una metadescripcion a ~limit chars en un limite de palabra SEO."""
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(".,;:") + "..."


def extraer_clave(key_file: str) -> str | None:
    """Extrae el bloque BEGIN/END del ssh.txt a un archivo temporal."""
    if not os.path.isfile(key_file):
        return None
    with open(key_file, "r", encoding="utf-8", errors="ignore") as f:
        contenido = f.read()
    m = re.search(
        r"-----BEGIN OPENSSH PRIVATE KEY-----.*?-----END OPENSSH PRIVATE KEY-----",
        contenido, re.S,
    )
    if not m:
        return None
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".key", mode="w", encoding="utf-8")
    tmp.write(m.group(0) + "\n")
    tmp.close()
    return tmp.name


def conectar(env: dict):
    host = env.get("WP_PROD_HOST", "")
    user = env.get("WP_PROD_USER", "")
    port = int(env.get("WP_PROD_PORT", "22"))
    password = env.get("WP_PROD_PASS", "")
    passphrase = env.get("WP_PROD_KEY_PASSPHRASE", "") or password
    key_file = env.get("WP_PROD_KEY_FILE", "")

    if not host or not user:
        sys.exit("Faltan WP_PROD_HOST / WP_PROD_USER en .env")

    # Ruta al ssh.txt (si es relativa, relativa a la raiz del proyecto).
    if key_file and not os.path.isabs(key_file):
        key_file = os.path.join(ROOT, key_file)

    ruta_clave = extraer_clave(key_file) if key_file else None

    cliente = paramiko.SSHClient()
    cliente.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        try:
            if ruta_clave:
                cliente.connect(hostname=host, port=port, username=user,
                                key_filename=ruta_clave, passphrase=passphrase,
                                timeout=20, banner_timeout=20, auth_timeout=20,
                                allow_agent=False)
            else:
                raise paramiko.AuthenticationException("sin clave")
        except paramiko.AuthenticationException:
            if not password:
                raise
            cliente.connect(hostname=host, port=port, username=user, password=password,
                            timeout=20, banner_timeout=20, auth_timeout=20,
                            allow_agent=False)
    finally:
        if ruta_clave and os.path.exists(ruta_clave):
            os.unlink(ruta_clave)
    return cliente


def run(cliente, wp_prefix: str, args_str: str) -> tuple[int, str, str]:
    """Ejecuta un comando wp remoto. args_str ya incluye las comillas shell."""
    cmd = f"{wp_prefix} {args_str}".strip()
    stdin, stdout, stderr = cliente.exec_command(cmd, timeout=120)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return 0, out.strip(), err.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="Autodespliega una entrada a PRODUCCION por SSH.")
    ap.add_argument("--json", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--update", action="store_true",
                    help="Si el slug ya existe en produccion, actualizalo en vez de crear un duplicado")
    args = ap.parse_args()

    if not os.path.isfile(args.json):
        sys.exit(f"No existe el JSON: {args.json}")

    env = load_env(os.path.join(ROOT, ".env"))
    wp_root = env.get("WP_PROD_WP_ROOT", "")
    wp_url = env.get("WP_PROD_URL", "")
    wp_cmd = env.get("WP_PROD_WP", "wp")
    author_id = env.get("WP_AUTHOR_ID", "")
    status = env.get("WP_PROD_STATUS", "draft")
    if not wp_root:
        sys.exit("Falta WP_PROD_WP_ROOT en .env")
    if not wp_url:
        sys.exit("Falta WP_PROD_URL en .env")

    # Prefijo remoto: cd <root> && wp --url=<url>
    wp_prefix = f"cd {shlex.quote(wp_root)} && {wp_cmd} --url={shlex.quote(wp_url)}"

    payload = json.load(open(args.json, encoding="utf-8"))
    title = payload.get("post_title", "")
    slug = payload.get("post_name", "")
    excerpt = payload.get("post_excerpt", "")
    content = payload.get("post_content", "")
    cats = payload.get("post_category", []) or []
    tags = payload.get("tags_input", []) or []
    feat = payload.get("featured_image", "")
    yoast = payload.get("yoast", {}) or {}
    metadesc = trim_metadesc(yoast.get("metadesc") or excerpt)
    seo_title = yoast.get("title") or title
    focuskw = yoast.get("focuskw", "") or ""
    bctitle = yoast.get("bctitle", "") or ""
    is_corner = "1" if yoast.get("is_cornerstone") else "0"
    schema_type = yoast.get("schema_article_type", "") or "Article"
    canonical = yoast.get("canonical", "") or ""
    og_title = yoast.get("opengraph-title") or seo_title
    og_desc = yoast.get("opengraph-description") or metadesc
    tw_title = yoast.get("twitter-title") or og_title
    tw_desc = yoast.get("twitter-description") or og_desc

    print(f"[*] Destino: {wp_url} (SSH {env.get('WP_PROD_HOST','')})")
    print(f"[*] Autor ID: {author_id or '(por defecto)'} | Status: {status}")

    # ---- Pre-check de conexion ----
    if args.dry_run:
        print("=== DRY RUN (no se conecta, lista de acciones) ===")
        print(f"  wp_prefix = {wp_prefix}")
        accion = "Actualizar por slug" if args.update else "Crear post"
        print(f"  {accion} con titulo:", title[:60])
        print("  Categorias:", cats)
        print("  Tags:", tags)
        print("  Autor:", author_id)
        print("  Status:", status)
        print("  Metas Yoast:", {k: (v[:40] + '...') if len(str(v)) > 40 else v for k, v in {
            "title": seo_title, "metadesc": metadesc, "focuskw": focuskw,
            "bctitle": bctitle, "is_cornerstone": is_corner,
            "schema_article_type": schema_type, "opengraph-title": og_title,
            "opengraph-description": og_desc, "twitter-title": tw_title,
            "twitter-description": tw_desc, "canonical": canonical}.items()})
        return 0

    cliente = conectar(env)
    try:
        # Pre-check wp: version
        rc, out, err = run(cliente, wp_prefix, "core version")
        print(f"[OK] WP Core {out}")

        # Autor: resolver login -> ID si WP_AUTHOR_ID no es numerico
        aid = author_id
        if aid and not re.fullmatch(r"\d+", aid):
            rc, out, err = run(cliente, wp_prefix, f"user get {shlex.quote(aid)} --field=ID")
            aid = out.strip()
        author_arg = f"--post_author={shlex.quote(aid)}" if aid and re.fullmatch(r"\d+", aid) else ""

        # Resolver categorias (crear si faltan) -> ids.
        cat_ids = []
        for c in cats:
            rc, out, err = run(cliente, wp_prefix, f"term list category --name={shlex.quote(c)} --field=term_id --porcelain")
            cid = out.strip()
            if not re.fullmatch(r"\d+", cid):
                rc, out, err = run(cliente, wp_prefix, f"term create category {shlex.quote(c)} --porcelain")
                cid = out.strip()
            if re.fullmatch(r"\d+", cid):
                cat_ids.append(cid)

        # Modo actualizar: resolver el post existente por slug (evita duplicado).
        pid = ""
        if args.update:
            rc, out, err = run(cliente, wp_prefix,
                               f"post list --name={shlex.quote(slug)} --post_type=post "
                               f"--post_status=any --field=ID --format=csv")
            for line in out.splitlines():
                if re.fullmatch(r"\d+", line.strip()):
                    pid = line.strip()
                    break
            if pid:
                print(f"[*] Modo actualizar: post existente id={pid} (slug={slug})")

        if pid:
            upargs = ["post", "update", pid,
                      f"--post_title={title}", f"--post_excerpt={excerpt}",
                      f"--post_content={content}"]
            if cat_ids:
                upargs.append(f"--post_category={','.join(cat_ids)}")
            if tags:
                upargs.append(f"--tags_input={','.join(tags)}")
            quoted = [shlex.quote(a) for a in upargs]
            rc, out, err = run(cliente, wp_prefix, " ".join(quoted))
        else:
            wpargs = ["post", "create", "--post_type=post", f"--post_status={status}",
                      f"--post_title={title}", f"--post_name={slug}",
                      f"--post_excerpt={excerpt}", "--porcelain"]
            if author_arg:
                wpargs.append(author_arg)
            if cat_ids:
                wpargs.append(f"--post_category={','.join(cat_ids)}")
            if tags:
                wpargs.append(f"--tags_input={','.join(tags)}")
            wpargs.append(f"--post_content={content}")
            quoted = [shlex.quote(a) for a in wpargs]
            rc, out, err = run(cliente, wp_prefix, " ".join(quoted))
            pid = out.strip()
        if not re.fullmatch(r"\d+", pid):
            sys.stderr.write(f"Fallo de despliegue. stdout: {out}\nstderr: {err}\n")
            return 1
        print(f"POST_ID={pid}")

        # Imagen destacada (URL publica; no fatal)
        if feat:
            rc, out, err = run(cliente, wp_prefix, f"media import {shlex.quote(feat)} --post_id={pid} --porcelain")
            att = out.strip()
            if re.fullmatch(r"\d+", att):
                run(cliente, wp_prefix, f"post meta update {pid} _thumbnail_id {att}")
                print(f"THUMB_ID={att}")
            else:
                print("THUMB_WARN: no se pudo importar la imagen destacada (debe ser URL publica)")

        # ---- Meta de Yoast (no fatal) ----
        metas = [
            ("_yoast_wpseo_title", seo_title),
            ("_yoast_wpseo_metadesc", metadesc),
            ("_yoast_wpseo_focuskw", focuskw),
            ("_yoast_wpseo_bctitle", bctitle),
            ("_yoast_wpseo_is_cornerstone", is_corner),
            ("_yoast_wpseo_schema_article_type", schema_type),
            ("_yoast_wpseo_opengraph-title", og_title),
            ("_yoast_wpseo_opengraph-description", og_desc),
            ("_yoast_wpseo_twitter-title", tw_title),
            ("_yoast_wpseo_twitter-description", tw_desc),
        ]
        if cat_ids:
            metas.append(("_yoast_wpseo_primary_category", cat_ids[0]))
        if canonical:
            metas.append(("_yoast_wpseo_canonical", canonical))
        if feat:
            metas.append(("_yoast_wpseo_opengraph-image", feat))
            metas.append(("_yoast_wpseo_twitter-image", feat))

        for meta_key, meta_val in metas:
            rc, out, err = run(cliente, wp_prefix,
                               f"post meta update {pid} {meta_key} {shlex.quote(str(meta_val))}")
            if err and "Error" in err:
                print(f"  [warn] {meta_key}: {err.strip()}")

        rc, out, err = run(cliente, wp_prefix, f"post get {pid} --field=url")
        print(f"POST_URL={out.strip()}")
        print(f"[OK] Publicado en produccion (status={status}, id={pid}).")
    finally:
        cliente.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
