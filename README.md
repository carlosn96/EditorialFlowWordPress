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
│   ├── build_wp_entry.py     # borrador (.md) -> artefacto (.wp.json / .html)
│   ├── build_all.py          # lote: todos los borradores -> artefactos
│   ├── deploy_wp.py          # despliegue a WordPress LOCAL
│   ├── deploy_prod_ssh.py    # despliegue a PRODUCCION (paramiko + WP-CLI remoto)
│   └── deploy_all.py         # lote de despliegue
├── references/brand-voice.md # voz de marca y pautas editoriales
├── .env.example              # variables de produccion (plantilla)
└── .gitignore
```

## Requisitos

- Python 3.
- WordPress local (Local by Flywheel) con el wrapper `wp.ps1` en la raíz del proyecto.
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
py scripts/deploy_wp.py --json workspace/draft-entradas/generados/<slug>/<slug>.wp.json --author-name COMFIL

# 3) Desplegar en produccion (crea; con --update actualiza por slug)
py scripts/deploy_prod_ssh.py --json <...>.wp.json [--update]
```

El detalle del flujo (análisis, redacción, SEO, taxonomía, autocrítica) está en
`skill/SKILL.md`.

## Dónde vive la copia activa

Este repo es la **fuente versionada**. La copia que consume el pipeline de
agentes vive en `<proyecto>/.agents/skills/comfil-draft-entradas/`. Para activar
cambios, sincroniza:

```powershell
Copy-Item "scripts\*" "<proyecto>\.agents\skills\comfil-draft-entradas\scripts\" -Recurse -Force
Copy-Item "skill\SKILL.md" "<proyecto>\.agents\skills\comfil-draft-entradas\SKILL.md" -Force
Copy-Item "references\*" "<proyecto>\.agents\skills\comfil-draft-entradas\references\" -Recurse -Force
```

> Nota: `deploy_wp.py` resuelve la raíz subiendo 4 niveles desde `scripts/`. Si
> ejecutas desde el bundle (no desde `.agents/skills/...`), ajusta ese cálculo o
> usa la copia dentro del proyecto.

## Nunca versionar

`.env`, credenciales SSH (`ssh.txt`), `workspace/` y salidas generadas. Ver `.gitignore`.
