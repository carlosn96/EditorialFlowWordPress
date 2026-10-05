# Changelog

Todos los cambios relevantes de EditorialFlow. Formato basado en
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y versionado semántico.

## [Unreleased]

### Añadido
- Compuerta de evaluacion de redaccion (`references/eval-redaccion.md`, PASS/FAIL) y nuevos patrones de IA a eliminar + lista de palabras/frases + principios de edicion, inspirados en `petergyang/no-ai-slop`.
- Estructura inicial: `skill/SKILL.md`, `scripts/` (build y deploy), `references/brand-voice.md`.
- `deploy_prod_ssh.py`: modo `--update` (actualizar por slug sin duplicar).
- `deploy_wp.py` y `deploy_prod_ssh.py`: fijan `_yoast_wpseo_primary_category`.
- `build_wp_entry.py`: soporte de `<details>` → bloque FAQ nativo (`wp:details`).
- `SKILL.md`: sección de aprendizajes operativos (topics-agnósticos).

### Notas
- Los scripts son agnósticos al tema: categorías/tags se resuelven por slug/nombre
  en el sitio destino.
