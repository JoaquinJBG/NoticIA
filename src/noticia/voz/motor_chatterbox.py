"""Motor de voz Chatterbox Multilingual V3 es-ES (GPU)."""

import asyncio
import copy
import importlib
import importlib.util
import inspect
import logging
import sys
import types
from collections.abc import Callable
from pathlib import Path
from typing import Any

from noticia.config import settings
from noticia.personajes import locutores_requeridos
from noticia.voz.base import ErrorMotorVoz, Locutor, MotorNoDisponible, ajuste
from noticia.voz.texto import trocear_frases

logger = logging.getLogger("noticia.voz.motor_chatterbox")

_SILENCIO_ENTRE_TROZOS_S = 0.12
_RECORTE_FINAL_S = 0.04
_CLAVES_FALTANTES_ESPERADAS = {"tokenizer._mel_filters", "tokenizer.window"}


def _exageracion(locutor: Locutor) -> float:
    return ajuste("chatterbox_exageracion", locutor)


def _referencia(locutor: Locutor) -> Path:
    return ajuste("chatterbox_ref", locutor)


_CONDICION_CORTE = "if long_tail or alignment_repetition or token_repetition:"
_CONDICION_SIN_REPETICION = "if long_tail or alignment_repetition:"
_MARCA_PARCHE = "_noticia_sin_token_repetition"


def construir_analizador_sin_token_repetition(modulo_analizador: types.ModuleType) -> type:
    """Devuelve el AlignmentStreamAnalyzer sin el corte por `token_repetition`.

    chatterbox-tts 0.1.7 fuerza EOS cuando salen 2 tokens de voz iguales seguidos (el
    comentario dice 3 pero comprueba 2), lo que trunca audios válidos. Se conservan
    `long_tail` y `alignment_repetition`. El código se recompila dentro del namespace
    del módulo original para que resuelva sus propios imports.
    """
    fuente = inspect.getsource(modulo_analizador.AlignmentStreamAnalyzer)
    if _CONDICION_CORTE not in fuente:
        raise RuntimeError(
            "el AlignmentStreamAnalyzer de chatterbox no tiene la condición esperada"
        )
    fuente = fuente.replace(_CONDICION_CORTE, _CONDICION_SIN_REPETICION)
    espacio = dict(vars(modulo_analizador))
    exec(compile(fuente, f"<{modulo_analizador.__name__} parcheado>", "exec"), espacio)  # noqa: S102
    clase = espacio["AlignmentStreamAnalyzer"]
    setattr(clase, _MARCA_PARCHE, True)
    return clase


def parchear_analizador_chatterbox() -> bool:
    """Sustituye el analizador en `chatterbox.models.t3.t3`. Idempotente.

    Devuelve True si el parche queda aplicado. Si falla (otra versión de chatterbox),
    se registra y se sigue con el analizador original.
    """
    try:
        modulo_t3 = importlib.import_module("chatterbox.models.t3.t3")
        if getattr(modulo_t3.AlignmentStreamAnalyzer, _MARCA_PARCHE, False):
            return True
        modulo_analizador = sys.modules.get(
            modulo_t3.AlignmentStreamAnalyzer.__module__
        ) or importlib.import_module(modulo_t3.AlignmentStreamAnalyzer.__module__)
        modulo_t3.AlignmentStreamAnalyzer = construir_analizador_sin_token_repetition(
            modulo_analizador
        )
    except Exception as exc:
        logger.warning("No se pudo parchear el analizador de Chatterbox: %s", exc)
        return False
    logger.info("AlignmentStreamAnalyzer de Chatterbox parcheado (sin corte por token_repetition)")
    return True


def cargar_es_es(device: str = "cuda") -> Any:
    """Carga el Language Pack es-ES de Chatterbox Multilingual con el paquete PyPI."""
    import torch
    from chatterbox.models.s3gen import S3Gen
    from chatterbox.models.t3 import T3
    from chatterbox.models.t3.modules.t3_config import T3Config
    from chatterbox.models.tokenizers import MTLTokenizer
    from chatterbox.models.voice_encoder import VoiceEncoder
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS, Conditionals
    from huggingface_hub import hf_hub_download, snapshot_download
    from safetensors.torch import load_file

    parchear_analizador_chatterbox()

    base = Path(
        snapshot_download(
            "ResembleAI/chatterbox",
            allow_patterns=["ve.pt", "conds.pt", "grapheme_mtl_merged_expanded_v1.json"],
        )
    )
    t3_path = hf_hub_download("ResembleAI/Chatterbox-Multilingual-es-es", "t3_es_es.safetensors")
    s3_path = hf_hub_download("ResembleAI/Chatterbox-Multilingual-es-es", "s3gen_v3.pt")

    mapa_cpu = torch.device("cpu")

    codificador_voz = VoiceEncoder()
    pesos_ve = torch.load(base / "ve.pt", map_location=mapa_cpu, weights_only=True)
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

    tokenizador = MTLTokenizer(str(base / "grapheme_mtl_merged_expanded_v1.json"))
    conds = Conditionals.load(base / "conds.pt", map_location=mapa_cpu).to(device)

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
        for locutor in locutores_requeridos():
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
                for locutor in locutores_requeridos():
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
