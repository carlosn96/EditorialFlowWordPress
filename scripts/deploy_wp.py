#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deploy_wp.py — Autodespliegue de una entrada WordPress a partir de un .wp.json
generado por build_wp_entry.py.

Uso:
  py deploy_wp.py --json entradas/<slug>.wp.json [--wp ruta/wp.ps1] [--dry-run]
                    [--author 1] [--author-name "<login>"]
                    [--production]

Qué hace:
  1. Crea el post (borrador por defecto) con título, slug, extracto y contenido HTML.
  2. Asigna categorías y etiquetas (tags).
  3. Si hay imagen destacada (URL o ruta local), la importa y la fija como
     _thumbnail_id (imagen destacada).
  4. Aplica los meta de Yoast SEO (bloque "yoast" del .wp.json o defaults):
     _yoast_wpseo_title (acepta templates %%...%%), _yoast_wpseo_metadesc
     (truncada a ~156 caracteres para caber en el preview de Google),
     _yoast_wpseo_focuskw, _yoast_wpseo_bctitle, _yoast_wpseo_is_cornerstone,
     _yoast_wpseo_schema_article_type, _yoast_wpseo_canonical, y las meta
     OpenGraph/Twitter (title/description/image) alineadas con las anteriores.
  5. Asigna el autor del post (--author ID o --author-name login) para que el
     schema Author de Yoast no quede vacio.
  6. Devuelve el ID y la URL del post creado.

  --production despliega en PRODUCCION delegando en deploy_prod_ssh.py
  (paramiko + wp-cli remoto por SSH al hosting), que aplica TODOS los metas de
  Yoast porque el servidor tiene el plugin instalado, sin depender de la REST API.

Requiere que el sitio WordPress local esté iniciado y que el comando WP-CLI
(wrapper `wp.ps1` o `wp` en PATH; o `WP_CLI_COMMAND`) funcione (modo local), o
acceso SSH a producción (modo --production).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile

# La raiz del proyecto se detecta subiendo desde este script hasta encontrar las
# señales del proyecto (wp.ps1, .env o app/public/wp-config.php). El comando de
# WP-CLI local se puede fijar con la variable de entorno WP_CLI_COMMAND.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import config as pipeline_config  # noqa: E402

ROOT = pipeline_config.find_project_root(HERE)
DEFAULT_WP = os.environ.get("WP_CLI_COMMAND") or os.path.join(ROOT, "wp.ps1")


def trim_metadesc(text: str, limit: int = 156) -> str:
    """Recorta una metadescripcion a ~limit chars en un limite de palabra SEO."""
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    # Corta en el ultimo espacio para no partir palabras a mitad.
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(".,;:") + "..."


def build_ps1(payload: dict, content_file: str, wp: str,
              author_id: str = "", author_name: str = "") -> str:
    title = payload.get("post_title", "")
    slug = payload.get("post_name", "")
    excerpt = payload.get("post_excerpt", "")
    status = payload.get("post_status", "draft")
    cats = payload.get("post_category", [])
    tags = payload.get("tags_input", [])
    feat = payload.get("featured_image", "")
    yoast = payload.get("yoast", {}) or {}
    # Metadesc: truncada a 156 chars (cabe en el snippet de Google).
    metadesc = trim_metadesc(yoast.get("metadesc") or excerpt)
    seo_title = yoast.get("title") or title
    focuskw = yoast.get("focuskw", "") or ""
    bctitle = yoast.get("bctitle", "") or ""
    is_corner = yoast.get("is_cornerstone") or 0
    schema_type = yoast.get("schema_article_type", "") or "Article"
    canonical = yoast.get("canonical", "") or ""
    og_title = yoast.get("opengraph-title") or seo_title
    og_desc = yoast.get("opengraph-description") or metadesc
    tw_title = yoast.get("twitter-title") or og_title
    tw_desc = yoast.get("twitter-description") or og_desc
    # Normalizar cornerstone a "1"/"0" (cadena, como lo guarda Yoast).
    is_corner = "1" if is_corner else "0"

    lines = []
    # Modo local: $wp = ruta al wrapper wp.ps1 de la raiz del proyecto.
    # (El modo produccion se delega a deploy_prod_ssh.py desde main()).
    lines.append(f'$wp = "{wp}"')
    lines.append('$ErrorActionPreference = "Continue"')
    # Forzar UTF-8 al pasar argumentos con acentos al proceso nativo (wp-cli):
    # si la consola usa cp1252, los acentes se pierden (>Leon<) o se mojbakean.
    lines.append('[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding')
    # Pre-check de conectividad: si la BD no responde, aborta con mensaje claro
    lines.append('& $wp db check | Out-Null')
    lines.append('if ($LASTEXITCODE -ne 0) {')
    lines.append('  Write-Error "No se puede conectar a la BD de WordPress. Arranca el sitio local y reintenta."')
    lines.append('  exit 1')
    lines.append('}')
    lines.append(f'$status = "{status}"')
    lines.append(f'$slug = "{slug}"')
    lines.append(f'$title = @\'\n{title}\n\'@')
    lines.append(f'$excerpt = @\'\n{excerpt}\n\'@')
    lines.append(f'$content = Get-Content "{content_file}" -Raw -Encoding UTF8')
    # WP-CLI interpretaria las comillas dobles (") como delimitador y partaria el
    # argumento. Se escapan a \" (WP-CLI las restituye a " al asignar el valor).
    lines.append('$content = $content -replace \'"\', \'\\"\'')
    # Resolver el autor del post: prioridad a --author (ID) sobre --author-name
    # (login). Resuelve login -> ID via wp user. Si no llega ninguno, se crea
    # con el autor por defecto (editorial). Evita que el schema Author quede vacio.
    if author_id:
        lines.append(f'$aid = "{author_id}"')
    elif author_name:
        lines.append(f'$aid = (& $wp user get "{author_name}" --field=ID 2>$null).Trim()')
        lines.append('if (-not $aid -match "^\\d+$") { $aid = "" }')
    else:
        lines.append('$aid = ""')
    lines.append('')
    # Crear el post (argumentos base)
    lines.append('$wpargs = @("post","create","--post_type=post",'
                 '"--post_status=$status","--post_title=$title",'
                 '"--post_name=$slug","--post_excerpt=$excerpt",'
                 '"--porcelain")')
    lines.append('if ($aid -match "^\\d+$") { $wpargs += "--post_author=$aid" }')
    # Categorias: resolver el ID sin generar errores si ya existen
    # (term list devuelve el ID; si no existe, se crea). Evita que un
    # "term already exists" benigno aborte el script con ErrorActionPreference.
    lines.append('$primary_cid = ""')
    for c in cats:
        lines.append(f'$cid = (& $wp term list category --name="{c}" --field=term_id --porcelain 2>$null).Trim()')
        lines.append('if (-not ($cid -match "^\\d+$")) {')
        lines.append(f'  $cid = (& $wp term create category "{c}" --porcelain 2>$null).Trim()')
        lines.append('}')
        lines.append('if ($cid -match "^\\d+$") { $wpargs += "--post_category=$cid"; if (-not $primary_cid) { $primary_cid = $cid } }')
    if tags:
        joined = ",".join(tags)
        lines.append(f'$wpargs += "--tags_input={joined}"')
    # El contenido lleva comillas (p.ej. {"level":2}); se concatena como variable
    # para no romper el parseo de la cadena entrecomillada de PowerShell.
    lines.append('$pc = "--post_content=" + $content')
    lines.append('$wpargs = $wpargs + $pc')
    lines.append('$out = & $wp @wpargs')
    lines.append('$id = "$out".Trim()')
    lines.append('if (-not $id) { Write-Error "La creacion del post fallo (sin ID). Revisa wp.ps1 / BD."; exit 1 }')
    lines.append('Write-Host "POST_ID=$id"')
    # Imagen destacada (no fatal)
    if feat:
        lines.append('try {')
        lines.append(f'  $att = (& $wp media import "{feat}" --post_id=$id --porcelain).Trim()')
        lines.append('  & $wp post meta update $id _thumbnail_id $att')
        lines.append('  Write-Host "THUMB_ID=$att"')
        lines.append('} catch { Write-Host "THUMB_WARN: $_" }')
    # ---- Meta SEO (Yoast/RankMath si esta instalado; no fatal) ----
    # Cargar las cadenas SEO (pueden llevar templates %%...%% de Yoast).
    lines.append(f'$seo_title = @\'\n{seo_title}\n\'@')
    lines.append(f'$metadesc = @\'\n{metadesc}\n\'@')
    lines.append(f'$focuskw = @\'\n{focuskw}\n\'@')
    lines.append(f'$bctitle = @\'\n{bctitle}\n\'@')
    lines.append(f'$og_title = @\'\n{og_title}\n\'@')
    lines.append(f'$og_desc = @\'\n{og_desc}\n\'@')
    lines.append(f'$tw_title = @\'\n{tw_title}\n\'@')
    lines.append(f'$tw_desc = @\'\n{tw_desc}\n\'@')
    lines.append('try {')
    lines.append('  & $wp post meta update $id _yoast_wpseo_title $seo_title | Out-Null')
    lines.append('  & $wp post meta update $id _yoast_wpseo_metadesc $metadesc | Out-Null')
    lines.append('  & $wp post meta update $id _yoast_wpseo_focuskw $focuskw | Out-Null')
    lines.append('  & $wp post meta update $id _yoast_wpseo_bctitle $bctitle | Out-Null')
    lines.append('  if ($primary_cid -match "^\\d+$") { & $wp post meta update $id _yoast_wpseo_primary_category $primary_cid | Out-Null }')
    lines.append(f'  & $wp post meta update $id _yoast_wpseo_is_cornerstone {is_corner} | Out-Null')
    lines.append(f'  & $wp post meta update $id _yoast_wpseo_schema_article_type "{schema_type}" | Out-Null')
    lines.append(f'  & $wp post meta update $id _yoast_wpseo_opengraph-title $og_title | Out-Null')
    lines.append('  & $wp post meta update $id _yoast_wpseo_opengraph-description $og_desc | Out-Null')
    lines.append('  & $wp post meta update $id _yoast_wpseo_twitter-title $tw_title | Out-Null')
    lines.append('  & $wp post meta update $id _yoast_wpseo_twitter-description $tw_desc | Out-Null')
    if canonical:
        lines.append(f'  & $wp post meta update $id _yoast_wpseo_canonical "{canonical}" | Out-Null')
    if feat:
        lines.append(f'  & $wp post meta update $id _yoast_wpseo_opengraph-image "{feat}" | Out-Null')
        lines.append(f'  & $wp post meta update $id _yoast_wpseo_twitter-image "{feat}" | Out-Null')
    lines.append('} catch { Write-Host "SEO_PLUGIN_WARN: $_" }')
    lines.append('$url = (& $wp post get $id --field=url).Trim()')
    lines.append('Write-Host "POST_URL=$url"')
    return "\n".join(lines)


def load_env(path):
    """Carga un .env simple (clave=valor, ignora # y vacios)."""
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


def main() -> int:
    ap = argparse.ArgumentParser(description="Autodespliega una entrada WordPress.")
    ap.add_argument("--json", required=True)
    ap.add_argument("--wp", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--author", default="",
                    help="ID de usuario WordPress para el autor del post (evita author vacio en schema)")
    ap.add_argument("--author-name", default="",
                    help="Login de usuario WordPress para el autor del post (se resuelve a ID)")
    ap.add_argument("--production", action="store_true",
                    help="Despliegue a PRODUCCION via SSH. Reenvia a "
                         "deploy_prod_ssh.py (paramiko + wp-cli remoto) usando "
                         "las variables WP_PROD_* del .env.")
    args = ap.parse_args()

    if not os.path.isfile(args.json):
        sys.exit(f"No existe el JSON: {args.json}")

    # La consola de Windows es cp1252; si el stdout de wp-cli trae un
    # U+FFFD (replacement char) el print() crashea. Forzamos UTF-8 en stdout.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    payload = json.load(open(args.json, encoding="utf-8"))
    slug = payload.get("post_name", "entrada")

    # Modo produccion: reenviar a deploy_prod_ssh.py (paramiko + wp-cli remoto)
    # y salir. Es el camino real de despliegue a produccion, verificado.
    if args.production:
        prod = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "deploy_prod_ssh.py")
        cmd = [sys.executable, prod, "--json", args.json]
        if args.dry_run:
            cmd.append("--dry-run")
        return subprocess.call(cmd)

    # Modo local: usar el wrapper wp.ps1 de la raiz.
    wp = args.wp or DEFAULT_WP
    author_id = args.author

    # El contenido se vuelca a un temporal (no se deja .content.html en el area)
    cf = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False,
                                     encoding="utf-8")
    cf.write(payload.get("post_content", ""))
    cf.close()
    content_file = cf.name

    ps1 = build_ps1(payload, content_file, wp, author_id=author_id,
                    author_name=args.author_name)
    if args.dry_run:
        print("=== PowerShell a ejecutar ===")
        print(ps1)
        os.unlink(content_file)
        return 0

    # El .ps1 debe llevar BOM (utf-8-sig): si no, PowerShell lo lee como
    # cp1252 y corrompe (doble-codifica) las cadenas con acentos embebidas
    # (titulo, extracto, etiquetas). El contenido se lee aparte con
    # -Encoding UTF8, por eso ese si salia bien.
    tmp = tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False,
                                      encoding="utf-8-sig")
    tmp.write(ps1)
    tmp.close()
    try:
        proc = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy",
                                "Bypass", "-File", tmp.name],
                              capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
    finally:
        os.unlink(tmp.name)
        os.unlink(content_file)

    if proc.returncode != 0:
        sys.stderr.write((proc.stdout or "") + "\n" + (proc.stderr or ""))
        return proc.returncode
    print(proc.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
