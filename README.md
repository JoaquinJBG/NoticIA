# 🎙️ NoticIA: El Podcast Autónomo Inteligente

**NoticIA** es un sistema automatizado que transforma la actualidad diaria en una tertulia de podcast profesional. Utiliza IA para la ingesta de noticias, generación de guiones dinámicos con personalidad propia y locución con voces realistas, culminando en un proceso de edición y mastering de audio automático.

## 🚀 Características

- **Ingesta Multi-fuente:** Captura noticias de RSS feeds organizados por categorías (España, Geopolítica, Ciencia, Tecnología, Friki, Fútbol).
- **Cerebro Claude:** Genera diálogos naturales entre dos locutores, **Álex** (el mentor experto) y **María** (la entusiasta tecnológica), vía el CLI headless `claude -p`.
- **Voces Realistas:** Integración con `edge-tts` para una locución fluida con acento de España.
- **Edición Pro:** Montaje automático con sintonías de fondo, transiciones dinámicas y una cadena de mastering (compresión, EQ y normalización) usando `pydub`.

---

## 🛠️ Requisitos Previos

1.  **[uv](https://docs.astral.sh/uv/)** — instala Python y las dependencias:
    `curl -LsSf https://astral.sh/uv/install.sh | sh`
2.  **Python 3.12 o superior** (uv lo instala solo si no lo tienes).
3.  **FFmpeg** — `pydub` lo necesita para leer y escribir MP3.
    - **Linux / WSL:** `sudo apt install ffmpeg`
    - **macOS:** `brew install ffmpeg`
    - **Windows:** descargar de [ffmpeg.org](https://ffmpeg.org/download.html) y añadir al `PATH`.
4.  **[Claude Code](https://claude.ai/download) con una sesión de Claude Max iniciada** — es el cerebro
    que escribe el guion, vía el CLI headless `claude -p`.

> **No hacen falta API keys.** El guion usa tu suscripción de Claude Max, no una API de pago.
> La sesión vive en `~/.claude` (tu carpeta de usuario), **no en el repositorio**: al clonar el
> proyecto en otra máquina tendrás que ejecutar `claude` una vez e iniciar sesión allí.

---

## 📦 Puesta en marcha

```bash
git clone https://github.com/JoaquinJBG/NoticIA.git
cd NoticIA
make preparar
```

`make preparar` instala las dependencias y comprueba que ffmpeg, el CLI de Claude y la GPU (si la hay)
están donde deben. Si falta algo bloqueante, te lo dice y sale con error.

---

## 🎮 Uso

```bash
make ayuda      # ver todos los atajos
```

| Comando | Qué hace |
|---|---|
| `make guion` | Genera **solo el guion** con Claude, sin audio → `output/guion_<fecha>.md` |
| `make audio` | Locuta y masteriza un guion **ya escrito**, sin regenerarlo |
| `make episodio` | Pipeline completo: ingesta → guion → locución → mastering |
| `make test` | Ejecuta la suite de tests |
| `make lint` | `ruff check` + comprobación de formato |
| `make limpiar` | Borra los fragmentos temporales de audio |

`make audio` toma por defecto el guion más reciente de `output/`. Para elegir otro:

```bash
make audio GUION=output/guion_2026-07-10.md SALIDA=output/prueba.mp3
```

Iterar sobre el audio con `make audio` cuesta segundos; regenerar el guion cuesta ~14 minutos y consume
cuota de Claude Max. Por eso están separados.

El resultado final se guarda en `output/`.

---

## 📂 Estructura del Proyecto

- `src/noticia/cli.py`: Punto de entrada principal (comando `uv run noticia`).
- `src/noticia/`: Lógica del sistema (config, ingesta, generador, locutor, editor).
- `reglas/`: Prompts de sistema y contexto que definen la personalidad de los locutores.
- `sintonias/`: Archivos MP3 con la música de fondo para cada bloque.
- `output/`: Carpeta donde se generan los podcasts finales.
- `temp/`: Carpeta temporal para fragmentos de audio (se limpia automáticamente).
- `tests/`: Pruebas automatizadas con pytest.

---

## 🎙️ Personajes

- **Álex:** El veterano carismático. Aporta el contexto histórico y la reflexión profunda. Fanático del cine de culto.
- **María:** El motor de energía. Experta en gadgets, Nintendo y Pokémon VGC. Siempre busca cómo la tecnología afecta al día a día.

---

## ⚖️ Licencia

Este proyecto está bajo la licencia **Creative Commons Atribución-NoComercial-CompartirIgual 4.0 Internacional (CC BY-NC-SA 4.0)**.

**Esto significa que:**
- ✅ **Puedes:** Copiar, modificar y compartir el código.
- ❌ **No puedes:** Usar este material para fines comerciales o venderlo.
- 🔄 **Compartir Igual:** Si alteras o transformas este código, debes distribuir tu contribución bajo la misma licencia que el original.
- 👤 **Atribución:** Debes dar crédito de manera adecuada al autor original.
