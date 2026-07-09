# Cadena de audio y prosodia (Fase 3A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el podcast deje de sonar robótico sin cambiar de motor de voz: parser de locutor real, pausas naturales entre turnos, mastering sano y prosodia por personaje.

**Architecture:** `locutor.py` gana una función pura `_parsear_linea` y pasa `rate` por personaje a edge-tts. `editor.py` sustituye el crossfade entre voces por silencio (`_unir_con_pausas`, función pura) y arregla la cadena de mastering. `cli.py` gana un modo `--solo-audio --guion RUTA` para iterar sobre el audio sin regenerar el guion. Santi pasa a ser **María**, mujer, porque edge-tts solo tiene una voz masculina de España.

**Tech Stack:** Python 3.12, `edge-tts`, `pydub`, `pytest`, `uv`, `ruff`. Sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-07-09-fase-3a-cadena-de-audio-design.md`

## Global Constraints

- Dominio en **español** (nombres de funciones y variables).
- **`logging`**, nunca `print`; logger vía `logging.getLogger("noticia.<modulo>")`.
- Nada de `except:` desnudo: `except Exception as exc:` (o excepción concreta) con log.
- Config vía `from noticia.config import settings`, no `os.getenv` suelto.
- `uv` para todo: `uv run pytest`, `uv run ruff check`, `uv run ruff format`.
- Cada tarea termina con `uv run ruff check` y `uv run ruff format --check` limpios antes del commit.
- Commits: Conventional Commits en **español**, **sin** trailer `Co-Authored-By`.
- Tests deterministas: **sin red y sin TTS real** (mock de `edge_tts.Communicate`); audio sintético con `pydub.generators`.
- **Sin dependencias nuevas.** `pyloudnorm`/LUFS están deliberadamente fuera de alcance.
- Locutores exactos: **`Álex`** (masculino) y **`María`** (femenino). Normalizados: `"alex"`, `"maria"`.
- Voces exactas: Álex = `es-ES-AlvaroNeural`; María = `es-ES-ElviraNeural`.
- Fuera de alcance: motor dual con GPU, locución en paralelo, interrupciones intencionadas.

---

## File Structure

| Archivo | Responsabilidad |
|---------|-----------------|
| `src/noticia/config.py` (modificar) | `voz_maria` (renombra `voz_santi`), `rate_alex`, `rate_maria`, `pausa_entre_turnos_ms` |
| `src/noticia/locutor.py` (modificar) | `_normalizar`, `_parsear_linea` (puras) + prosodia por locutor |
| `src/noticia/editor.py` (modificar) | `_unir_con_pausas` (pura), `aplicar_mastering` (renombra `aplicar_mastering_pro`) |
| `src/noticia/cli.py` (modificar) | `_trocear_guion` (pura), `generar_solo_audio`, rutas de `main()` |
| `reglas/instrucciones.md`, `reglas/contexto.md` (modificar) | Santi → María, mujer |
| `tests/test_locutor.py` (crear) | Parser y prosodia |
| `tests/test_editor.py` (crear) | Pausas y mastering |
| `tests/test_cli.py` (modificar) | Troceo del guion y modo `--solo-audio` |
| `tests/test_config.py` (modificar) | Defaults nuevos |

---

## Task 1: `config.py` — voces, prosodia y pausa

**Files:**
- Modify: `src/noticia/config.py:20-24`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `settings.voz_alex: str`, `settings.voz_maria: str`, `settings.rate_alex: str`,
  `settings.rate_maria: str`, `settings.pausa_entre_turnos_ms: int`.

- [ ] **Step 1: Actualizar el test existente y añadir el nuevo**

`tests/test_config.py:6` afirma hoy `config.settings.voz_santi == "es-ES-XimenaNeural"`.
Ese campo desaparece, así que hay que **editar** ese test, no solo añadir otro.

Reemplazar la función `test_settings_valores_por_defecto` completa por:

```python
def test_settings_valores_por_defecto():
    assert config.settings.voz_alex == "es-ES-AlvaroNeural"
    assert config.settings.voz_maria == "es-ES-ElviraNeural"
    assert config.settings.carpeta_output == "output"
    assert config.settings.carpeta_temp == "temp"


def test_prosodia_y_pausa_por_defecto():
    assert config.settings.rate_alex == "-4%"
    assert config.settings.rate_maria == "+6%"
    assert config.settings.pausa_entre_turnos_ms == 350
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL — `AttributeError: 'Settings' object has no attribute 'voz_maria'`.

- [ ] **Step 3: Implementar**

En `src/noticia/config.py`, reemplazar estas dos líneas:

```python
    voz_alex: str = "es-ES-AlvaroNeural"
    voz_santi: str = "es-ES-XimenaNeural"
```

por:

```python
    # edge-tts solo tiene una voz masculina de España (Alvaro), así que María
    # es mujer. Ximena, la voz anterior de Santi, tiene acento colombiano.
    voz_alex: str = "es-ES-AlvaroNeural"
    voz_maria: str = "es-ES-ElviraNeural"

    # Prosodia: Álex es el mentor reflexivo, María el motor de energía.
    # No se toca el pitch: en voces neuronales suena artificial.
    rate_alex: str = "-4%"
    rate_maria: str = "+6%"

    # Silencio entre turnos. El crossfade solapaba sílabas.
    pausa_entre_turnos_ms: int = 350
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS.

- [ ] **Step 5: Lint y formato**

Run: `uv run ruff check src/noticia/config.py tests/test_config.py && uv run ruff format --check src/noticia tests`
Expected: `All checks passed!` y sin reformateos.

- [ ] **Step 6: Commit**

```bash
git add src/noticia/config.py tests/test_config.py
git commit -m "feat: voces de España, prosodia por personaje y pausa entre turnos"
```

---

## Task 2: `locutor.py` — `_parsear_linea` (función pura)

**Files:**
- Modify: `src/noticia/locutor.py`
- Test: `tests/test_locutor.py` (crear)

**Interfaces:**
- Produces: `_parsear_linea(linea: str) -> tuple[str, str] | None` — devuelve
  `("alex" | "maria", texto)` o `None` si la línea no es diálogo.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_locutor.py`:

```python
from noticia import locutor


def test_parsear_linea_alex_y_maria():
    assert locutor._parsear_linea("Álex: hola") == ("alex", "hola")
    assert locutor._parsear_linea("María: qué tal") == ("maria", "qué tal")


def test_parsear_linea_sin_tildes():
    assert locutor._parsear_linea("Alex: hola") == ("alex", "hola")
    assert locutor._parsear_linea("Maria: hola") == ("maria", "hola")


def test_parsear_linea_mencion_de_otro_locutor_no_confunde():
    # El bug antiguo: buscaba "álex:" en CUALQUIER posición y se lo atribuía a Álex.
    linea = "María: y entonces Álex: dijo que no"
    assert locutor._parsear_linea(linea) == ("maria", "y entonces Álex: dijo que no")


def test_parsear_linea_dos_puntos_en_la_frase():
    # split(":", 1) corta por el dos puntos del prefijo, no por el de la hora.
    assert locutor._parsear_linea("Álex: quedamos a las 15:30") == (
        "alex",
        "quedamos a las 15:30",
    )


def test_parsear_linea_no_dialogo_devuelve_none():
    assert locutor._parsear_linea("IMPORTANTE: no inventes hechos") is None
    assert locutor._parsear_linea("una línea cualquiera") is None
    assert locutor._parsear_linea("Santi: ya no existe") is None
    assert locutor._parsear_linea("Álex:") is None  # sin texto
    assert locutor._parsear_linea("") is None
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `uv run pytest tests/test_locutor.py -v`
Expected: FAIL — `AttributeError: module 'noticia.locutor' has no attribute '_parsear_linea'`.

- [ ] **Step 3: Implementar**

En `src/noticia/locutor.py`, añadir `import unicodedata` a los imports y estas funciones justo debajo de `logger = logging.getLogger("noticia.locutor")`:

```python
_LOCUTORES = ("alex", "maria")


def _normalizar(texto: str) -> str:
    """minúsculas y sin tildes, para comparar el prefijo del locutor."""
    texto = texto.strip().lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def _parsear_linea(linea: str) -> tuple[str, str] | None:
    """"Álex: hola" -> ("alex", "hola"). None si la línea no es diálogo.

    El prefijo es lo que hay ANTES del primer dos puntos, y debe ser un locutor
    conocido. Así una mención a otro locutor dentro de la frase no confunde la
    atribución, y un dos puntos dentro del texto no rompe el corte.
    """
    if ":" not in linea:
        return None
    prefijo, resto = linea.split(":", 1)
    locutor = _normalizar(prefijo)
    if locutor not in _LOCUTORES:
        return None
    texto = resto.strip()
    if not texto:
        return None
    return locutor, texto
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `uv run pytest tests/test_locutor.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Lint y formato**

Run: `uv run ruff check src/noticia/locutor.py tests/test_locutor.py && uv run ruff format --check src/noticia tests`
Expected: `All checks passed!`.

- [ ] **Step 6: Commit**

```bash
git add src/noticia/locutor.py tests/test_locutor.py
git commit -m "feat: parser de locutor por prefijo real en vez de subcadena"
```

---

## Task 3: `locutor.py` — usar el parser y aplicar prosodia

**Files:**
- Modify: `src/noticia/locutor.py` (función `procesar_guion_a_audio`)
- Test: `tests/test_locutor.py`

**Interfaces:**
- Consumes: `_parsear_linea` (Task 2); `settings.voz_alex`, `settings.voz_maria`,
  `settings.rate_alex`, `settings.rate_maria` (Task 1).
- Produces: `_voz_y_rate(locutor: str) -> tuple[str, str]`;
  `procesar_guion_a_audio(guion_texto: str) -> list[str]` (rutas de MP3, sin cambio de firma).

- [ ] **Step 1: Añadir los tests que fallan**

Primero, añadir `import asyncio` **al principio** de `tests/test_locutor.py` (antes de
`from noticia import locutor`). Un import a media altura dispara `E402` en ruff.

Luego añadir al final del fichero:

```python
class _FakeCommunicate:
    llamadas = []

    def __init__(self, texto, voz, rate="+0%"):
        _FakeCommunicate.llamadas.append({"texto": texto, "voz": voz, "rate": rate})

    async def save(self, ruta):
        with open(ruta, "wb") as fh:
            fh.write(b"fake-mp3")


def test_procesar_guion_usa_voz_y_rate_por_locutor(monkeypatch, tmp_path):
    _FakeCommunicate.llamadas = []
    monkeypatch.setattr(locutor.edge_tts, "Communicate", _FakeCommunicate)
    monkeypatch.setattr(locutor.settings, "carpeta_temp", str(tmp_path))

    guion = "Álex: buenos días\nMaría: hola a todos\nlínea sin locutor"
    piezas = asyncio.run(locutor.procesar_guion_a_audio(guion))

    assert len(piezas) == 2  # la línea sin locutor se salta
    primera, segunda = _FakeCommunicate.llamadas
    assert primera == {
        "texto": "buenos días",
        "voz": "es-ES-AlvaroNeural",
        "rate": "-4%",
    }
    assert segunda == {
        "texto": "hola a todos",
        "voz": "es-ES-ElviraNeural",
        "rate": "+6%",
    }
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `uv run pytest tests/test_locutor.py::test_procesar_guion_usa_voz_y_rate_por_locutor -v`
Expected: FAIL — la implementación actual no pasa `rate` (el fake recibe `rate="+0%"`) y usa `settings.voz_santi`, que ya no existe (`AttributeError`).

- [ ] **Step 3: Implementar**

Añadir a `src/noticia/locutor.py`, debajo de `_parsear_linea`:

```python
def _voz_y_rate(locutor: str) -> tuple[str, str]:
    if locutor == "alex":
        return settings.voz_alex, settings.rate_alex
    return settings.voz_maria, settings.rate_maria
```

Y reemplazar TODO el cuerpo de `procesar_guion_a_audio` por:

```python
async def procesar_guion_a_audio(guion_texto):
    piezas_audio = []

    logger.info("Empezando la locución...")
    os.makedirs(settings.carpeta_temp, exist_ok=True)

    contador = 0
    for linea in guion_texto.split("\n"):
        parseada = _parsear_linea(linea.strip())
        if parseada is None:
            if linea.strip():
                logger.warning("Saltando línea sin locutor: %s...", linea.strip()[:30])
            continue

        locutor_id, texto = parseada
        voz, rate = _voz_y_rate(locutor_id)
        temp_file = os.path.join(settings.carpeta_temp, f"fragmento_{contador}.mp3")

        try:
            logger.info("Grabando a %s con voz %s (rate %s)...", locutor_id, voz, rate)
            communicate = edge_tts.Communicate(texto, voz, rate=rate)
            await communicate.save(temp_file)
            piezas_audio.append(temp_file)
            contador += 1
        except Exception as exc:
            logger.error("Error grabando la línea %s: %s", contador, exc)
            continue

    logger.info("Se han generado %s fragmentos.", len(piezas_audio))
    return piezas_audio
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `uv run pytest tests/test_locutor.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Lint, formato y suite completa**

Run: `uv run ruff check && uv run ruff format --check src/noticia tests && uv run pytest -q`
Expected: `All checks passed!` y todos los tests verdes.

- [ ] **Step 6: Commit**

```bash
git add src/noticia/locutor.py tests/test_locutor.py
git commit -m "feat: prosodia por personaje en la locución"
```

---

## Task 4: `editor.py` — pausas en vez de crossfade, y mastering sano

**Files:**
- Modify: `src/noticia/editor.py`
- Test: `tests/test_editor.py` (crear)

**Interfaces:**
- Consumes: `settings.pausa_entre_turnos_ms` (Task 1).
- Produces: `_unir_con_pausas(segmentos: list, pausa_ms: int) -> AudioSegment`;
  `aplicar_mastering(audio: AudioSegment) -> AudioSegment` (renombra `aplicar_mastering_pro`).

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_editor.py`:

```python
from pydub import AudioSegment
from pydub.generators import Sine

from noticia import editor


def _tono(ms):
    return Sine(440).to_audio_segment(duration=ms)


def test_unir_con_pausas_suma_silencio_entre_segmentos():
    segmentos = [_tono(100), _tono(100), _tono(100)]
    unido = editor._unir_con_pausas(segmentos, pausa_ms=350)
    # 3 tonos de 100 ms + 2 silencios de 350 ms
    assert abs(len(unido) - (300 + 700)) <= 2  # tolerancia de redondeo


def test_unir_con_pausas_un_solo_segmento_no_anade_silencio():
    unido = editor._unir_con_pausas([_tono(100)], pausa_ms=350)
    assert abs(len(unido) - 100) <= 2


def test_unir_con_pausas_lista_vacia():
    assert len(editor._unir_con_pausas([], pausa_ms=350)) == 0


def test_aplicar_mastering_deja_margen_y_no_satura():
    resultado = editor.aplicar_mastering(_tono(500))
    # normalize(headroom=1.0) deja el pico 1 dB por debajo de fondo de escala
    assert -1.5 <= resultado.max_dBFS <= -0.5


def test_aplicar_mastering_devuelve_audiosegment():
    assert isinstance(editor.aplicar_mastering(_tono(200)), AudioSegment)
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `uv run pytest tests/test_editor.py -v`
Expected: FAIL — `AttributeError: module 'noticia.editor' has no attribute '_unir_con_pausas'` (y `aplicar_mastering`).

- [ ] **Step 3: Reemplazar `aplicar_mastering_pro` por `aplicar_mastering` y añadir `_unir_con_pausas`**

En `src/noticia/editor.py`, reemplazar la función `aplicar_mastering_pro` completa por estas dos:

```python
def _unir_con_pausas(segmentos, pausa_ms):
    """Concatena segmentos separándolos por silencio. Sin crossfade.

    El crossfade solapaba el final de cada frase con el principio de la
    siguiente: en voz eso pisa sílabas.
    """
    if not segmentos:
        return AudioSegment.empty()
    silencio = AudioSegment.silent(duration=pausa_ms)
    resultado = segmentos[0]
    for segmento in segmentos[1:]:
        resultado = resultado + silencio + segmento
    return resultado


def aplicar_mastering(audio):
    """Cadena sobria: limpia graves, nivela, comprime suave y deja margen.

    La versión anterior sumaba una copia filtrada sobre el original
    (low_pass_filter().apply_gain().overlay()), lo que enturbiaba y saturaba,
    y normalizaba a 0.1 dB del máximo.
    """
    logger.info("Aplicando mastering...")
    audio = audio.high_pass_filter(80)  # fuera el retumbe: esto sí es una EQ
    audio = effects.normalize(audio)
    audio = effects.compress_dynamic_range(
        audio, threshold=-18.0, ratio=2.5, attack=5.0, release=50.0
    )
    return effects.normalize(audio, headroom=1.0)
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `uv run pytest tests/test_editor.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Usar `_unir_con_pausas` en el montaje y llamar al mastering renombrado**

En `ensamblar_podcast_dinamico`, reemplazar este bloque:

```python
        voces_bloque = AudioSegment.empty()
        for i, f in enumerate(archivos):
            try:
                segmento = AudioSegment.from_mp3(f)
                if i == 0:
                    voces_bloque = segmento
                else:
                    voces_bloque = voces_bloque.append(segmento, crossfade=ms_solapamiento)
            except Exception as exc:
                logger.warning("No se pudo cargar el fragmento %s: %s", f, exc)
                continue
```

por:

```python
        segmentos = []
        for f in archivos:
            try:
                segmentos.append(AudioSegment.from_mp3(f))
            except Exception as exc:
                logger.warning("No se pudo cargar el fragmento %s: %s", f, exc)
                continue
        voces_bloque = _unir_con_pausas(segmentos, settings.pausa_entre_turnos_ms)
        if len(voces_bloque) == 0:
            continue
```

Eliminar la línea `ms_solapamiento = 250` (ya no se usa) y cambiar la llamada
`podcast_final = aplicar_mastering_pro(podcast_completo)` por
`podcast_final = aplicar_mastering(podcast_completo)`.

- [ ] **Step 6: Verificar que no queda rastro del crossfade entre voces ni del nombre viejo**

Run: `grep -n "ms_solapamiento\|aplicar_mastering_pro" src/noticia/editor.py`
Expected: sin resultados.

- [ ] **Step 7: Lint, formato y suite completa**

Run: `uv run ruff check && uv run ruff format --check src/noticia tests && uv run pytest -q`
Expected: `All checks passed!` y todos los tests verdes.

- [ ] **Step 8: Commit**

```bash
git add src/noticia/editor.py tests/test_editor.py
git commit -m "fix: pausas entre turnos y cadena de mastering sana"
```

---

## Task 5: `cli.py` — modo `--solo-audio --guion RUTA`

**Files:**
- Modify: `src/noticia/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `procesar_guion_a_audio` (Task 3), `ensamblar_podcast_dinamico` (Task 4),
  `_ORDEN_BLOQUES` (ya existe en `cli.py:48`).
- Produces: `_trocear_guion(texto_md: str) -> dict[str, str]`;
  `generar_solo_audio(ruta_guion: str, salida: str | None = None) -> str` (corutina).

- [ ] **Step 1: Añadir los tests que fallan**

Primero, asegurarse de que `tests/test_cli.py` tiene `import asyncio` y `import pytest`
**al principio** del fichero (antes de `from noticia import cli`). Un import a media altura
dispara `E402` en ruff.

Luego añadir al final del fichero:

```python
def test_trocear_guion_separa_por_bloques():
    md = "## intro\n\nÁlex: hola\n\n## espana\n\nMaría: qué tal\nÁlex: bien\n"
    bloques = cli._trocear_guion(md)
    assert set(bloques) == {"intro", "espana"}
    assert bloques["intro"] == "Álex: hola"
    assert bloques["espana"] == "María: qué tal\nÁlex: bien"


def test_trocear_guion_texto_sin_bloques_devuelve_vacio():
    assert cli._trocear_guion("Álex: sin encabezados") == {}


def test_solo_audio_no_genera_guion(monkeypatch, tmp_path):
    llamadas = {"locucion": [], "ensamblado": []}

    def _no_llamar(*_a, **_k):  # el modo solo-audio NO debe tocar la generación
        raise AssertionError("construir_guion no debe invocarse en --solo-audio")

    monkeypatch.setattr(cli, "construir_guion", _no_llamar)
    monkeypatch.setattr(cli, "obtener_noticias", _no_llamar)

    async def fake_locucion(texto):
        llamadas["locucion"].append(texto)
        return ["frag.mp3"]

    monkeypatch.setattr(cli, "procesar_guion_a_audio", fake_locucion)
    monkeypatch.setattr(
        cli,
        "ensamblar_podcast_dinamico",
        lambda fragmentos, salida: llamadas["ensamblado"].append((fragmentos, salida)),
    )
    monkeypatch.setattr(cli.settings, "carpeta_temp", str(tmp_path))
    monkeypatch.setattr(cli.settings, "carpeta_output", str(tmp_path))

    guion = tmp_path / "g.md"
    guion.write_text("## intro\n\nÁlex: hola\n", encoding="utf-8")
    salida = tmp_path / "out.mp3"

    ruta = asyncio.run(cli.generar_solo_audio(str(guion), str(salida)))

    assert ruta == str(salida)
    assert llamadas["locucion"] == ["Álex: hola"]
    assert llamadas["ensamblado"] == [({"intro": ["frag.mp3"]}, str(salida))]


def test_solo_audio_guion_sin_bloques_falla(monkeypatch, tmp_path):
    guion = tmp_path / "g.md"
    guion.write_text("Álex: sin encabezados\n", encoding="utf-8")
    with pytest.raises(RuntimeError):
        asyncio.run(cli.generar_solo_audio(str(guion), str(tmp_path / "o.mp3")))
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL — `AttributeError: module 'noticia.cli' has no attribute '_trocear_guion'`.

- [ ] **Step 3: Implementar `_trocear_guion` y `generar_solo_audio`**

En `src/noticia/cli.py`, añadir `import re` a los imports, y estas dos funciones justo antes de `def main():`:

```python
_ENCABEZADO_BLOQUE = re.compile(r"^##\s+(\w+)\s*$")


def _trocear_guion(texto_md: str) -> dict[str, str]:
    """Inverso de _formatear_guion: '## bloque' + texto -> {bloque: texto}."""
    bloques: dict[str, str] = {}
    actual = None
    lineas: list[str] = []
    for linea in texto_md.splitlines():
        encabezado = _ENCABEZADO_BLOQUE.match(linea)
        if encabezado:
            if actual is not None:
                bloques[actual] = "\n".join(lineas).strip()
            actual = encabezado.group(1)
            lineas = []
        elif actual is not None:
            lineas.append(linea)
    if actual is not None:
        bloques[actual] = "\n".join(lineas).strip()
    return bloques


async def generar_solo_audio(ruta_guion: str, salida: str | None = None) -> str:
    """Locuta y masteriza un guion ya escrito, sin regenerarlo."""
    logger.info("Modo solo-audio: locución + montaje desde %s", ruta_guion)
    texto = Path(ruta_guion).read_text(encoding="utf-8")
    bloques = _trocear_guion(texto)
    if not bloques:
        raise RuntimeError(f"El guion {ruta_guion} no tiene bloques '## nombre'.")

    os.makedirs(settings.carpeta_temp, exist_ok=True)
    os.makedirs(settings.carpeta_output, exist_ok=True)

    fragmentos_por_bloque = {}
    for categoria in _ORDEN_BLOQUES:
        contenido = bloques.get(categoria)
        if not contenido:
            continue
        logger.info("Procesando locución del bloque: %s...", categoria)
        fragmentos_por_bloque[categoria] = await procesar_guion_a_audio(contenido)

    if salida is None:
        salida = os.path.join(settings.carpeta_output, "NoticIA_audio.mp3")

    ensamblar_podcast_dinamico(fragmentos_por_bloque, salida)
    logger.info("Audio escrito en %s", salida)
    return salida
```

- [ ] **Step 4: Añadir las opciones de `main()`**

En `main()`, añadir estos dos argumentos después del argumento `--salida` existente:

```python
    parser.add_argument(
        "--solo-audio",
        action="store_true",
        help="Locuta y masteriza un guion ya escrito (requiere --guion).",
    )
    parser.add_argument(
        "--guion",
        help="Ruta del guion .md de entrada (solo con --solo-audio).",
    )
```

Y reemplazar el enrutado final por:

```python
    if args.solo_audio:
        if not args.guion:
            parser.error("--solo-audio requiere --guion RUTA")
        asyncio.run(generar_solo_audio(args.guion, args.salida))
    elif args.solo_guion:
        generar_solo_guion(args.salida)
    else:
        asyncio.run(producir_episodio())
```

- [ ] **Step 5: Ejecutar y verificar que pasa**

Run: `uv run pytest tests/test_cli.py -v`
Expected: PASS.

- [ ] **Step 6: Comprobar el `--help`**

Run: `uv run noticia --help`
Expected: aparecen `--solo-guion`, `--salida`, `--solo-audio` y `--guion`.

- [ ] **Step 7: Lint, formato y suite completa**

Run: `uv run ruff check && uv run ruff format --check src/noticia tests && uv run pytest -q`
Expected: `All checks passed!` y todos los tests verdes.

- [ ] **Step 8: Commit**

```bash
git add src/noticia/cli.py tests/test_cli.py
git commit -m "feat: modo --solo-audio para iterar sobre el audio sin regenerar el guion"
```

---

## Task 6: `reglas/` — Santi pasa a ser María

**Files:**
- Modify: `reglas/instrucciones.md`
- Modify: `reglas/contexto.md`

**Interfaces:**
- Consumes: nada (contenido de prompts).
- Produces: las reglas que lee `get_prompt_sistema()` / `get_contexto()` nombran a **María**,
  mujer, con concordancia femenina.

> Sin tests automáticos: es contenido de prompt. La verificación es el `grep` del Step 3
> y, más adelante, regenerar un guion y leer la concordancia.

- [ ] **Step 1: Editar `reglas/instrucciones.md`**

Reemplazar la sección `# PERSONAJES:` completa por:

```markdown
# PERSONAJES:
- Álex: El veterano carismático y apasionado. Es un gran cinéfilo. Su realismo viene de su tono reflexivo y su capacidad para contar historias.
- María: La motora de energía. Experta en tecnología, Nintendo y Pokémon VGC. Es curiosa y siempre pregunta el "cómo nos afecta esto".
```

En la sección `# BLOQUE FRIKI (ESPECIALIZADO):`, cambiar
`Al final del bloque friki, Álex o Santi DEBEN recomendar` por
`Al final del bloque friki, Álex o María DEBEN recomendar`.

En `# ESTILO:`, cambiar `Formato: Diálogos "Álex:" y "Santi:".` por:

```markdown
- Formato: Diálogos "Álex:" y "María:".
- María es una mujer: concordancia femenina en sus frases ("estoy encantada", no "encantado").
- Se tratan de "tía"/"tío" según corresponda; nunca llaméis "tío" a María.
```

- [ ] **Step 2: Editar `reglas/contexto.md`**

Reemplazar la línea que empieza por `Santi (Dev Fullstack):` por:

```markdown
María (Dev Fullstack): Perfil técnico (Svelte, Django, K8s). Entusiasta del anime y experta en Pokémon VGC. Su rol es aterrizar las noticias al contexto español y aportar la visión "tech/friki".
```

Y en `Reglas de Estilo:`, cambiar
`Formato: Exclusivamente diálogo etiquetado como "Álex:" y "Santi:".` por
`Formato: Exclusivamente diálogo etiquetado como "Álex:" y "María:". María es mujer (concordancia femenina).`

En la última línea (`Estado actual del proyecto`), cambiar
`(interrupciones de Santi, pragmatismo de Álex)` por
`(interrupciones de María, pragmatismo de Álex)`.

- [ ] **Step 3: Verificar que no queda ningún "Santi" en las reglas**

Run: `grep -rn "Santi" reglas/`
Expected: sin resultados.

- [ ] **Step 4: Suite completa (nada debe romperse)**

Run: `uv run pytest -q`
Expected: todos los tests verdes.

- [ ] **Step 5: Commit**

```bash
git add reglas/instrucciones.md reglas/contexto.md
git commit -m "feat: Santi pasa a ser María, con voz y concordancia femeninas"
```

---

## Verificación final de la fase (manual, tras las 6 tareas)

Los guiones ya generados usan `Santi:`, que el parser nuevo ya no reconoce. Para escuchar
el resultado sin regenerar el guion (14 min + cuota de Max), renombrar el locutor:

- [ ] **Renombrar Santi → María en el guion de validación**

```bash
sed 's/^Santi:/María:/' output/guion_verificacion.md > output/guion_maria.md
grep -c '^María:' output/guion_maria.md   # debe ser > 0
```

- [ ] **Generar el audio y escucharlo**

```bash
uv run noticia --solo-audio --guion output/guion_maria.md --salida output/prueba_audio.mp3
```

Criterio de aceptación al escuchar: los turnos **no se pisan**, hay una pausa natural entre
intervenciones, y no se oye turbieza ni saturación.

> Ojo: el guion ronda las 8.900 palabras (~1 h de audio) y la locución es secuencial. Si
> el render tarda demasiado para iterar cómodamente, se adelanta el subproyecto **D**
> (locución en paralelo). Para una prueba rápida, recortar el guion a un par de bloques.

---

## Notas para el ejecutor

- **No** se tocan `ingesta.py`, `agrupador.py`, `fuentes.py`, `generador.py` ni `motor_claude.py`.
- **Sin dependencias nuevas.** `pyloudnorm` / LUFS están fuera de alcance a propósito.
- El crossfade **entre bloques** (`crossfade=1000`) y la mezcla con sintonías se dejan como están.
- Las "interrupciones leves" que piden las reglas son un solapamiento intencionado y puntual,
  no un crossfade uniforme: se abordan en una iteración posterior.
- `pydub` emite un `DeprecationWarning` de `audioop` en Py3.12: es deuda conocida, no la arregles aquí.
