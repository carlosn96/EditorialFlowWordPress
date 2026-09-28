#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_wp_entry.py — Convierte un borrador (Markdown) en un artefacto desplegable
en WordPress, con todos los atributos que una entrada necesita.

Uso:
  py build_wp_entry.py --draft ruta/borrador.md \
      --title "Título" --slug "mi-entrada" \
      --excerpt "Resumen SEO..." \
      --categories "Comunicación,Iglesia" \
      --tags "Papa León XIV,Perú,Voluntariado" \
      --featured-image "https://.../img.jpg" \
      --status draft --out entradas

Salidas (en --out):
  <slug>.wp.json   -> payload completo de la entrada (autodespliegue)
  <slug>.html      -> contenido HTML compatible con el editor de WordPress
  <slug>.deploy.ps1-> script de despliegue listo para ejecutar (wp-cli)

El JSON incluye: post_title, post_name, post_content (HTML), post_excerpt,
post_status, post_category, tags_input, featured_image y meta (SEO/OG).
Esto es lo que consume deploy_wp.py para el autodespliegue.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import unicodedata


# --------------------------------------------------------------------------- #
# Markdown -> HTML (compatible WordPress / Gutenberg)
# --------------------------------------------------------------------------- #
def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "entrada"


def _href_normalizado(url: str) -> str:
    """Convierte las URLs internas de COMFIL (Local o produccion) en rutas
    relativas (/ruta/), y deja el resto igual. Asi los enlaces internos del
    sitio funcionan en cualquier entorno (local y produccion)."""
    u = url.rstrip(".,;:!?")
    m = re.match(r"^https?://(?:comfil-local\.local|comfil\.edu\.mx)(/.*)$", u)
    if m:
        return m.group(1) or "/"
    return u


def _inline(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

    # 1) Genera los enlaces y los protege con tokens para que el enfasis
    #    (*, _) posterior no toque los caracteres especiales de las URLs
    #    (p. ej. guiones bajos como en ..._13.html).
    links: dict[str, str] = {}
    def _link(m):
        href = _href_normalizado(m.group(2))
        token = f"\x00L{len(links)}\x00"
        links[token] = f'<a href="{href}" target="_blank" rel="noopener">{m.group(1)}</a>'
        return token

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _link, text)

    # 2) Enfasis (negrita / cursiva) sobre el texto, ya sin URLs expuestas.
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"_([^_]+)_", r"<em>\1</em>", text)

    # 3) Reinserta los enlaces protegidos.
    for token, html_link in links.items():
        text = text.replace(token, html_link)
    return text


def _youtube_embed_id(url: str) -> str | None:
    """Extrae el ID de un video de YouTube a partir de una URL, o None si no
    es una URL de YouTube de video (watch, youtu.be, o embed)."""
    m = re.search(r"(?:youtube\.com/watch\?[^#\s]*v=|youtube\.com/embed/|youtu\.be/)([A-Za-z0-9_-]{6,})", url)
    if m:
        vid = m.group(1)
        if not re.fullmatch(r"[A-Za-z0-9_-]{6,}", vid):
            return None
        return vid
    # YouTube Shorts
    m = re.search(r"youtube\.com/shorts/([A-Za-z0-9_-]{6,})", url)
    return m.group(1) if m else None


def _auto_embed_youtube(md: str) -> str:
    """Convierte en <iframe> las URLs de YouTube que esten SOLAS en su propia
    linea (indicio de un video a insertar, no una mencion en una frase).
    Determinista: usa exactamente el ID que ya esta en el texto, nunca inventa."""
    out = []
    for line in md.splitlines():
        u = line.strip()
        vid = _youtube_embed_id(u)
        if vid and (" " not in u):
            out.append(
                f'<iframe width="560" height="315" '
                f'src="https://www.youtube.com/embed/{vid}" '
                f'title="Video de YouTube" frameborder="0" '
                f'allow="accelerometer; autoplay; clipboard-write; encrypted-media; '
                f'gyroscope; picture-in-picture" allowfullscreen loading="lazy">'
                f'</iframe>'
            )
        else:
            out.append(line)
    return "\n".join(out)


def _render_table(rows: list[str]) -> str:
    def cells(r: str):
        return [c.strip() for c in r.strip().strip("|").split("|")]
    head = cells(rows[0])
    body = [cells(r) for r in rows[2:] if r.strip().startswith("|")]
    out = ["<table>", "<thead><tr>"]
    out += [f"<th>{_inline(c)}</th>" for c in head]
    out.append("</tr></thead><tbody>")
    for r in body:
        out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def md_to_html(md: str) -> str:
    lines = md.splitlines()
    html: list[str] = []
    in_ul = in_ol = False

    def close_lists():
        nonlocal in_ul, in_ol
        if in_ul:
            html.append("</ul>")
            in_ul = False
        if in_ol:
            html.append("</ol>")
            in_ol = False

    i = 0
    while i < len(lines):
        line = lines[i]
        # Tabla
        if (line.strip().startswith("|") and i + 1 < len(lines)
                and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1])):
            tbl = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                tbl.append(lines[i])
                i += 1
            html.append(_render_table(tbl))
            continue
        # Encabezados
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            close_lists()
            level = len(m.group(1))
            html.append(f"<h{level}>{_inline(m.group(2).strip())}</h{level}>")
            i += 1
            continue
        if line.startswith("> "):
            close_lists()
            html.append(f"<blockquote><p>{_inline(line[2:].strip())}</p></blockquote>")
            i += 1
            continue
        if line.strip() in ("---", "***", "___"):
            close_lists()
            html.append("<hr />")
            i += 1
            continue
        if re.match(r"^\s*[-*]\s+", line):
            if not in_ul:
                close_lists()
                html.append("<ul>")
                in_ul = True
            html.append(f"<li>{_inline(line.strip()[2:].strip())}</li>")
            i += 1
            continue
        if re.match(r"^\s*\d+\.\s+", line):
            if not in_ol:
                close_lists()
                html.append("<ol>")
                in_ol = True
            html.append(f"<li>{_inline(re.sub(r'^\s*\d+\.\s+', '', line))}</li>")
            i += 1
            continue
        if line.strip() == "":
            close_lists()
            i += 1
            continue
        # HTML embebido (iframes, embeds de X/YouTube, tweets, details): se pasa tal cual,
        # sin escaparlo por _inline(), para que los iframes y embeds funcionen.
        # Acumula líneas contiguas hasta cerrar el tag para soportar iframes
        # y details que ocupan varias líneas en el markdown.
        if re.match(r"^\s*<", line.strip()):
            close_lists()
            block = [line.strip()]
            i += 1
            # Solo consume mas lineas si el tag NO cerro en la primera linea.
            def _consume_until(closing: str):
                nonlocal i
                while i < len(lines) and closing not in lines[i]:
                    block.append(lines[i].strip())
                    i += 1
                if i < len(lines):
                    block.append(lines[i].strip())
                    i += 1
            if re.match(r"^\s*<iframe\b", line.strip()) and "</iframe>" not in block[-1]:
                _consume_until("</iframe>")
            elif re.match(r"^\s*<details\b", line.strip()) and "</details>" not in block[-1]:
                _consume_until("</details>")
            html.append("\n".join(block))
            continue
        # Párrafo: acumula todas las líneas contiguas (no-bloque) y las une en un
        # único <p>. Un párrafo markdown son líneas consecutivas separadas por una
        # línea en blanco (o por otro bloque de contenido). Así no se genera un
        # <p> por cada línea con hard-wrap, evitando el interlineado fragmentado.
        close_lists()
        para: list[str] = []
        while i < len(lines):
            l = lines[i]
            s = l.strip()
            if s == "":
                break
            if (re.match(r"^(#{1,6})\s+", l)
                    or line.startswith("> ") or re.match(r"^#{1,6}\s+", l)
                    or re.match(r"^\s*[-*]\s+", l) or re.match(r"^\s*\d+\.\s+", l)
                    or l.strip() in ("---", "***", "___")
                    or (l.strip().startswith("|") and i + 1 < len(lines)
                        and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]))):
                break
            para.append(s)
            i += 1
        html.append(f"<p>{_inline(' '.join(para))}</p>")
    close_lists()
    return "\n".join(html)


def to_gutenberg(html: str) -> str:
    """Envuelve el HTML plano en comentarios de bloque de Gutenberg para que
    el contenido sea nativo al pegarlo en el editor de WordPress."""
    def heading(m):
        lvl = len(m.group(1))
        return (f'<!-- wp:heading {{"level":{lvl}}} -->'
                f'<h{lvl}>{m.group(2)}</h{lvl}><!-- /wp:heading -->')
    html = re.sub(r'<(h[1-6])>(.*?)</\1>', heading, html, flags=re.DOTALL)
    html = re.sub(r'<blockquote>(.*?)</blockquote>',
                  r'<!-- wp:quote --><blockquote>\1</blockquote><!-- /wp:quote -->',
                  html, flags=re.DOTALL)
    html = re.sub(r'<ul>(.*?)</ul>',
                  r'<!-- wp:list --><ul>\1</ul><!-- /wp:list -->',
                  html, flags=re.DOTALL)
    html = re.sub(r'<ol>(.*?)</ol>',
                  r'<!-- wp:list {"ordered":true} --><ol>\1</ol><!-- /wp:list -->',
                  html, flags=re.DOTALL)
    html = re.sub(r'<table>(.*?)</table>',
                  r'<!-- wp:table --><figure class="wp-block-table">\1</figure><!-- /wp:table -->',
                  html, flags=re.DOTALL)
    html = re.sub(r'<hr\s*/?>',
                  r'<!-- wp:separator --><hr class="wp-block-separator"/><!-- /wp:separator -->',
                  html)
    # FAQ / acordeon nativo: <details> -> bloque Details de WordPress.
    html = re.sub(r'(?s)<details>(.*?)</details>',
                  r'<!-- wp:details --><details class="wp-block-details">\1</details><!-- /wp:details -->',
                  html)
    # Embeds (iframes de X/YouTube, tweet embebido) -> bloque HTML nativo.
    def _html_block(m):
        return f'<!-- wp:html -->\n{m.group(0).strip()}\n<!-- /wp:html -->'
    html = re.sub(r'(?s)<iframe\b.*?</iframe>', _html_block, html)
    html = re.sub(r'(?s)<blockquote class="twitter-tweet".*?</blockquote>.*?(?:</script>|$)', _html_block, html)
    html = re.sub(r'<p>(.*?)</p>',
                  r'<!-- wp:paragraph --><p>\1</p><!-- /wp:paragraph -->',
                  html, flags=re.DOTALL)
    return html


# --------------------------------------------------------------------------- #
# Auto-enriquecimiento: referencias consultadas
# --------------------------------------------------------------------------- #
def _auto_referencias(md: str) -> list[str]:
    """Extrae las URLs externas (no internas COMFIL) que aparecen en el borrador
    y devuelve una lista de strings markdown 'fuente': url para una seccion de
    referencias. No inventa nada: usa exactamente las URLs ya presentes."""
    urls: list[str] = []
    for m in re.finditer(r"https?://[^\s\)\]\"']+", md):
        u = m.group(0).rstrip(".,;:!?")
        if "comfil-local.local" in u or "comfil.edu.mx" in u:
            continue
        if "youtube" in u and ("/embed/" in u):
            # el embed ya se inserta como iframe; no se repite como referencia
            continue
        if u not in urls:
            urls.append(u)
    # Etiqueta con dominio como nombre de la fuente
    return [
        f"- {re.sub(r'^www\\.', '', url.split('//')[1].split('/')[0])}: {url}"
        for url in urls
    ]


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description="Convierte un borrador en entrada WordPress.")
    ap.add_argument("--draft", required=True)
    ap.add_argument("--out", default="entradas")
    ap.add_argument("--title", default=None)
    ap.add_argument("--slug", default=None)
    ap.add_argument("--excerpt", default=None)
    ap.add_argument("--categories", default="")
    ap.add_argument("--tags", default="")
    ap.add_argument("--featured-image", default="")
    ap.add_argument("--status", default="draft")
    ap.add_argument("--seo-title", default=None,
                    help="Titulo SEO (acepta templates Yoast, p.ej. '%%title%% %%sep%% %%sitename%%')")
    ap.add_argument("--seo-description", default=None)
    ap.add_argument("--og-image", default=None)
    # Campos Yoast SEO (por post; opcionales)
    ap.add_argument("--focuskw", default=None,
                    help="Keyword de foco de Yoast (frase principal a posicionar)")
    ap.add_argument("--schema-article-type", default="Article",
                    help="Tipo de schema articulo de Yoast: Article, NewsArticle, BlogPosting, ...")
    ap.add_argument("--bctitle", default=None,
                    help="Titulo corto para el breadcrumb de Yoast")
    ap.add_argument("--cornerstone", action="store_true",
                    help="Marca la entrada como contenido pilares/cornerstone de Yoast")
    ap.add_argument("--og-title", default=None)
    ap.add_argument("--og-description", default=None)
    ap.add_argument("--twitter-title", default=None)
    ap.add_argument("--twitter-description", default=None)
    ap.add_argument("--canonical", default=None,
                    help="URL canonica (vacio: WP usa la propia)")
    ap.add_argument("--author", default="COMFIL",
                    help="Nombre del autor/organizacion para el schema Article")
    ap.add_argument("--extras", action="store_true",
                    help="Ademas de .wp.json y .html, genera .gutenberg.html y .schema.json")
    args = ap.parse_args()

    if not os.path.isfile(args.draft):
        sys.exit(f"No existe el borrador: {args.draft}")

    # utf-8-sig QUITA el BOM del archivo fuente; si no, el \ufeff se propaga
    # al post_content y queda guardado en la BD.
    md = open(args.draft, encoding="utf-8-sig").read()
    md = md.lstrip("﻿")
    # AUTO-EMBED: las URLs de YouTube aisladas en su propia linea se convierten
    # en iframe (determinista, usa el ID que ya esta en el texto).
    md = _auto_embed_youtube(md)
    # AUTO-REFERENCIAS: si el borrador no cierra con una seccion de referencias,
    # la genera automaticamente con las URLs externas ya presentes en el texto.
    if not re.search(r"^#{1,4}\s+[Rr]eferencias?\s", md, re.M):
        refs = _auto_referencias(md)
        if refs:
            md = md.rstrip() + "\n\n## Referencias consultadas\n\n" + "\n".join(refs) + "\n"
    html = md_to_html(md)
    gut = to_gutenberg(html)
    gut = gut.lstrip("﻿")
    html = html.lstrip("﻿")

    # Título: flag o primer H1
    title = args.title
    if not title:
        m = re.search(r"^#\s+(.+)$", md, re.M)
        title = m.group(1).strip() if m else os.path.splitext(os.path.basename(args.draft))[0]

    slug = args.slug or _slugify(title)

    # Extracto: flag, primer párrafo, o recorte del contenido
    excerpt = args.excerpt
    if not excerpt:
        m = re.search(r"^#\s+.+$[\r\n]+([^\r\n#|>].+)$", md, re.M)
        excerpt = (m.group(1).strip() if m else title)[:300]

    cats = [c.strip() for c in args.categories.split(",") if c.strip()]
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    # Datos Yoast SEO por post: deploy_wp.py los aplica si estan presentes.
    # Por defecto se rellenan con valores sensatos derivados de la entrada.
    og_title = args.og_title or title
    og_desc = args.og_description or args.seo_description or excerpt
    tw_title = args.twitter_title or og_title
    tw_desc = args.twitter_description or og_desc
    yoast = {
        "focuskw": args.focuskw or "",
        "title": args.seo_title or title,
        "metadesc": args.seo_description or excerpt,
        "bctitle": args.bctitle or "",
        "is_cornerstone": 1 if args.cornerstone else 0,
        "schema_article_type": args.schema_article_type or "Article",
        "canonical": args.canonical or "",
        "opengraph-title": og_title,
        "opengraph-description": og_desc,
        "twitter-title": tw_title,
        "twitter-description": tw_desc,
    }

    payload = {
        "post_title": title,
        "post_name": slug,
        "post_content": gut,
        "post_excerpt": excerpt,
        "post_status": args.status,
        "post_category": cats,
        "tags_input": tags,
        "featured_image": args.featured_image,
        "yoast": yoast,
        "meta": {
            "seo_title": args.seo_title or title,
            "seo_description": args.seo_description or excerpt,
            "og:image": args.og_image or args.featured_image,
        },
        # Datos estructurados (pasan el checklist de blog-seo-check)
        "schema": {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": title,
            "description": excerpt,
            "image": args.featured_image or None,
            "datePublished": datetime.date.today().isoformat(),
            "dateModified": datetime.date.today().isoformat(),
            "author": {"@type": "Organization", "name": args.author},
            "publisher": {"@type": "Organization", "name": args.author},
            "mainEntityOfPage": {"@type": "WebPage", "@id": ""},
        },
    }

    # Cada entrada va a su propio subfolder para soportar volumenes n-esimos
    entry_dir = os.path.join(args.out, slug)
    os.makedirs(entry_dir, exist_ok=True)
    json_path = os.path.join(entry_dir, f"{slug}.wp.json")
    html_path = os.path.join(entry_dir, f"{slug}.html")

    # .wp.json SIN BOM: si tuviera BOM, json.load() en deploy_wp.py fallaria.
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    # .html SIN BOM: el usuario pega desde un editor UTF-8, el BOM solo
    # introduciria un caracter raro al inicio del contenido.
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(html)

    print(f"[OK] Entrada WordPress generada (subfolder: {args.out}/{slug}/):")
    print(f"   JSON (despliegue)        : {json_path}")
    print(f"   HTML (copy-paste editor) : {html_path}")
    if args.extras:
        gut_path = os.path.join(entry_dir, f"{slug}.gutenberg.html")
        schema_path = os.path.join(entry_dir, f"{slug}.schema.json")
        with open(gut_path, "w", encoding="utf-8") as fh:
            fh.write(gut)
        with open(schema_path, "w", encoding="utf-8") as fh:
            json.dump(payload["schema"], fh, ensure_ascii=False, indent=2)
        print(f"   GUTENBERG (solo vista codigo bloques): {gut_path}")
        print(f"   SCHEMA (referencia JSON-LD)          : {schema_path}")
    print(f"   Título : {title}")
    print(f"   Slug  : {slug}")
    print(f"   Cats  : {cats}")
    print(f"   Tags  : {tags}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
