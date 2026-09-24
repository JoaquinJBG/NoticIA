# Guion: duración, fútbol y ritmo — Diseño

**Fecha:** 2026-09-24
**Estado:** Pendiente de revisión
**Contexto:** primer sub-proyecto de la tanda de mejoras "que se escuche mucho mejor sin GPU".
Los siguientes (memoria entre episodios, voz en CPU, sintonía) van en specs propios.

---

## Objetivo

Que el episodio diario sea más ameno y más corto, sin cambiar de motor de voz:

- **Duración total de 40-50 minutos** (hoy, 63 min).
- **Fútbol en 3-4 minutos**, como resumen de los resultados reales de los partidos importantes.
- **Ritmo de conversación más natural**: réplicas cortas, interrupciones y pausas variables.

El oyente es el propio autor (uso personal). El episodio se lanza a mano.

### Criterios de éxito

1. Un episodio completo dura entre 40 y 50 minutos.
2. El bloque de fútbol dura entre 3 y 4 minutos y solo cita marcadores que vienen de la fuente de datos.
3. Las pausas entre turnos ya no son todas iguales, y el guion incluye réplicas cortas e interrupciones.
4. Si la fuente de resultados falla, el episodio se genera igual.
5. Los tests nuevos pasan sin red. `ruff` y la suite completa, en verde.

---

## Situación actual (medida en el episodio del 2026-09-24)

Todos los bloques reciben la misma instrucción ("charlad durante 8-10 minutos"). Resultado:

| Bloque | Duración real |
|---|---|
| Intro | 1,6 min |
| España | 7,1 min |
| Geopolítica | 10,1 min |
| IA y actualidad | 8,4 min |
| Ciencia | 14,1 min |
| Friki | 11,7 min |
| Fútbol | 8,0 min |
| Outro | 2,3 min |
| **Total** | **63,3 min** |

edge-tts habla a unas **150 palabras por minuto** (medido: 2139 palabras → 14,1 min en Ciencia).
El bloque de fútbol se alimenta de noticias de prensa (fichajes, polémicas), no de resultados.
Las pausas son de 350 ms exactos entre todos los turnos (`settings.pausa_entre_turnos_ms`).

---

## 1. Presupuesto de palabras por bloque

**`bloques.py`** gana una constante:

```python
PALABRAS_POR_MINUTO = 150

PALABRAS_OBJETIVO: dict[str, int] = {
    "intro": 150,             # 1 min
    "espana": 1200,           # 8 min
    "geopolitica": 1200,      # 8 min
    "ia_y_actualidad": 1050,  # 7 min
    "ciencia": 1050,          # 7 min
    "friki": 1200,            # 8 min
    "futbol": 525,            # 3,5 min
    "outro": 225,             # 1,5 min
}
```

Suman 6600 palabras, unos 44 minutos de voz. Con pausas y sintonías, el total queda en ~46-47 minutos.

**`generador.py`:**

- `construir_bloque_con_contexto` sustituye "Charlad durante 8-10 minutos" por
  "El bloque debe tener unas {N} palabras de diálogo (unos {N/150} minutos)".
- Añade la instrucción: **"De las noticias de la lista, elegid las 3-4 más interesantes y
  profundizad en ellas; no hace falta comentarlas todas."** La selección sigue entregando
  8 noticias por bloque, para que Claude tenga donde elegir.
- `generar_intro` y `generar_outro` reciben también su objetivo de palabras.
- Tras generar cada bloque, se cuentan sus palabras. Si se desvían más de un **25 %** del
  objetivo, se registra un `WARNING` con el bloque, las palabras reales y las objetivo.
  **Sin reintento** en esta iteración: primero se mide cuánto se desvía Claude en la práctica.

---

## 2. Fútbol: resultados reales

### Fuente de datos

API pública de ESPN, sin clave:

```
https://site.api.espn.com/apis/site/v2/sports/soccer/{liga}/scoreboard?dates=YYYYMMDD
```

Verificado el 2026-09-24:
- Devuelve los partidos del día con marcador, estado y goleadores (`competitions[0].details`,
  con `scoringPlay: true`).
- **No admite rangos de fechas** (`dates=A-B` → HTTP 400): hay que hacer una petición por
  competición y día.
- **Responde comprimido con gzip**: hay que descomprimir la respuesta.
- El local y el visitante se distinguen por el campo `homeAway` de cada `competitor`,
  **no por su posición** en la lista.

Competiciones, en orden de prioridad para el guion:

| Código ESPN | Nombre | Filtro |
|---|---|---|
| `esp.1` | LaLiga | — |
| `uefa.champions` | Champions League | — |
| `uefa.europa` | Europa League | — |
| `uefa.europa.conf` | Conference League | — |
| `eng.1` | Premier League | — |
| `ita.1` | Serie A | — |
| `ger.1` | Bundesliga | — |
| `fra.1` | Ligue 1 | — |
| `uefa.nations` | Nations League | solo partidos de España |
| `fifa.worldq.uefa` | Clasificación Mundial (UEFA) | solo partidos de España |
| `fifa.friendly` | Amistosos internacionales | solo partidos de España |

### Módulo nuevo `src/noticia/resultados_futbol.py`

```python
@dataclass(frozen=True)
class Gol:
    jugador: str
    minuto: str          # "72'", tal como lo da ESPN
    equipo: str

@dataclass(frozen=True)
class Partido:
    competicion: str     # nombre legible ("LaLiga")
    prioridad: int       # posición en la tabla de competiciones
    inicio: datetime     # en hora de Madrid
    local: str
    visitante: str
    goles_local: int
    goles_visitante: int
    goles: tuple[Gol, ...]

def obtener_resultados(fecha: date, dias: int = 3, timeout: float = 10) -> list[Partido]: ...
def formatear_resultados_prompt(partidos: list[Partido], maximo: int = 25) -> str: ...
def resultados_a_json(partidos: list[Partido]) -> list[dict]: ...
```

- `obtener_resultados` consulta los días `fecha-1` … `fecha-dias`. Son 11 × 3 = 33 peticiones,
  en paralelo con `ThreadPoolExecutor`, igual que la ingesta. Usa `urllib` de la librería
  estándar con descompresión gzip: sin dependencias nuevas.
- Solo se quedan los partidos con `status.type.completed == true` (así entran también los
  que acaban en prórroga o penaltis).
- Se deduplican por id de evento: un partido nocturno puede aparecer en dos días, porque ESPN
  agrupa por su propia zona horaria.
- En las competiciones con filtro "solo España" se descartan los partidos en los que no juega España.
- Una petición que falla (timeout, HTTP ≠ 200, JSON inválido o un campo que falta) registra
  un `WARNING` y se ignora. Si fallan todas, devuelve `[]`. **Nunca lanza excepción.**
- `formatear_resultados_prompt` ordena por prioridad de competición y luego por fecha, y
  recorta a `maximo` partidos. Formato de cada línea:
  `<Competición> (<día abreviado> <n.º>): <Local> <g>-<g> <Visitante> — goles: <Jugador> <min>', …`
  (por ejemplo, `LaLiga (dom 20): Atlético 2-1 Real Madrid — goles: …`). Si ESPN no trae
  goleadores, se omite el tramo "— goles:".

### Integración

- `orquestador.generar_guion` llama a `obtener_resultados(fecha)` **una vez**, antes del bucle
  de reintentos, y pasa el resultado a `construir_guion(noticias, fecha, resultados_futbol=...)`.
- Guarda `resultados_futbol.json` en la carpeta del episodio, junto a `noticias.json`, para
  poder comprobar después si algún marcador se inventó.
- `generador.construir_guion`, para el bloque `futbol`:
  - **Con resultados:** llama a una función nueva, `construir_bloque_futbol(resultados,
    noticias, fecha)`. No hace briefing de investigación: los resultados no necesitan
    contexto histórico y así se ahorra una llamada a Claude. El prompt pide:
    - un repaso ágil de ~525 palabras;
    - primero LaLiga y los equipos españoles en Europa, y después lo más llamativo del resto;
    - usar como mucho 2-3 titulares de prensa de la lista, y solo como contexto;
    - **"No menciones ningún marcador ni goleador que no aparezca en la lista de resultados."**
  - **Sin resultados** (fallo o 0 partidos): se usa el flujo actual con noticias de prensa,
    con el objetivo de 525 palabras.
  - Sin resultados y sin noticias: el bloque se omite, como ahora.

---

## 3. Ritmo de conversación

### En el guion (`reglas/instrucciones.md`)

Se amplía la sección **PAUTAS DE ENTRETENIMIENTO**:

- **Réplicas cortas:** aproximadamente uno de cada cinco turnos es una reacción breve de 1 a
  5 palabras ("¡No me digas!", "Ya, ya", "Espera, espera", "Hombre, claro").
- **Interrupciones:** algunas veces por bloque, un turno queda cortado con "…" y el otro
  locutor entra reaccionando.
- **Prohibido escribir risas** ("jaja", "jeje", "(risas)") y acotaciones entre paréntesis:
  el motor de voz las lee literalmente. La complicidad se expresa con palabras.

### Red de seguridad en la limpieza de texto

`voz/texto.py` (`limpiar_texto_locucion`) elimina las risas escritas que se cuelen en el guion:
palabras sueltas `ja`, `jaja`, `jajaja`… y `je`/`jeje`…, sin distinguir mayúsculas, y la
acotación `(risas)`. Si un turno queda vacío tras limpiarlo, ya se descarta hoy con un warning.

### Pausas variables: módulo nuevo `src/noticia/ritmo.py`

```python
def calcular_pausas(textos: Sequence[str], semilla: str) -> list[int]:
    """Milisegundos de silencio tras cada turno (len(textos) - 1 valores)."""
```

La pausa **entre el turno i y el i+1**:

| Caso (se evalúa en este orden) | Pausa |
|---|---|
| El turno i acaba en "…" o "..." (interrupción) | 60 ms |
| El turno i o el i+1 tiene ≤ 5 palabras (réplica corta) | aleatoria entre 150 y 250 ms |
| Resto | aleatoria entre 280 y 480 ms |

- Se usa un `random.Random(semilla)` propio, nunca el global. La semilla es `"{fecha}:{bloque}"`,
  así que el mismo guion siempre produce el mismo audio.
- Los rangos son constantes del módulo, no ajustes de `Settings`: se afinan de oído y en código.

### Cómo llega el texto al montaje

Hoy el editor solo recibe rutas de audio. Cambios:

- `ResultadoLocucion` gana `textos_por_bloque: dict[str, list[str]]`: el texto de los turnos
  **locutados con éxito**, en el mismo orden que `fragmentos_por_bloque`. Si un turno falla,
  no aparece en ninguna de las dos listas y siguen alineadas.
- `editor.ensamblar_podcast_dinamico` acepta un parámetro opcional
  `pausas_por_bloque: Mapping[str, Sequence[int]] | None = None`.
  `_unir_con_pausas` pasa a aceptar una lista de pausas. Si no llega (por ejemplo, en
  `--solo-audio` o en código antiguo) o su longitud no cuadra con los fragmentos, se usa la
  pausa fija `settings.pausa_entre_turnos_ms`, como ahora (y, si no cuadra, con un `WARNING`).
- `orquestador` calcula `pausas_por_bloque` con `ritmo.calcular_pausas` a partir de
  `textos_por_bloque` y se lo pasa al editor.

---

## Tests

Todos sin red ni audio real, siguiendo los patrones de `tests/`:

- **`test_resultados_futbol.py`** (nuevo), con un JSON de ESPN guardado en `tests/datos/`:
  - parseo correcto del local y el visitante por `homeAway`, aunque lleguen en orden invertido;
  - solo partidos con `completed`;
  - deduplicación por id de evento;
  - filtro "solo España" en selecciones;
  - goleadores extraídos solo de `scoringPlay`;
  - respuesta gzip descomprimida;
  - una petición que falla no rompe las demás; si fallan todas, devuelve `[]`;
  - orden por prioridad y recorte a `maximo` en `formatear_resultados_prompt`.
- **`test_ritmo.py`** (nuevo): tres casos de pausa; determinismo con la misma semilla; semillas
  distintas dan pausas distintas; longitud `len(textos) - 1`; lista vacía o de un solo turno.
- **`test_generador.py`:**
  - el prompt de cada bloque contiene su objetivo de palabras;
  - el bloque `futbol` con resultados usa `construir_bloque_futbol` y no llama al briefing;
  - sin resultados, cae al flujo de noticias;
  - `WARNING` cuando el bloque se desvía más del 25 %.
- **`test_editor.py`:** pausas por turno aplicadas; fallback a pausa fija si faltan o no cuadran.
- **`test_locutor.py`:** `textos_por_bloque` alineado con `fragmentos_por_bloque`, también con
  turnos fallidos.
- **`test_voz_texto.py`:** eliminación de `jaja`, `JAJAJA`, `jeje` y `(risas)`, sin tocar palabras
  como "jamón" o "Jaén".
- **`test_orquestador.py`:** `resultados_futbol.json` guardado; `generar_guion` pasa los
  resultados al generador.

## Validación manual

1. Generar un episodio completo con `make episodio` y comprobar en `episodio.json` que la
   duración está entre 40 y 50 minutos, y que el capítulo de fútbol dura 3-4 minutos.
2. Contrastar los marcadores que se dicen en el bloque de fútbol con `resultados_futbol.json`.
3. Escucharlo y valorar el ritmo de oído. Los rangos de pausa se ajustan en `ritmo.py` si hace falta.

## Fuera de alcance

- Memoria entre episodios.
- Motor de voz en CPU.
- Sintonías nuevas.
- Reintento automático cuando un bloque se desvía del presupuesto de palabras (se decide
  después de medir).
- Clasificaciones de liga o partidos en directo.
