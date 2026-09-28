---
name: comfil-draft-entradas
description: >
  Pipeline para convertir una carpeta de borradores, notas o recortes en una
  entrada de WordPress lista para desplegar (WP-compatible). Lee una carpeta
  indicada, analiza el material, redacta con la skill blog, valida SEO con
  blog-seo-check, asigna taxonomia con blog-taxonomy, y convierte el borrador en
  un artefacto JSON/HTML con todos los atributos de la entrada (titulo,
  extracto, tags, categorias, imagen destacada) listo para autodespliegue. Usa
  SIEMPRE este skill cuando el usuario quiera pasar notas a un articulo
  WordPress, diga crear entrada, armar articulo desde una carpeta, pipeline de
  borradores, publicar en WP desde una carpeta, o hable de generar o desplegar
  contenido de blog desde materiales existentes, aunque no nombre al skill
  explicitamente. No uses scrappers: el banco de noticias ya lo resuelve
  Activepieces.
---

# COMFIL · Pipeline de borradores -> entrada WordPress

Pasa de una carpeta con materiales (notas, recortes, borradores) a una **entrada
de WordPress desplegable**, sin escribir a mano el JSON ni los atributos de WP.
El scrapper/banco de noticias ya lo aporta Activepieces; este pipeline **empieza
cuando los borradores ya estan en una carpeta**.

## Por que existe este pipeline
Escribir/desplegar entradas a mano es repetitivo y propenso a olvidar atributos
(tags, extracto SEO, imagen destacada). Centralizar el flujo en un skill
garantiza que cada articulo salga con la misma estructura, SEO y metadatos, y
que el despliegue sea un paso deterministico (script, no copiar-pegar).

## Entradas / salidas
- **Entrada obligatoria:** ruta a la carpeta con el material
  (p. ej. `workspace/draft-entradas/voluntariado-leon-peru/`).
- **Salidas (en `entradas/` o donde indiques con `--out`):**
  - `<slug>.wp.json` — payload completo de la entrada (contrato de autodespliegue).
  - `<slug>.html` — contenido HTML compatible con el editor de WP.
  - `<slug>.content.html` — contenido crudo (lo consume el despliegue).

## Estructuras prohibidas (IA sobreexplotadas)
**Prohibido estrictamente.** Redacta la idea directa; no uses andamiaje retorico
vacio. Estas estructuras son la marca de una redaccion generativa barata: restan
autoridad y hacen que el texto parezca de IA, justo lo contrario del tono
pastoral y directo que requiere COMFIL. Revisa el borrador y elimina cualquiera de
las siguientes antes de convertirlo a entrada.

### Aperturas vacías
- "En el mundo de...", "En un mundo cada vez más...", "En la era de... / En la era digital..."
- "En la actualidad...", "Hoy en día...", "En los últimos años...", "En el panorama actual..."
- "Cuando se trata de...", "A medida que...", "A lo largo de..."

### Muletillas de énfasis (relleno)
- "Es importante destacar que...", "Cabe señalar que...", "Vale la pena mencionar que..."
- "Sin duda...", "Indudablemente...", "No se puede negar que..."
- "Es fundamental / esencial / crucial..." (sin justificación concreta)
- "En pocas palabras...", "En otras palabras..." como muletilla

### Andamiaje de contraste fingido
- **"No es X, sino Y" / "No se trata de..., sino de..." / "No tanto X como Y".** Salvo que exista una confusión real que aclarar, es fórmula de relleno. Escribe lo que es.
- "Por un lado... por otro...", "No solo..., sino que también...", "Más que..., es..."
- **Variante con dos puntos:** "X no es solo un A: busca B" / "La iniciativa no es solo un esquema: busca...". Mismo vicio; redacta la idea directa.

### Transiciones vacuas
- "En este sentido...", "En este contexto...", "A este respecto...", "En consecuencia...", "Por lo tanto..."

### Metáforas y clichés desgastados
- "En el tejido de...", "En el corazón de...", "La piedra angular de...", "Una pieza clave del rompecabezas"
- "La punta del iceberg", "El viaje de...", "Abrazar (embrace) lo X", "Deslumbrar", "Sin precedentes"
- "Jugar un papel crucial / desempeñar un papel fundamental", "Desarrollar todo su potencial"
- Verbos inflados sin sustancia: "transformar", "revolucionar", "impulsar", "potenciar" usados como relleno
- Abuso del guion largo (—) como muletilla de separación

### Gancho de engagement barato
- "Imagina que...", "¿Te has preguntado alguna vez...?", "¿Alguna vez te has detenido a pensar...?"
- "En este artículo, exploraremos...", "Vamos a profundizar...", "Sigue leyendo para descubrir..."

### Cierres de manual
- "En conclusión... / Para concluir... / En resumen... / En definitiva..."
- "¡Así que ya sabes!" / "¡Así que ya lo sabes!" o cualquier cierre con exclamaciones o emoji
- "El futuro de X..." o "El tiempo lo dirá" como remate genérico

## Workflow

### 0. Areas de trabajo (raiz = `workspace`) y volumen n-esimo
El area de trabajo es `workspace/draft-entradas/` y se divide en DOS zonas
claramente separadas para que no haya confusion entre borradores/referencias y
archivos finales:

```
workspace/draft-entradas/
├── borradores/                 (INPUT: materiales y trabajo en curso)
│   └── <carpeta-tema>/
│       ├── referencias/        (fuentes .md del banco de noticias; NO tocar)
│       ├── informacion/        (artefactos generados por el pipeline)
│       │   ├── brief.md        (paso 1)
│       │   ├── borrador.md     (paso 2, redaccion final)
│       │   ├── seo-report.md   (paso 3)
│       │   └── taxonomy.md     (paso 4)
│       └── meta.json           (titulo, slug, excerpt, categories, tags, featured_image,
│                               status, + campos Yoast SEO opcionales — ver seccion 6b)
└── generados/                  (OUTPUT: archivos finales listos para WordPress)
    ├── <slug>/
    │   ├── <slug>.wp.json       (despliegue: fuente de verdad)
    │   └── <slug>.html          (copy-paste compatible con el editor WP)
    └── manifest.json           (indice de todas las entradas)
```

- **`borradores/`** = donte estan los borradores y referencias (input). Cada
  `<carpeta-tema>` es una entrada; dentro, `referencias/` guarda las fuentes
  originales y `informacion/` los artefactos del pipeline.
- **`generados/`** = donte se guardan los archivos finales (output), uno por
  entrada en su propio subfolder `<slug>/`, mas el `manifest.json`.

Para **n entradas** hay n carpetas-tema en `borradores/`; se procesan en lote
(ver pasos 5 y 6). Si una carpeta-tema tiene varios borradores,
**sintetizalos en un solo `borrador.md`** (no los proceses por separado). La
imagen destacada no se inventa: debe ir en `meta.json` como URL/ruta real
(asset de marca u OG image oficial).

### 1. Analizar y comprender
Lee todos los archivos. Extrae: entidades (personas, lugares, fechas,
instituciones, fuentes), angulo/tesis, hechos clave con procedencia, y palabras
clave candidatas a tags/categorias. Vuelca el analisis en
`<carpeta>/informacion/brief.md` (breve) para fundamentar el borrador. **No
inventes datos**: si algo falta, marca la fuente, no la suplies.

El brief debe incluir un campo obligatorio **"Ángulo COMFIL"**: qué le interesa
de la nota a la comunidad/estudiantes y a qué lector concreto habla (p. ej. un
egresado que sirve de caso, una lección para los alumnos, un tema de la
comunicación eclesial). Ese ángulo —no el tema de la fuente— es el que debe
gobernar el titular y la estructura del borrador.

### 2. Redactar con la skill `blog`
Aplica la skill **`blog`** (ya instalada en `.agents/skills/blog`): escribe el
articulo en espanol siguiendo sus 6 pilares (claridad con proposito, datos
reales citados, medios visuales, Q&A opcional, estructura, mantenimiento) y sus
quality gates. **Si `blog` no esta registrada como invocable en tu entorno,
lee `.agents/skills/blog/SKILL.md` y aplica su metodologia directamente.**
**Ajusta la redaccion a la voz de COMFIL** (lee `references/brand-voice.md`
antes de escribir: registro pastoral/formal, lexico de acogida y encuentro,
tratamiento exacto de cargos, cierre orientado a la comunidad). El borrador
resultante se guarda como `<carpeta>/informacion/borrador.md` (Markdown).
**Cero tolerancia a datos fabricados:** no uses cifras (p. ej. "6.000
voluntarios") que no esten en las fuentes de la carpeta; marca la fuente.

**Cifras variables:** toda cifra que cambie con el tiempo (seguidores, vistas,
descargas) se escribe con su **matiz exacto** (p. ej. "seguidores" ≠
"participantes del directo") y, si procede, con la **fecha de verificación**
("septiembre de 2026"). Si las fuentes discrepan, señala la discrepancia en una
frase y cita ambas. Un titular nunca debe atribuir a una métrica un significado
que no tenga el dato real del cuerpo.

**Originalidad sin inferencia (obligatorio):** no infieras, deduzcas ni "rellenes"
datos que no estén explícitamente en las fuentes. Toda afirmación, cifra, cita,
fecha o nombre debe tener fuente verificable y citarse inline. Si un dato no está
en las fuentes, no se escribe. La originalidad se logra por **síntesis, ángulo
propio y datos actuales verificados** (fuentes oficiales y recientes), nunca por
contexto inventado. Distingue siempre hecho, opinión y proyección. No te quedes
con un único caso o una fuente antigua: busca y contrasta material reciente y
oficial antes de redactar.

### 2c. Enriquecimiento (OBLIGATORIO para toda entrada)
Para que cada articulo salga anclado a fuentes reales y con medios visuales,
**toda** entrada debe incorporar, si el material lo permite, los siguientes
elementos antes de pasar al paso 3. No se inventa nada: usa solo lo que esta en
`referencias/` y las URLs verificadas del material.

- **Seccion "Referencias consultadas"** al final del borrador: lista de las
  fuentes que respaldan cada dato (nombre de la fuente + URL verificada, sin
  inventar URLs). Como minimo las fuentes principales de `referencias/`.
- **Embeds de video** (YouTube/X/otros): si el material menciona o apunta a un
  video (p. ej. el clip de Kharg), inserta el `<iframe>`/embed del video en la
  seccion correspondiente del cuerpo, indicandolo con su origen. `build_wp_entry.py`
  tambien convierte automaticamente a iframe cualquier URL de **YouTube
  aislada en su propia linea** del borrador (ver paso 5).
- **Enlaces internos COMFIL**: enlaza de 3 a 5 entradas publicadas del propio
  sitio (*comfil-local.local/...* en local, se mantienen al desplegar) cuando
  haya conexion tematica, para reforzar el tema y el SEO interno.
- **Enlaces externos siameses**: los datos clave (cifras, verificaciones,
  nombres propios) se citan con su fuente enlazada inline con
  `[texto](https://...url...)`.

El script `build_wp_entry.py` respalda esto de forma automatica y determinista:
- **Auto-embeds**: convierte en `<iframe>` las URLs de YouTube que esten **solas
  en su propia linea** del borrador (usa el ID real de la URL; nunca inventa).
- **Auto-referencias**: si el borrador **no** cierra con una seccion "Referencias
  consultadas", la genera al final extrayendo automaticamente las URLs externas
  ya presentes en el texto (excluye enlaces internos y el embed de YouTube ya
  insertado).

Asi, incluso si un material no lleva el enriquecimiento escrito a mano, el
artefacto final (`.wp.json`) sale con referencias y embeds al desplegar.

### 2b. Autocrítica (obligatoria antes de avanzar)
Antes de pasar al paso 3, **relee `borrador.md`** y tacha del checklist cada
patron de la seccion "Estructuras prohibidas". Si queda alguno, reescribelo. No
avances hasta tener todas las casillas marcadas.

- [ ] Sin aperturas vacias ("En el mundo de...", "En la actualidad...", "Cuando se trata de...")
- [ ] Sin muletillas de enfasis ("Es importante destacar que...", "Cabe señalar que...", "Sin duda...", "Es fundamental...")
- [ ] Sin contraste fingido ("No es X, sino Y", "X no es solo A: busca B" con dos puntos, "Por un lado... por otro", "No solo..., sino que tambien...")
- [ ] Sin transiciones vacuas ("En este sentido...", "En este contexto...", "Por lo tanto...")
- [ ] Sin metaforas/cliches desgastados ("piedra angular", "punta del iceberg", "abraza lo X", verbos inflados: transformar/impulsar/potenciar de relleno)
- [ ] Sin gancho de engagement barato ("Imagina que...", "¿Te has preguntado alguna vez...?", "Sigue leyendo para descubrir...")
- [ ] Sin cierres de manual ("En conclusion...", "¡Asi que ya sabes!" con exclamaciones/emoji, "El futuro de X...")
- [ ] Voz COMFIL: registro pastoral/formal, cargos con tratamiento correcto, cierre orientado a la comunidad, sin invenciones de citas
- [ ] Variación de referencias a COMFIL: la sigla no se repite en menciones seguidas; se alterna con "Instituto de Comunicación y Filosofía", "la escuela", "la casa de estudios", "nuestra comunidad"
- [ ] Ángulo propio: la nota tiene un ángulo que interesa a la comunidad COMFIL y no replica el orden ni el relato de la fuente primaria (no es una paráfrasis)
- [ ] Sin registro laudatorio/heroico: las personas se tratan como casos o ejemplos, no como modelos a imitar ni con adjetivación elogiosa
- [ ] Cifras con matiz exacto (seguidores vs. participantes) y fecha de verificación; discrepancias entre fuentes señaladas con ambas citas
- [ ] Cero inferencia: cada dato, cita, cifra y nombre tiene fuente verificable citada inline; no hay afirmaciones sin respaldo ni contexto inventado

### 3. Validar SEO con `blog-seo-check`
Aplica la skill **`blog-seo-check`** (`.agents/skills/blog-seo-check`) sobre
`borrador.md`: titulo (tag `<title>`), meta description, jerarquia de
encabezados, enlaces internos/externos, tags OG/Twitter y datos estructurados.
Guarda el reporte en `<carpeta>/informacion/seo-report.md`.
**Si no esta registrada como invocable, lee su SKILL.md y aplica el checklist.**
Corrige hasta pasar la lista. Anota el `seo_title` y `seo_description` finales.

Notas de entorno (no bloquean el borrador):
- En un borrador aislado no existen URLs del sitio: marca los **enlaces
  internos** como WARN y difierelos hasta desplegar (luego enlaza 3+ entradas
  COMFIL).
- `build_wp_entry.py` ya genera el **JSON-LD Article** y `deploy_wp.py` fija
  **OG/Twitter/yoast**, asi que esos puntos del checklist quedan cubiertos por
  el script, no a mano.

### 4. Taxonomia (tags + categorias) con `blog-taxonomy`
Usa la skill **`blog-taxonomy`** (disponible localmente) para sugerir etiquetas
y categorias coherentes con el sitio WordPress. Por defecto usa el modo
**`suggest`** (no requiere credenciales). Define la lista final de `categories`
(1 primaria) y `tags` (3-8) y guárdalas en `<carpeta>/informacion/taxonomy.md`
y en `<carpeta>/meta.json` (para el batch). El modo **`sync`** a WordPress
necesita las variables `CMS_TYPE`, `CMS_URL` y `CMS_API_KEY`; si no estan
configuradas, omite el sync y deja los tags en el JSON para que los fije
`deploy_wp.py`.

### 5. Convertir a artefacto WP
**Una entrada:** ejecuta desde la raiz del proyecto (`comfil-local`):

```powershell
py .agents/skills/comfil-draft-entradas/scripts/build_wp_entry.py `
  --draft <carpeta>/informacion/borrador.md `
  --title "Titulo final" --slug "mi-entrada" `
  --excerpt "Resumen SEO (meta description)" `
  --categories "Comunicacion,Iglesia" `
  --tags "Papa Leon XIV,Peru,Voluntariado" `
  --featured-image "https://.../imagen-destacada.jpg" `
  --status draft --out workspace/draft-entradas/generados
```

**n entradas (lote):** usa `build_all.py`, que escanea todas las carpetas-tema
en `borradores/` (cada una con `informacion/borrador.md` + `meta.json`) y genera
cada entrada en su propio subfolder. Sus defaults ya apuntan al area de
trabajo (`workspace/draft-entradas/borradores` y
`workspace/draft-entradas/generados`), asi que basta ejecutarlo:

```powershell
py .agents/skills/comfil-draft-entradas/scripts/build_all.py
```

Cada entrada se escribe en **`workspace/draft-entradas/generados/<slug>/`**
(subfolder propio) con solo dos archivos:

- **`<slug>.wp.json`** — fuente de verdad para el despliegue (lo lee `deploy_wp.py`).
- **`<slug>.html`** — **HTML plano** (`<p>`, `<h2>`, `<ul>`…), el archivo
  **copy-paste compatible con el editor de WordPress**: al pegarlo en el editor
  (vista visual o editor clásico) se convierte solo en bloques. Este es el
  archivo que usas para publicar manualmente.

Con `--extras` se generan ademas `<slug>.gutenberg.html` (marcado de bloque
`<!-- wp: -->`, solo util para pegar en la *vista de código* del editor de
bloques) y `<slug>.schema.json` (JSON-LD de referencia).

`build_wp_entry.py` aplica **auto-enriquecimiento** en cada conversion (paso 2c):
- **Auto-embeds de YouTube**: una URL de YouTube que este **sola en su propia
  linea** del borrador se convierte automaticamente en `<iframe>` embebido.
- **Auto-referencias**: si el borrador no cierra con una seccion "Referencias
  consultadas", se **genera al final** con las URLs externas ya presentes en el
  texto (excluye enlaces internos COMFIL y el embed de YouTube ya insertado).

Así, aunque el borrador no incluya el enriquecimiento escrito a mano, el
`.wp.json` siempre sale con referencias y el video embebido cuando los hay.

Al terminar se actualiza **`manifest.json`** (indice de todas las entradas:
slug, titulo, carpeta origen, estado, tags, categorias). Así el volumen
n-esimo queda organizado y trazable. `deploy_wp.py` no deja archivos
transitorios en el area.

El `.wp.json` lleva **todos** los atributos: `post_title`, `post_name` (slug),
`post_content` (**HTML con marcado de bloque Gutenberg**, listo para pegar en el
editor), `post_excerpt`, `post_status`, `post_category`, `tags_input`,
`featured_image` y `meta` (seo_title, seo_description, og:image).

`<slug>.gutenberg.html` es el mismo contenido envuelto en comentarios
`<!-- wp:... -->`, **copy-paste ready** para pegar directamente en el editor de
bloques (crea bloques nativos). `deploy_wp.py` usa ese marcado.

### 6. Autodespliegue
**Una entrada:**
```powershell
py .agents/skills/comfil-draft-entradas/scripts/deploy_wp.py `
  --json workspace/draft-entradas/generados/<slug>/<slug>.wp.json `
  --author-name COMFIL   # opcional: asigna autor (schema Author de Yoast)
```

**n entradas (lote):** `deploy_all.py` itera `workspace/draft-entradas/generados/<slug>/.wp.json`
(su default ya apunta ahi); propaga el autor a todas:
```powershell
py .agents/skills/comfil-draft-entradas/scripts/deploy_all.py `
  --author-name COMFIL [--dry-run]
```

Crea el post (borrador por defecto), asigna categorias/tags, e importa y fija la
imagen destacada. `--dry-run` muestra el script sin ejecutarlo. El script
resuelve la raiz del proyecto y `wp.ps1` desde su propia ubicacion.

Comportamiento de `deploy_wp.py` (corregido tras pruebas):
- **Pre-check de BD:** antes de crear, verifica la conexion; si el sitio Local
  (comfil-local) no esta arrancado, aborta con mensaje claro y `exit 1` (no
  crashea con error de NULL).
- **Meta SEO (Yoast):** tras crear, fija automaticamente titulo, meta
  description, focus keyword, breadcrumb, cornerstone, schema article type y
  OG/Twitter (title/description/image). La **meta description se trunca a ~156
  caracteres** para que no se recorte en el snippet de Google.
- **Autor del post:** asigna el autor para que el schema `Author` de Yoast no
  quede vacio. Pasa `--author <ID>` o `--author-name <login>` (el login se
  resuelve a ID); si no, se crea con el autor por defecto.
- **Imagen destacada:** si no se importa, el post se crea igual (no fatal).

> El JSON es el contrato de autodespliegue: cualquier sistema (Activepieces,
> CRON, CI) puede leer `entradas/*.wp.json` y llamar a `deploy_wp.py`.

### 6b. Campos Yoast SEO en `meta.json` (opcionales)
Yoast SEO esta activo en el sitio. El pipeline **produce y aplica automaticamente**
todos los meta de SEO por post cuando estan en `meta.json`; si no estan, se usan
valores por defecto sensatos. Claves admitidas en `meta.json`:

| Clave | Meta Yoast que genera | Default si no se indica |
|---|---|---|
| `seo_title` | `_yoast_wpseo_title` (acepta templates `%%title%% %%page%% %%sep%% %%sitename%%`) | el titulo |
| `seo_description` | `_yoast_wpseo_metadesc` (truncada a ~156 chars) + OG/Twitter desc | el extracto |
| `focus_keyword` | `_yoast_wpseo_focuskw` | vacio |
| `schema_article_type` | `_yoast_wpseo_schema_article_type` (`Article`, `NewsArticle`, `BlogPosting`…) | `Article` |
| `breadcrumb_title` | `_yoast_wpseo_bctitle` | vacio |
| `is_cornerstone` | `_yoast_wpseo_is_cornerstone` | 0 |
| `canonical` | `_yoast_wpseo_canonical` | vacio (WP usa la URL propia) |
| `og_title` / `og_description` | `_yoast_wpseo_opengraph-title/-description` | titulo / metadesc |
| `twitter_title` / `twitter_description` | `_yoast_wpseo_twitter-title/-description` | = OG |

Ejemplo:
```json
{
  "title": "Periodismo y jóvenes: la brecha que crece y quiénes intentan cerrarla",
  "slug": "periodismo-jovenes-brecha-confianza-formacion",
  "seo_title": "%%title%% %%page%% %%sep%% %%sitename%%",
  "seo_description": "El Digital News Report 2026: por primera vez las redes sociales superan a la TV como fuente de noticias.",
  "focus_keyword": "periodismo jóvenes",
  "schema_article_type": "NewsArticle",
  "breadcrumb_title": "Periodismo y jóvenes",
  "categories": ["Comunicación"],
  "tags": ["Periodismo juvenil", "Desinformación"]
}
```

`build_wp_entry.py` vuelca estos campos en el bloque **`yoast`** del
`<slug>.wp.json`, y `deploy_wp.py` los escribe como meta de Yoast al crear el
post. Asi, cada entrada sale con SEO completo (no solo OG/Twitter) sin tocar el
editor. Para el **autor** (schema `Author`), pasa `--author-name <login>` en el
despliegue; se recomienda `COMFIL`.

### 6c. Despliegue a PRODUCCION (vía SSH con paramiko + WP-CLI remoto)
Para publicar en el sitio de producción se usa **`deploy_prod_ssh.py`**, que
conecta por SSH al hosting (SiteGround: `ssh.comfil.edu.mx`, ver
`workspace/remote/ssh.txt` y `ssh_lectura_solo.py`) con **paramiko** y ejecuta el
wp-cli del servidor (`cd <WP_ROOT> && wp --url=<URL> …`). Como producción tiene
el plugin Yoast instalado, se aplican **todos** los metas de SEO, sin depender de
la REST API ni de mu-plugins.

El JSON de entrada es el mismo artefacto validado en Local (el contrato de
autodespliegue); no se reescribe.

```powershell
# Una entrada (crea en produccion con status WP_PROD_STATUS, por defecto draft)
py .agents/skills/comfil-draft-entradas/scripts/deploy_prod_ssh.py `
  --json workspace/draft-entradas/generados/<slug>/<slug>.wp.json [--dry-run]

# Lote (--production -> deploy_prod_ssh.py por cada entrada)
py .agents/skills/comfil-draft-entradas/scripts/deploy_all.py --production [--dry-run]
```

Variables que lee del `.env` de la raiz (NO hardcodeadas):
- `WP_PROD_HOST` / `WP_PROD_USER` / `WP_PROD_PORT` / `WP_PROD_PASS` — conexión SSH.
- `WP_PROD_KEY_PASSPHRASE` / `WP_PROD_KEY_FILE` — clave privada (se extrae de `workspace/remote/ssh.txt` a un temporal y se elimina tras usar).
- `WP_PROD_WP_ROOT` — raíz de WordPress en el servidor (`…/public_html`).
- `WP_PROD_URL` — URL pública de producción.
- `WP_PROD_WP` — binario de WP-CLI en el servidor (default `wp`, ya en PATH: `/usr/local/bin/wp`, WP-CLI 2.12).
- `WP_AUTHOR_ID` — ID del autor en producción (en prod el login es `COMFIL` = ID 1, distinto de Local; se lee del .env).
- `WP_PROD_STATUS` — estado por defecto (`draft` | `publish`; se recomienda `draft` para revisión previa).

Notas del modo producción:
- **Pre-check:** `wp core version` remoto antes de crear; si el SSH/credenciales fallan, aborta con mensaje claro.
- Aplica categorías, tags (crea las que falten), imagen destacada (solo si es **URL pública**) y el bloque **`yoast`** completo igual que en Local (verificado en prod: `_yoast_wpseo_title`, `_metadesc`, `_focuskw`, `_bctitle`, `_is_cornerstone`, `_schema_article_type`, OG/Twitter, canonical).
- Es **crear nuevo** (no actualiza por slug): para re-desplegar, borra el borrador en producción primero.
- Las credenciales SSH viven en `workspace/remote/ssh.txt` (ignorado por git). No se comprometen.

## Notas
- No uses scrappers: el banco de noticias ya lo aporta Activepieces.
- El sitio destino es WordPress local (Local by Flywheel). El wrapper `wp.ps1`
  de la raiz ya resuelve PHP/BD; no pases `--path`/`--url`.
- Si falta `blog`, `blog-seo-check` o `blog-taxonomy`, instalarlas con
  `find-skills` (o clonar desde el registry) antes de continuar.
- El despliegue requiere que el sitio Local este iniciado; si falla con
  "Error establishing a database connection", arranca comfil-local en Local y
  reintenta.

## Aprendizajes operativos (agnósticos al tema)
Reglas de ejecución y calidad detectadas en el uso real. No dependen del tema de la entrada.

### WP-CLI / taxonomía
- `wp post term set` **reemplaza** los términos, no añade. Pasa **todos** los términos en **una sola llamada** y por **slug**; nunca pases ids numéricos (los interpreta como nombre y crea términos basura).
- Tras **actualizar el contenido** de un post existente, **re-aplica taxonomía y categoría primaria** (pueden perderse).
- Las **categorías y tags pueden diferir entre local y producción**. No asumas que coinciden: resuelve cada término por nombre/slug en el sitio destino.

### Despliegue
- `deploy_wp.py` (local) y `deploy_prod_ssh.py` fijan `_yoast_wpseo_primary_category` con la primera categoría del JSON.
- `deploy_prod_ssh.py` es **crear nuevo**; para actualizar sin duplicar usa **`--update`** (resuelve el post por slug y lo actualiza).
- Editar contenido en remoto requiere subir el HTML a un temporal y `--post_content="$(cat archivo)"`.

### Verificación
- En PowerShell, la salida de `wp.ps1` llega como **array de líneas**: únela con `-join` antes de buscar substrings (`Contains`/`Length` dan falsos negativos).
- Antes de desplegar, **valida que los enlaces internos existan** en el entorno destino (posts publicados).
- La puntuación de Yoast se **recalcula al abrir/guardar** el post en el editor; el `_yoast_wpseo_linkdex` guardado puede estar desactualizado.

### Embeds y bloques
- X/Twitter **no** tiene iframe nativo. Opciones: pegar la URL sola (oEmbed de WP), el embed oficial `blockquote`+`widgets.js`, o el iframe `https://platform.twitter.com/embed/Tweet.html?id=<status_id>`.
- `build_wp_entry.py` auto-embebe **YouTube**; pasa `<iframe>` y `<details>` (bloque FAQ nativo `wp:details`). Las **imágenes markdown `![]()` no están soportadas**: usa HTML `<figure><img …></figure>`.

### Editorial / legal (agnóstico al tema)
- **No reproduzcas** desinformación o montajes con la **imagen real de personas identificables**; usa material simbólico.
- **Material oficial con licencia**: úsalo con atribución; los **logos de organismos** suelen tener uso restringido.
- **Verifica la atribución** de fuentes secundarias y **señala discrepancias** con la fuente original (no las repitas como hecho).
