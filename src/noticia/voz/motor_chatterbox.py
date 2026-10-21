"""Motor de voz Chatterbox Multilingual V3 es-ES (GPU)."""

import asyncio
import copy
import hashlib
import importlib.util
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from noticia.config import settings
from noticia.voz.base import ErrorMotorVoz, Locutor, MotorNoDisponible
from noticia.voz.texto import trocear_frases

logger = logging.getLogger("noticia.voz.motor_chatterbox")

_SILENCIO_ENTRE_TROZOS_S = 0.12
_RECORTE_FINAL_S = 0.04
_CLAVES_FALTANTES_ESPERADAS = {"tokenizer._mel_filters", "tokenizer.window"}

_REPO_BASE = "ResembleAI/chatterbox"
_REPO_ES = "ResembleAI/Chatterbox-Multilingual-es-es"
_REVISION_BASE = "5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18"
_REVISION_ES = "7262b364e3222ba9446c9289e7485eadc47ed902"

# Fichero -> (repo, revisión, sha256). Los sha256 de los ficheros LFS vienen de la API
# de Hugging Face; ve.pt, conds.pt y el de grafemas se han descargado y medido.
_FICHEROS_CHATTERBOX: dict[str, tuple[str, str, str]] = {
    "ve.pt": (
        _REPO_BASE,
        _REVISION_BASE,
        "4b16d836bc598509860f6fa068165a8bb5e9ac84f05582dfcf278a5a372879f1",
    ),
    "conds.pt": (
        _REPO_BASE,
        _REVISION_BASE,
        "6552d70568833628ba019c6b03459e77fe71ca197d5c560cef9411bee9d87f4e",
    ),
    "grapheme_mtl_merged_expanded_v1.json": (
        _REPO_BASE,
        _REVISION_BASE,
        "69632f47220a788a52ce2661d096453c5655e9bf25289d89a8d832c46ee07dbf",
    ),
    "t3_es_es.safetensors": (
        _REPO_ES,
        _REVISION_ES,
        "d85844b13ea8cb45e95b8d84a55bcfeccb2d743035cf304ee3d778fc6be39546",
    ),
    "s3gen_v3.pt": (
        _REPO_ES,
        _REVISION_ES,
        "f7abce4b196dae2d08d9296cbebc6521b046079577643b42a19a03499d08721e",
    ),
}


def _exageracion(locutor: Locutor) -> float:
    if locutor == "alex":
        return settings.chatterbox_exageracion_alex
    return settings.chatterbox_exageracion_maria


def _referencia(locutor: Locutor) -> Path:
    if locutor == "alex":
        return settings.chatterbox_ref_alex
    return settings.chatterbox_ref_maria


def _verificar_sha256(ruta: Path, esperado: str) -> Path:
    with ruta.open("rb") as fh:
        obtenido = hashlib.file_digest(fh, "sha256").hexdigest()
    if obtenido != esperado:
        raise ValueError(
            f"el sha256 de {ruta.name} no coincide: esperado {esperado}, obtenido {obtenido}"
        )
    return ruta


def cargar_es_es(device: str = "cuda") -> Any:
    """Carga el Language Pack es-ES de Chatterbox Multilingual con el paquete PyPI."""
    import torch
    from chatterbox.models.s3gen import S3Gen
    from chatterbox.models.t3 import T3
    from chatterbox.models.t3.modules.t3_config import T3Config
    from chatterbox.models.tokenizers import MTLTokenizer
    from chatterbox.models.voice_encoder import VoiceEncoder
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS, Conditionals
    from huggingface_hub import hf_hub_download
    from safetensors.torch import load_file

    def _fichero(nombre: str) -> Path:
        repo, revision, sha256 = _FICHEROS_CHATTERBOX[nombre]
        ruta = Path(hf_hub_download(repo, nombre, revision=revision))
        return _verificar_sha256(ruta, sha256)

    t3_path = _fichero("t3_es_es.safetensors")
    s3_path = _fichero("s3gen_v3.pt")

    mapa_cpu = torch.device("cpu")

    codificador_voz = VoiceEncoder()
    pesos_ve = torch.load(_fichero("ve.pt"), map_location=mapa_cpu, weights_only=True)
    codificador_voz.load_state_dict(pesos_ve)
    codificador_voz.to(device).eval()

    t3 = T3(T3Config.multilingual())
    estado_t3 = load_file(t3_path)
    if "model" in estado_t3:
        estado_t3 = estado_t3["model"][0]
    t3.load_state_dict(estado_t3)
    t3.to(device).eval()

    s3gen = S3Gen()
    resultado_carga = s3gen.load_state_dict(
        torch.load(s3_path, map_location=mapa_cpu, weights_only=True), strict=False
    )
    claves_inesperadas = set(resultado_carga.missing_keys) - _CLAVES_FALTANTES_ESPERADAS
    if claves_inesperadas:
        logger.warning("s3gen cargó con claves inesperadas ausentes: %s", claves_inesperadas)
    s3gen.to(device).eval()

    tokenizador = MTLTokenizer(str(_fichero("grapheme_mtl_merged_expanded_v1.json")))
    # Conditionals.load usa torch.load(weights_only=True) en chatterbox 0.1.7 (mtl_tts.py).
    conds = Conditionals.load(_fichero("conds.pt"), map_location=mapa_cpu).to(device)

    return ChatterboxMultilingualTTS(t3, s3gen, codificador_voz, tokenizador, device, conds=conds)


class MotorChatterbox:
    nombre = "chatterbox"
    extension = "wav"
    concurrencia_maxima = 1

    def __init__(self, cargador: Callable[[str], Any] | None = None) -> None:
        self._cargador = cargador or cargar_es_es
        self._modelo: Any = None
        self._conds: dict[Locutor, Any] = {}
        self._lock = asyncio.Lock()

    def disponible(self) -> tuple[bool, str]:
        if importlib.util.find_spec("chatterbox") is None:
            return False, "el paquete chatterbox no está instalado"
        if importlib.util.find_spec("torch") is None:
            return False, "el paquete torch no está instalado"
        for locutor in ("alex", "maria"):
            ref = _referencia(locutor)
            if not ref.exists():
                return False, f"falta el WAV de referencia {ref}"
        return True, ""

    async def cargar(self) -> None:
        async with self._lock:
            if self._modelo is not None:
                return
            try:
                self._modelo = await asyncio.to_thread(self._cargador, "cuda")
                for locutor in ("alex", "maria"):
                    ref = _referencia(locutor)
                    exageracion = _exageracion(locutor)
                    await asyncio.to_thread(
                        self._modelo.prepare_conditionals, str(ref), exaggeration=exageracion
                    )
                    self._conds[locutor] = copy.copy(self._modelo.conds)
            except Exception as exc:
                self._modelo = None
                self._conds = {}
                logger.error("No se pudo cargar Chatterbox: %s", exc)
                raise MotorNoDisponible(f"no se pudo cargar Chatterbox: {exc}") from exc

    async def sintetizar(self, texto: str, locutor: Locutor, ruta: Path) -> Path:
        if self._modelo is None:
            await self.cargar()

        async with self._lock:
            audio = await asyncio.to_thread(self._sintetizar_bloqueante, texto, locutor)

        if audio.size == 0:
            raise ErrorMotorVoz(f"Chatterbox generó un audio vacío para {locutor!r}")

        import soundfile as sf

        sf.write(str(ruta), audio, self._modelo.sr, subtype="PCM_16")
        return ruta

    def _sintetizar_bloqueante(self, texto: str, locutor: Locutor):
        import numpy as np

        self._modelo.conds = self._conds[locutor]
        exageracion = _exageracion(locutor)
        trozos = trocear_frases(texto, 280)
        recorte = int(self._modelo.sr * _RECORTE_FINAL_S)
        silencio = np.zeros(int(self._modelo.sr * _SILENCIO_ENTRE_TROZOS_S), dtype=np.float32)

        partes: list[Any] = []
        try:
            for trozo in trozos:
                salida = self._modelo.generate(
                    trozo,
                    language_id="es",
                    exaggeration=exageracion,
                    cfg_weight=settings.chatterbox_cfg,
                    temperature=settings.chatterbox_temperatura,
                    repetition_penalty=1.2,
                    top_p=0.95,
                    min_p=0.05,
                )
                trozo_audio = salida.squeeze(0).cpu().numpy()
                if recorte > 0 and len(trozo_audio) > recorte:
                    trozo_audio = trozo_audio[:-recorte]
                if partes:
                    partes.append(silencio)
                partes.append(trozo_audio)
        except Exception as exc:
            logger.error("Chatterbox falló al sintetizar para %s: %s", locutor, exc)
            raise ErrorMotorVoz(f"Chatterbox falló al sintetizar: {exc}") from exc

        if not partes:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(partes)

    async def cerrar(self) -> None:
        self._modelo = None
        self._conds = {}
