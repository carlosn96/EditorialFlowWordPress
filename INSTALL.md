# INSTALL — EditorialFlow

## Requisitos
- Python 3.
- WP-CLI: wrapper `wp.ps1` en la raíz del proyecto, o `wp` en PATH (o define `WP_CLI_COMMAND`).
- Para producción: `pip install paramiko` y las variables `WP_PROD_*` en el `.env`.

## Instalar (instrucción)

Ejecuta el instalador apuntando a la **raíz del proyecto destino**:

```powershell
py scripts/install.py --project-root "C:\ruta\al\proyecto" `
   --skill-name comfil-draft-entradas --brand comfil
```

- `--skill-name`: nombre de la carpeta del skill; el instalador ajusta el `name:`
  del frontmatter para que coincida.
- `--brand`: copia un perfil de marca; sin él copia **todos** los de `brands/`.
- Es **idempotente**: vuelve a ejecutarlo para actualizar.

El instalador copia:

1. El SKILL y los scripts en `<proyecto>/.agents/skills/<skill-name>/`.
2. Los perfiles de marca en `<proyecto>/brands/`.

## Activar la marca

Agrega al `.env` del proyecto (o al entorno):

```
EDITORIALFLOW_BRAND=comfil
```

## Verificar

```powershell
py .agents/skills/<skill-name>/scripts/config.py
```

Debe imprimir la configuración de la marca activa (`internal_domains`, `author`…).

## Cómo lo descubre un agente nuevo

- El `AGENTS.md` de la raíz del proyecto indica leer
  `.agents/skills/<skill-name>/SKILL.md` y seguir el flujo.
- Si el entorno soporta skills, aparece el skill `<skill-name>` en la lista y se
  carga al detectar la tarea.
