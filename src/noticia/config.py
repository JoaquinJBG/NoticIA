from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# src/noticia/config.py -> parents[2] es la raíz del proyecto
ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    modelo_claude: str = "sonnet"

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

    carpeta_output: str = "output"
    carpeta_temp: str = "temp"

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
