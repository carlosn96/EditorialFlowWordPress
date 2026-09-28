# AGENTS.md — EditorialFlow

Guía para agentes que operan este repo.

## Qué es

Motor editorial que convierte borradores en entradas de WordPress desplegables,
para local y producción. **Agnóstico al tema y al sitio**: la configuración entra
por `meta.json` (por entrada) y `.env` (por entorno).

## Reglas de oro

- No inventes datos ni URLs. Todo dato/cita lleva fuente verificable citada.
- No versiones secretos (`.env`, `ssh.txt`) ni salidas de `workspace/`.
- Mantén el código **agnóstico**: sin temas, categorías ni etiquetas hardcodeadas.
- Cambios en `scripts/` o `skill/` deben **sincronizarse** a
  `<proyecto>/.agents/skills/comfil-draft-entradas/` para que el pipeline los use.

## Mapa de archivos

- `skill/SKILL.md` — el pipeline completo (pasos, reglas editoriales, checklist).
- `references/brand-voice.md` — voz de marca y pautas.
- `scripts/build_wp_entry.py` — borrador → artefacto.
- `scripts/deploy_wp.py` / `scripts/deploy_prod_ssh.py` — despliegue local / producción.
- `scripts/build_all.py` / `scripts/deploy_all.py` — lotes.

## Comandos útiles

```powershell
py scripts/deploy_prod_ssh.py --json <...>.wp.json --dry-run    # ver acciones
py scripts/deploy_prod_ssh.py --json <...>.wp.json --update     # actualizar por slug
```

## Commits

Conventional commits: `feat(scope): ...`, `fix(scope): ...`, `docs: ...`, `chore: ...`.
