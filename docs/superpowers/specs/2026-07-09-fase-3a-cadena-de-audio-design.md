# Fase 3A — Cadena de audio y prosodia — Design

**Fecha:** 2026-07-09
**Estado:** Aprobada
**Roadmap:** `docs/superpowers/specs/2026-07-08-rework-roadmap.md` (Fase 3)

---

## Objetivo

Que el podcast **deje de sonar robótico** sin cambiar de motor de voz. El diagnóstico
apunta a la cadena de audio, no a edge-tts (que usa voces neuronales de Microsoft).

## Descomposición de la Fase 3

La Fase 3 son cuatro subproyectos independientes. Esta spec cubre **A + B**:

| | Subproyecto | Estado |
|---|---|---|
| **A** | Cadena de audio: parser, pausas, mastering | **esta spec** |
| **B** | Prosodia (`rate` por personaje) | **esta spec** |
| C | Motor de voz dual (portátil CPU / torre RTX 3060) | diferido |
| D | Locución en paralelo (hoy secuencial) | diferido |

C y D se abordan **después de escuchar** el resultado de A+B.

## Diagnóstico (causas del sonido robótico)

1. **`crossfade=250` entre fragmentos de voz** (`editor.py:57`). Cada línea es un MP3
   independiente y se pegan solapando 250 ms: el final de cada frase se mezcla con el
   principio de la siguiente. Además **no hay ninguna pausa entre turnos**.
2. **Parser de locutor por `in` en vez de `startswith`** (`locutor.py:29,33`). Una línea
   que mencione a otro locutor se atribuye mal, y `split(":", 1)` corta por el primer
   dos puntos, que puede no ser el del hablante.
3. **La "EQ" no es una EQ** (`editor.py:29`):
   `audio.low_pass_filter(3000).apply_gain(1.5).overlay(audio)` suma una copia filtrada
   sobre el original → enturbia y arriesga saturación.
4. **`normalize(headroom=0.1)`** (`editor.py:32`) deja solo 0,1 dB de margen: nivel
   altísimo, muy por encima de cualquier estándar de podcast.
5. **Prosodia sin usar**: `edge_tts.Communicate` acepta `rate`/`pitch`/`volume` y no se
   pasa ninguno. Todo sale al mismo ritmo.

## Decisiones cerradas

| Tema | Decisión |
|------|----------|
| Alcance | A (cadena) + B (prosodia). C y D diferidos |
| Voces | Álex = `es-ES-AlvaroNeural` (masculino, España); María = `es-ES-ElviraNeural` (femenino, España) |
| Personaje | **Santi → María**, mujer. edge-tts solo tiene **una** voz masculina de España, así que dos hombres castellanos es imposible con este motor |
| Pausa entre turnos | **350 ms** de silencio (configurable). Fuera el `crossfade` entre voces |
| Mastering | Fuera la falsa EQ. `high_pass_filter(80)` → normalizar → compresión suave → `headroom=1.0` |
| Loudness LUFS | **Diferido.** `pyloudnorm` + `numpy` se valorarán tras escuchar. Añadir dependencia antes de oír el resultado es prematuro |
| Prosodia | `rate` por personaje: Álex `-4%`, María `+6%`. **No** se toca `pitch` (suena artificial en voces neuronales) |
| Validación | Nuevo modo `--solo-audio --guion RUTA` |

### Por qué edge-tts limita las voces

`edge_tts.list_voices()` devuelve solo **tres** voces `es-ES`:
`AlvaroNeural` (masc., España), `ElviraNeural` (fem., España) y `XimenaNeural`
(fem., **Colombia** pese a la etiqueta). Santi está hoy locutado por Ximena: voz
femenina y acento colombiano, lo que además incumple la regla de "español de España".

Consecuencia asumida: María pasa a ser mujer también **en el texto** (concordancia
femenina, se tratan de "tía"). Hoy el guion tiene a Santi diciendo "flipado" y a los dos
llamándose "tío" (6 veces) y "macho" (3).

## Arquitectura

```
src/noticia/
  locutor.py   (CAMBIA)  → _parsear_linea() pura + prosodia por personaje
  editor.py    (CAMBIA)  → pausas en vez de crossfade; cadena de mastering sana
  config.py    (CAMBIA)  → voz_alex/voz_maria, rate por personaje, pausa_entre_turnos_ms
                           (el campo voz_santi se renombra a voz_maria)
  cli.py       (CAMBIA)  → modo --solo-audio --guion RUTA
reglas/
  instrucciones.md, contexto.md  (CAMBIAN) → Santi → María, mujer
```

### El bucle de validación

Hoy, oír un cambio de audio obliga a regenerar el guion: ~14 min y cuota de Max. El modo
`noticia --solo-audio --guion RUTA` lee un guion ya escrito, lo trocea por bloques
(`## espana`, …) reutilizando `_ORDEN_BLOQUES`, y produce el MP3. Iterar sobre pausas y
mastering pasa de 15 minutos a segundos.

> Los guiones ya generados usan "Santi:". Para validar con ellos, renombrar a "María:"
> (p. ej. `sed`) o regenerar el guion.

### `locutor.py`

```python
def _parsear_linea(linea: str) -> tuple[str, str] | None:
    """"Álex: hola" -> ("alex", "hola"). None si la línea no es diálogo.

    Compara con startswith sobre el prefijo normalizado (minúsculas, sin tilde),
    y corta por el dos puntos DEL PREFIJO, no por el primero que aparezca.
    """
```

`procesar_guion_a_audio` usa `_parsear_linea`, elige voz y `rate` por locutor desde
`settings`, y llama a `edge_tts.Communicate(texto, voz, rate=rate)`.

### `editor.py`

```python
def aplicar_mastering(audio):
    audio = audio.high_pass_filter(80)          # limpia retumbe (EQ de verdad)
    audio = effects.normalize(audio)
    audio = effects.compress_dynamic_range(audio, threshold=-18.0, ratio=2.5,
                                           attack=5.0, release=50.0)
    return effects.normalize(audio, headroom=1.0)
```

En el montaje, los fragmentos de voz se unen con **silencio** entre ellos, mediante una
función pura y testeable:

```python
def _unir_con_pausas(segmentos, pausa_ms):
    """Concatena segmentos separándolos por silencio. Sin crossfade.

    Longitud resultante = sum(len(s)) + pausa_ms * (len(segmentos) - 1)
    """
```

El crossfade **entre bloques** (1000 ms) y la mezcla con sintonías no se tocan.

### Interrupciones (fuera de alcance)

Las reglas piden que Álex y María *"se interrumpan levemente"*. Eso es un solapamiento
**intencionado y puntual**, no un crossfade uniforme en todos los turnos. Se aborda más
adelante; primero que el diálogo respire.

## Testing

Deterministas, sin red ni TTS real:

| Test | Qué verifica |
|------|--------------|
| `test_locutor.py` | `_parsear_linea`: casos correctos; línea de María que menciona "Álex:" se atribuye a María; dos puntos dentro de la frase ("a las 15:30") no rompen el corte; línea sin locutor → `None` |
| `test_locutor.py` | `procesar_guion_a_audio` pasa el `rate` correcto por locutor (mock de `edge_tts.Communicate`) |
| `test_editor.py` | `aplicar_mastering` sobre un `AudioSegment` sintético (tono): el resultado deja al menos 1 dB de margen (`max_dBFS <= -1.0`) |
| `test_editor.py` | `_unir_con_pausas`: la longitud resultante es `sum(len(s)) + pausa_ms * (n-1)`, y con un solo segmento no añade silencio |
| `test_cli.py` | `--solo-audio --guion RUTA` trocea el `.md` por bloques y no invoca la generación de guion |

## Verificación de la fase

- Suite verde, `ruff check` y `ruff format --check` limpios.
- Manual: `uv run noticia --solo-audio --guion output/guion_verificacion.md` y **escuchar**.
  Criterio: los turnos no se pisan, hay pausa natural, no hay saturación ni turbieza.

## Riesgos

- El episodio ronda las 8.900 palabras (~1 h de audio). Con locución secuencial el render
  puede tardar; si molesta al iterar, se adelanta el subproyecto **D** (paralelo).
- `pydub` emite `DeprecationWarning` de `audioop` en Py3.12 (deuda conocida, no bloquea).
- Cambiar Santi→María toca `reglas/` y por tanto el estilo del guion: hay que regenerar un
  guion para ver la concordancia femenina en acción.
