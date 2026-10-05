# EditorialFlow

Pipeline editorial que convierte **borradores** (notas, recortes, fuentes) en
**entradas de WordPress** listas para desplegar, con SEO, taxonomía y metadatos,
y las publica en **local** y en **producción (vía SSH)**.

Es **agnóstico a la marca y al tema**: el motor no conoce categorías, etiquetas ni
marcas concretas. Todo lo específico entra por el **perfil de marca**
(`brands/<slug>/`), por la **entrada** (`meta.json`) y por el **entorno** (`.env`).

## Características

- **Construcción determinista** de artefactos: `.wp.json` (contrato de despliegue) y `.html` (copy-paste).
- **SEO on-page**: title, meta description, focus keyword, jerarquía de encabezados, JSON-LD y OG/Twitter.
- **Bloques nativos**: párrafos, listas, `<details>` (FAQ), `iframe` (YouTube/embeds).
- **Enlaces internos** normalizados a rutas relativas (funcionan en local y producción).
- **Despliegue local** (WP-CLI) y **a producción** (SSH + paramiko + WP-CLI remoto), con `--update` por slug.
- **Multi-marca** sin tocar código: un perfil por marca.

## Estructura

```
EditorialFlow/
├── skill/SKILL.md            # el pipeline (pasos, reglas editoriales, checklist)
├── scripts/
│   ├── config.py             # resolución de marca/sitio (perfil activo)
│   ├── build_wp_entry.py     # borrador (.md) -> artefacto (.wp.json / .html)
│   ├── build_all.py          # lote: todos los borradores -> artefactos
│   ├── deploy_wp.py          # despliegue a WordPress LOCAL
│   ├── deploy_prod_ssh.py    # despliegue a PRODUCCION (paramiko + WP-CLI remoto)
│   ├── deploy_all.py         # lote de despliegue
│   └── install.py            # instalador en un proyecto
├── brands/<slug>/            # PERFIL de marca
│   ├── brand.json            #   identidad: nombre, full_name, aliases, audiencia
│   ├── site.json             #   internal_domains, author, schema por defecto
│   └── brand-voice.md        #   voz/tono de la marca
├── references/brand-voice.md # plantilla de voz (fallback)
├── references/eval-redaccion.md # compuerta de evaluacion (PASS/FAIL) inspirada en no-ai-slop
├── INSTALL.md  RUNBOOK.md  AGENTS.md  CHANGELOG.md
├── .env.example              # variables de produccion (plantilla)
└── .gitignore
```

## Requisitos

- Python 3.
- WP-CLI local: wrapper `wp.ps1` en la raíz del proyecto, o `wp` en PATH
  (o define `WP_CLI_COMMAND`).
- Para producción: acceso SSH al hosting, WP-CLI en el servidor y `pip install paramiko`.

## Instalación

Instala el skill + los perfiles de marca en un proyecto WordPress (idempotente).
Detalle en [`INSTALL.md`](INSTALL.md).

```powershell
py scripts/install.py --project-root "C:\ruta\al\proyecto" `
   --skill-name comfil-draft-entradas --brand comfil
```

Luego define la marca activa en el `.env` del proyecto: `EDITORIALFLOW_BRAND=comfil`.

## Uso rápido

```powershell
# 1) Construir el artefacto de una entrada
py scripts/build_wp_entry.py --draft <carpeta>/informacion/borrador.md `
   --title "Titulo" --slug "mi-entrada" --excerpt "Resumen SEO" `
   --categories "Categoria" --tags "Tag1,Tag2" `
   --featured-image "https://.../img.jpg" --status draft `
   --out workspace/draft-entradas/generados

# 2) Desplegar en local
py scripts/deploy_wp.py --json workspace/draft-entradas/generados/<slug>/<slug>.wp.json --author-name <login-del-autor>

# 3) Desplegar en produccion (crea; con --update actualiza por slug)
py scripts/deploy_prod_ssh.py --json <...>.wp.json [--update]
```

El detalle del flujo (análisis, redacción, SEO, taxonomía, autocrítica) está en
[`skill/SKILL.md`](skill/SKILL.md).

## Perfiles de marca (multi-marca)

El perfil activo se resuelve así (orden): `--brand <slug>` → env `EDITORIALFLOW_BRAND` → default.
La carpeta `brands/` se busca en: `EDITORIALFLOW_BRANDS_DIR` → `<proyecto>/brands` → `<repo>/brands`.
Overrides por entorno: `SITE_DOMAINS` (dominios internos separados por coma) y `WP_AUTHOR_NAME`.

Agregar una marca nueva = crear `brands/<slug>/` con `brand.json`, `site.json` y
`brand-voice.md`. **No se toca el código.**

## Despliegue

- **Local:** `deploy_wp.py` usa el comando WP-CLI local y crea un post (borrador por defecto).
- **Producción:** `deploy_prod_ssh.py` conecta por SSH (credenciales en el `.env` y `workspace/remote/ssh.txt`)
  y aplica el bloque `yoast` completo. Crea por defecto; `--update` actualiza por slug.

## Cómo lo descubre un agente

- El `AGENTS.md` de la raíz del proyecto indica leer el `SKILL.md` del skill instalado.
- Si el entorno soporta skills, el skill aparece en la lista y se carga al detectar la tarea.

## Nunca versionar

`.env`, credenciales SSH (`ssh.txt`), `workspace/` y salidas generadas. Ver `.gitignore`.
