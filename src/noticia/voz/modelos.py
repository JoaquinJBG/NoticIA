"""Descarga y verificación de los pesos del motor de voz Kokoro."""

import hashlib
import logging
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from noticia.config import settings

logger = logging.getLogger("noticia.voz.modelos")

_TAMANO_BLOQUE = 1024 * 1024


@dataclass(frozen=True)
class FicheroModelo:
    nombre: str
    url: str
    sha256: str


FICHEROS_KOKORO: tuple[FicheroModelo, ...] = (
    FicheroModelo(
        nombre="kokoro-v1.0.onnx",
        url="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
        sha256="7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5",
    ),
    FicheroModelo(
        nombre="voices-v1.0.bin",
        url="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
        sha256="bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
    ),
)


def rutas_kokoro(directorio: Path | None = None) -> tuple[Path, Path]:
    """Devuelve (onnx, voices) dentro de `directorio` (por defecto `settings.kokoro_dir`)."""
    base = directorio if directorio is not None else settings.kokoro_dir
    onnx, voices = FICHEROS_KOKORO
    return base / onnx.nombre, base / voices.nombre


def _sha256_de(ruta: Path) -> str:
    digest = hashlib.sha256()
    with ruta.open("rb") as fh:
        for bloque in iter(lambda: fh.read(_TAMANO_BLOQUE), b""):
            digest.update(bloque)
    return digest.hexdigest()


def modelos_kokoro_presentes(directorio: Path | None = None) -> bool:
    """True si los dos pesos de Kokoro existen en `directorio` con su hash correcto."""
    base = directorio if directorio is not None else settings.kokoro_dir
    for fichero in FICHEROS_KOKORO:
        ruta = base / fichero.nombre
        if not ruta.exists():
            return False
        if _sha256_de(ruta) != fichero.sha256:
            return False
    return True


def descargar_fichero(fichero: FicheroModelo, destino: Path) -> Path:
    """Descarga `fichero` a `destino`, verificando su sha256.

    Descarga en streaming a `destino.with_suffix(".part")` y solo al terminar
    y comprobar el hash lo mueve a `destino`. Si el hash no coincide, o si la
    descarga falla, no deja ningún fichero a medias.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    parcial = destino.with_suffix(".part")
    digest = hashlib.sha256()
    try:
        with urllib.request.urlopen(fichero.url) as respuesta, parcial.open("wb") as salida:
            for bloque in iter(lambda: respuesta.read(_TAMANO_BLOQUE), b""):
                digest.update(bloque)
                salida.write(bloque)
    except Exception:
        parcial.unlink(missing_ok=True)
        raise

    if digest.hexdigest() != fichero.sha256:
        parcial.unlink(missing_ok=True)
        raise ValueError(
            f"el hash de {fichero.nombre} no coincide: esperado {fichero.sha256}, "
            f"obtenido {digest.hexdigest()}"
        )

    os.replace(parcial, destino)
    logger.info("Descargado %s en %s", fichero.nombre, destino)
    return destino


def asegurar_modelos_kokoro(directorio: Path | None = None) -> list[Path]:
    """Descarga los pesos de Kokoro que falten o tengan un hash incorrecto."""
    base = directorio if directorio is not None else settings.kokoro_dir
    rutas: list[Path] = []
    for fichero in FICHEROS_KOKORO:
        destino = base / fichero.nombre
        if destino.exists() and _sha256_de(destino) == fichero.sha256:
            logger.info("%s ya está descargado", fichero.nombre)
        else:
            descargar_fichero(fichero, destino)
        rutas.append(destino)
    return rutas


def main() -> int:
    """Punto de entrada de `python -m noticia.voz.modelos`."""
    try:
        asegurar_modelos_kokoro()
    except Exception as exc:
        logger.error("No se pudieron descargar los modelos de Kokoro: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
