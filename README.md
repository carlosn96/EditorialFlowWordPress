# EditorialFlow

Pipeline editorial que convierte **borradores** (notas, recortes, fuentes) en
**entradas de WordPress desplegables**, con SEO, taxonomía y metadatos, y las
publica en **local** y en **producción (vía SSH)**.

Es **agnóstico al tema**: no conoce categorías, etiquetas ni marcas concretas.
Todo lo específico del sitio entra por `meta.json` (la entrada) y por `.env`
(el entorno de publicación).

## Qué incluye

```
EditorialFlow/
├── skill/SKILL.md            # el pipeline (pasos, reglas editoriales, checklist)
├── scripts/
│   ├── config.py             # resolución de marca/sitio (perfil activo)
│   ├── build_wp_entry.py     # borrador (.md) -> artefacto (.wp.json / .html)
│   ├── build_all.py          # lote: todos los borradores -> artefactos
│   ├── deploy_wp.py          # despliegue a WordPress LOCAL
│   ├── deploy_prod_ssh.py    # despliegue a PRODUCCION (paramiko + WP-CLI remoto)
│   └── deploy_all.py         # lote de despliegue
├── brands/<slug>/            # PERFIL de marca (agnóstico)
│   ├── brand.json            #   identidad: nombre, full_name, aliases, audiencia
│   ├── site.json             #   internal_domains, author, schema por defecto
│   └── brand-voice.md        #   voz/tono de la marca
├── references/brand-voice.md # plantilla de voz (fallback)
├── .env.example              # variables de produccion (plantilla)
└── .gitignore
```

## Requisitos

- Python 3.
- WordPress local (p. ej. Local by Flywheel) accesible con WP-CLI (wrapper `wp.ps1` o `wp` en PATH; define `WP_CLI_COMMAND` si aplica).
- Para producción: acceso SSH al hosting y WP-CLI en el servidor.
- `paramiko` para `deploy_prod_ssh.py`.

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
`skill/SKILL.md`.

## Selección de marca

El perfil activo se resuelve así (orden): `--brand <slug>` → env `EDITORIALFLOW_BRAND` → default.
La carpeta `brands/` se busca en: `EDITORIALFLOW_BRANDS_DIR` → `<proyecto>/brands` → `<repo>/brands`.
Overrides por entorno: `SITE_DOMAINS` (dominios internos, separados por coma) y `WP_AUTHOR_NAME`.

Cada marca es una carpeta `brands/<slug>/` con `brand.json`, `site.json` y `brand-voice.md`.
Agregar una marca nueva no toca el código.

## Dónde vive la copia activa

Este repo es la **fuente versionada**. La copia que consume el pipeline de agentes
vive en `<proyecto>/.agents/skills/<skill>/` (para COMFIL: `comfil-draft-entradas`).
Para activar cambios, sincroniza:

```powershell
$skills = "<proyecto>\.agents\skills\comfil-draft-entradas"
Copy-Item "scripts\*" "$skills\scripts\" -Recurse -Force
Copy-Item "skill\SKILL.md" "$skills\SKILL.md" -Force
Copy-Item "brands\*" "<proyecto>\brands\" -Recurse -Force
```

> Nota: `deploy_wp.py` resuelve la raíz subiendo 4 niveles desde `scripts/`. Si
> ejecutas desde el bundle (no desde `.agents/skills/...`), ajusta ese cálculo o
> usa la copia dentro del proyecto.

## Nunca versionar

`.env`, credenciales SSH (`ssh.txt`), `workspace/` y salidas generadas. Ver `.gitignore`.
