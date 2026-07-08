# Rework de NoticIA — Hoja de ruta

**Fecha:** 2026-07-08
**Estado:** Aprobada
**Sustituye a:** `ROADMAP_PRO.md` (se elimina en la Fase 0)

---

## Visión

NoticIA es un **podcast diario automatizado** que se quiere llevar al máximo nivel:
publicado a diario, fiable y de bajo coste, con guion de alta calidad.

**Decisiones de producto cerradas:**

| Tema | Decisión |
|------|----------|
| Objetivo | Podcast **publicado a diario**, automatizado y de bajo coste |
| Cerebro del guion | **Claude vía suscripción Max** (Claude Agent SDK / Claude Code headless), no la API de pago |
| Cuándo se genera | **Por la tarde**, cuando el usuario no trabaja (respeta los límites de uso de Max) |
| Dónde corre la generación | **En la máquina del usuario** (WSL), donde vive el login de Claude — no en un cron cloud anónimo |
| Publicación | **RSS propio** (alimenta Spotify/Apple) + **YouTube** (vídeo encima del audio) |

**Restricción arquitectónica clave:** como el cerebro usa la suscripción Max, la
generación está anclada a la máquina logueada en Claude. El modelo es
*ejecución local programada por la tarde → genera guion (Claude/Max) → produce audio →
publica automáticamente*. Requiere que el equipo esté encendido a esa hora.

---

## Fases

Cada fase tiene su propio ciclo spec → plan → implementación. Se abordan en orden;
la Fase 0 es prerrequisito del resto.

### Fase 0 — Fundamentos, seguridad y estructura *(prerrequisito)*
Reestructurar a paquete limpio (`src/noticia/`, `pyproject.toml`, `uv`, `ruff`, `pytest`),
config tipada, `logging`, manejo de errores, tests base, borrado de código muerto,
`CLAUDE.md` del proyecto. **Nota de seguridad:** verificado que `.env` y `credentials.json`
NO están en git ni en el historial (están en `.gitignore`); no hay claves que rotar.

- Spec: `docs/superpowers/specs/2026-07-08-fase-0-fundamentos-design.md`

### Fase 1 — Ingesta multifuente con contraste
Ejecutar (revisado, adaptado a la nueva estructura de paquete) el plan ya escrito:
muchas fuentes → agrupar la misma noticia entre medios → clusters para contraste a ciegas.

- Spec: `docs/superpowers/specs/2026-05-22-ingesta-multifuente-contraste-design.md`
- Plan: `docs/superpowers/plans/2026-05-22-ingesta-multifuente-contraste.md`

### Fase 2 — Cerebro Claude (Max vía Agent SDK) ⭐
Sustituir Groq/Llama 3.3 por Claude. Rediseñar la generación del guion: contraste real
a ciegas para neutralidad, personalidades de Álex y Santi, estructura y química. Es el
salto de calidad principal. Primera skill de Claude Code natural aquí ("generar episodio
de prueba").

### Fase 3 — Producción de audio
Locución en paralelo (hoy es secuencial), parser de locutor robusto (`startswith` en vez
de `in`), arreglo del mastering/EQ y del diseño sonoro dinámico.

### Fase 4 — Publicación
Feed RSS propio + metadatos de episodio + hosting → luego generación de vídeo y subida a
YouTube reutilizando el mismo audio.

### Fase 5 — Orquestación y automatización
Ejecución programada por la tarde, idempotencia (no repetir episodio), recuperación de
errores, notificación al terminar o fallar.

### Transversal — Skills e instrucciones de Claude Code
Se crean cuando surge la necesidad concreta, no todas de golpe.

---

## Deuda técnica detectada (se aborda en su fase)

- `test_5min.py` no ejecuta nada (falta `asyncio.run`) → se elimina en Fase 0.
- Locución TTS secuencial, paralelizable → Fase 3.
- Mastering con "EQ" mal planteada y `normalize(headroom=0.1)` agresivo → Fase 3.
- Locutor usa `in` en vez de `startswith` para detectar hablante → Fase 3.
- `except:` desnudos y `print` en vez de `logging` → Fase 0 (módulos actuales) y Fase 1 (ingesta).
