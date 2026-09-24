from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# src/noticia/config.py -> parents[2] es la raíz del proyecto
ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    modelo_claude: str = "sonnet"

    # edge-tts solo tiene una voz masculina de España (Alvaro), así que María
    # es mujer. Ximena, la voz del locutor anterior, tiene acento colombiano.
    voz_alex: str = "es-ES-AlvaroNeural"
    voz_maria: str = "es-ES-ElviraNeural"

    # Prosodia: Álex es el mentor reflexivo, María el motor de energía.
    # No se toca el pitch: en voces neuronales suena artificial.
    rate_alex: str = "-4%"
    rate_maria: str = "+6%"

    # Silencio entre turnos. El crossfade solapaba sílabas.
    pausa_entre_turnos_ms: int = 350

    carpeta_output: str = "output"
    carpeta_temp: str = "temp"

    # Selección de motor de voz y control de la locución en paralelo.
    motor_voz: Literal["auto", "edge", "kokoro", "chatterbox"] = "auto"
    concurrencia_locucion: int = 6
    reintentos_locucion: int = 2
    max_fraccion_fallos_locucion: float = 0.10

    # Kokoro (motor CPU).
    kokoro_dir: Path = ROOT / "modelos" / "kokoro"
    kokoro_voz_alex: str = "em_alex"
    kokoro_voz_maria: str = "ef_dora"
    kokoro_velocidad_alex: float = 0.96
    kokoro_velocidad_maria: float = 1.05
    kokoro_concurrencia: int = 2

    # Chatterbox Multilingual es-ES (motor GPU).
    chatterbox_ref_alex: Path = ROOT / "voces" / "alex_ref.wav"
    chatterbox_ref_maria: Path = ROOT / "voces" / "maria_ref.wav"
    chatterbox_exageracion_alex: float = 0.5
    chatterbox_exageracion_maria: float = 0.65
    chatterbox_cfg: float = 0.4
    chatterbox_temperatura: float = 0.8

    # Mastering: ffmpeg loudnorm en 2 pasadas.
    objetivo_lufs: float = -16.0
    true_peak_dbtp: float = -1.5  # margen para que el MP3 quede <= -1.0
    bitrate_mp3: str = "192k"

    # Guion.
    noticias_por_bloque: int = 8
    reintentos_guion: int = 1
    espera_reintento_guion_s: float = 30.0

    # Publicación.
    publicacion_url_base: str = "http://localhost:8000"
    carpeta_publicacion: Path = ROOT / "output" / "publicacion"
    podcast_titulo: str = "NoticIA"
    podcast_descripcion: str = (
        "La actualidad del día convertida en una tertulia entre Álex y María. "
        "Guion y voces generados con IA."
    )
    podcast_autor: str = "NoticIA"
    podcast_email: str = ""  # vacío => se omiten itunes:owner y podcast:locked
    podcast_idioma: str = "es-ES"
    podcast_explicito: bool = False
    max_items_feed: int = 300

    @property
    def carpeta_episodios(self) -> Path:
        return ROOT / "output" / "episodios"

    @property
    def ruta_sintonia(self) -> str:
        return str(ROOT / "sintonias" / "sintonia1.mp3")

    @property
    def sintonias(self) -> dict[str, str]:
        base = ROOT / "sintonias"
        return {
            "espana": str(base / "serio.mp3"),
            "geopolitica": str(base / "serio.mp3"),
            "ia_y_actualidad": str(base / "animado.mp3"),
            "ciencia": str(base / "neutro.mp3"),
            "friki": str(base / "animado.mp3"),
            "futbol": str(base / "neutro.mp3"),
            "intro": str(base / "sintonia1.mp3"),
            "outro": str(base / "sintonia1.mp3"),
        }


settings = Settings()


def _leer_regla(nombre: str, fallback: str = "") -> str:
    ruta = ROOT / "reglas" / nombre
    if ruta.exists():
        return ruta.read_text(encoding="utf-8")
    return fallback


def get_prompt_sistema() -> str:
    return _leer_regla("instrucciones.md", "Eres el equipo de producción de NoticIA.")


def get_contexto() -> str:
    return _leer_regla("contexto.md", "")
