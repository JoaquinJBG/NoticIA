"""Valida las grabaciones de voz propia en una carpeta (solo local, no sube nada).

Uso: uv run python scripts/preparar_voz_propia.py voces/propia
Comprueba formato, duración, nivel, recorte (clipping) y ruido de fondo, y
sugiere el mejor clip de 10-30 s como referencia.
"""

import logging
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

log = logging.getLogger("noticia.voz_propia")


def analizar(ruta: Path) -> dict:
    datos, sr = sf.read(ruta, dtype="float32", always_2d=True)
    mono = datos.mean(axis=1)
    dur = len(mono) / sr
    pico = float(np.abs(mono).max()) if len(mono) else 0.0
    ventana = max(int(sr * 0.05), 1)
    n = len(mono) // ventana
    rms = np.sqrt((mono[: n * ventana].reshape(n, ventana) ** 2).mean(axis=1)) if n else np.zeros(1)
    voz = float(np.percentile(rms, 90))
    ruido = float(np.percentile(rms, 10))
    snr = 20 * np.log10((voz + 1e-9) / (ruido + 1e-9))
    avisos = []
    if datos.shape[1] > 1:
        avisos.append("no es mono")
    if sr < 24000:
        avisos.append(f"frecuencia baja ({sr} Hz)")
    if pico >= 0.99:
        avisos.append("saturado (clipping)")
    if pico < 0.1:
        avisos.append("nivel muy bajo")
    if snr < 25:
        avisos.append(f"mucho ruido de fondo (SNR~{snr:.0f} dB)")
    if dur < 8:
        avisos.append("muy corto")
    return {"ruta": ruta, "sr": sr, "dur": dur, "pico": pico, "snr": snr, "avisos": avisos}


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    carpeta = Path(sys.argv[1] if len(sys.argv) > 1 else "voces/propia")
    clips = sorted(carpeta.glob("*.wav"))
    if not clips:
        log.error("No hay WAV en %s", carpeta)
        return 1
    informes = []
    for clip in clips:
        try:
            informes.append(analizar(clip))
        except Exception as exc:
            log.error("%s: no se pudo leer (%s)", clip.name, exc)
    for i in informes:
        estado = "OK" if not i["avisos"] else "; ".join(i["avisos"])
        log.info("%-20s %5.1f s  %6d Hz  pico %.2f  SNR %4.0f dB  -> %s", i["ruta"].name, i["dur"], i["sr"], i["pico"], i["snr"], estado)
    buenos = [i for i in informes if not i["avisos"] and 10 <= i["dur"] <= 30]
    if buenos:
        mejor = max(buenos, key=lambda i: i["snr"])
        log.info("Referencia sugerida: %s", mejor["ruta"].name)
    else:
        log.info("Ningún clip de 10-30 s sin avisos: revisa los avisos y regraba.")
    log.info("Total grabado: %.1f min", sum(i["dur"] for i in informes) / 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
