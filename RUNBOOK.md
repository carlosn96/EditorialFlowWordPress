# RUNBOOK — EditorialFlow

Operaciones y resolución de problemas del desplegador de entradas.

## 1. Flujo estándar de una entrada

1. Analizar el material y volcar el brief (`informacion/brief.md`).
2. Redactar `informacion/borrador.md` (voz de marca + reglas del `SKILL.md`).
3. Autocrítica (checklist de estructuras prohibidas y de calidad).
4. Validar SEO (`seo-report.md`) y definir taxonomía (`meta.json`).
5. Construir el artefacto con `build_wp_entry.py` (o `build_all.py` en lote).
6. Desplegar en local (`deploy_wp.py`) y verificar en la BD.
7. Desplegar en producción (`deploy_prod_ssh.py`).

## 2. Local vs producción

- **Local:** `deploy_wp.py` usa el wrapper `wp.ps1` del proyecto. Crea un post nuevo.
- **Producción:** `deploy_prod_ssh.py` conecta por SSH (paramiko) y ejecuta el `wp` del servidor.
  - Crea por defecto. Para **actualizar sin duplicar**: `--update` (resuelve el post por slug).
  - Fija Yoast completo, incluida `_yoast_wpseo_primary_category` (primera categoría del JSON).
- Ambos leen el **mismo artefacto** `.wp.json`. Si editas un post en el editor de WordPress,
  esos cambios **no** viajan: hay que regenerar el `.wp.json`.

## 3. Taxonomía (trampas conocidas)

- `wp post term set` **reemplaza** los términos, no añade. Pasa **todos** en **una sola llamada**
  y por **slug**. Nunca pases ids numéricos (los interpreta como nombre y crea términos basura).
- Tras **actualizar el contenido** de un post existente, **re-aplica taxonomía y categoría primaria**.
- Categorías y etiquetas **pueden diferir entre entornos**: resuelve cada término por nombre/slug
  en el sitio destino; no asumas que coinciden.

## 4. Verificación

- En PowerShell, la salida de `wp.ps1` llega como **array de líneas**: únela con `-join` antes de
  buscar substrings (`Contains`/`Length` dan falsos negativos).
- Antes de desplegar, confirma que los **enlaces internos existen** en el entorno destino.
- La puntuación de Yoast se **recalcula al abrir/guardar** el post; el `linkdex` guardado puede estar viejo.

## 5. Embeds y bloques

- X/Twitter **no** tiene iframe nativo. Opciones: URL sola (oEmbed de WP), embed oficial
  `blockquote`+`widgets.js`, o iframe `https://platform.twitter.com/embed/Tweet.html?id=<id>`.
- `build_wp_entry.py` auto-embebe **YouTube** y pasa `<iframe>`; soporta `<details>` → bloque FAQ
  nativo (`wp:details`). Las imágenes markdown `![]()` **no** están soportadas: usa HTML `<figure><img>`.

## 6. Troubleshooting

| Síntoma | Causa probable | Fix |
|---|---|---|
| "Too many arguments" | valor con espacios sin entrecomillar | entrecomilla; orden posicionales→flags |
| No conecta a la BD (local) | sitio Local apagado | arranca comfil-local en Local |
| `post term set` creó términos basura | se pasaron ids numéricos | pasa slugs, en una sola llamada |
| Tags/categoría desaparecen tras editar | update de contenido sin re-aplicar taxonomía | re-aplica con `post term set` (una llamada) |
| Embed de X no carga | wrapper de terceros / sin oEmbed | usa oembed de WP o el iframe oficial de X |
| Puntuación Yoast baja/roja | sin focus keyword / metadatos | abre y guarda el post; verifica `_yoast_wpseo_focuskw` |

## 7. Producción: credenciales

Viven en el `.env` del proyecto y en `workspace/remote/ssh.txt` (ignorados por git).
Nunca se versionan ni se imprimen.
