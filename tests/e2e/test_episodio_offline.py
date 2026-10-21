"""Episodio completo sin red, sin Claude Max y sin voz real.

fixture RSS -> `claude -p` simulado -> voz sintética -> MP3 masterizado + feed.xml.
Corre con el resto de la suite; `-m e2e` lo selecciona solo.
"""

import asyncio
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime, timedelta
from email.utils import format_datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from pydub.generators import Sine

from noticia import fuentes, generador, masterizado, orquestador
from noticia.bloques import CATEGORIAS_NOTICIAS, ORDEN_BLOQUES
from noticia.config import ROOT, Settings

from .claude_falso import registrar_llamada, responder

pytestmark = pytest.mark.e2e

FECHA = date(2026, 10, 21)
PLANTILLA = Path(__file__).parent / "fixtures" / "feed_plantilla.xml"
SCRIPT_FALSO = Path(__file__).parent / "claude_falso.py"
_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


class _MotorSintetico:
    nombre = "sintetico"
    extension = "wav"
    concurrencia_maxima = 4

    def disponible(self):
        return True, ""

    async def cargar(self):
        return None

    async def sintetizar(self, texto, locutor, ruta):
        tono = 220 if locutor == "alex" else 330
        Sine(tono).to_audio_segment(duration=300).export(ruta, format="wav")
        return ruta

    async def cerrar(self):
        return None


def _exigir_ffmpeg() -> None:
    faltan = [b for b in ("ffmpeg", "ffprobe") if shutil.which(b) is None]
    if not faltan:
        return
    motivo = f"{', '.join(faltan)} no está en PATH (el masterizado lo necesita)"
    if os.environ.get("NOTICIA_E2E_OBLIGATORIO") == "1":
        pytest.fail(motivo)
    pytest.skip(motivo)


@pytest.fixture
def sin_red(monkeypatch):
    # Se deja pasar el loopback: en Windows el bucle de asyncio usa un socketpair por TCP local.
    connect_original = socket.socket.connect

    def _connect(self, direccion):
        if isinstance(direccion, tuple) and direccion[0] not in _LOOPBACK:
            raise RuntimeError("red prohibida en e2e")
        return connect_original(self, direccion)

    def _create_connection(direccion, *args, **kwargs):
        raise RuntimeError("red prohibida en e2e")

    monkeypatch.setattr(socket.socket, "connect", _connect)
    monkeypatch.setattr(socket, "create_connection", _create_connection)


def _escribir_feeds(tmp_path: Path, monkeypatch) -> None:
    plantilla = PLANTILLA.read_text(encoding="utf-8")
    pubdate = format_datetime(datetime.now(UTC) - timedelta(hours=1))
    carpeta = tmp_path / "feeds"
    carpeta.mkdir()
    feeds = {}
    for categoria in CATEGORIAS_NOTICIAS:
        ruta = carpeta / f"{categoria}.xml"
        ruta.write_text(
            plantilla.replace("{{CATEGORIA}}", categoria).replace("{{PUBDATE}}", pubdate),
            encoding="utf-8",
        )
        feeds[categoria] = [str(ruta)]
    monkeypatch.setattr(fuentes, "FEEDS_CURADOS", feeds)
    monkeypatch.setattr(fuentes, "SECCIONES_GOOGLE_NEWS", {})


def _aislar_io(tmp_path: Path, monkeypatch) -> Path:
    carpeta_output = tmp_path / "output"
    carpeta_publicacion = carpeta_output / "publicacion"
    carpeta_episodios = carpeta_output / "episodios"
    monkeypatch.setattr(orquestador.settings, "carpeta_output", str(carpeta_output))
    monkeypatch.setattr(orquestador.settings, "carpeta_temp", str(tmp_path / "temp"))
    monkeypatch.setattr(orquestador.settings, "carpeta_publicacion", carpeta_publicacion)
    monkeypatch.setattr(Settings, "carpeta_episodios", property(lambda self: carpeta_episodios))
    monkeypatch.setattr(orquestador.settings, "espera_reintento_guion_s", 0)

    sintonia = tmp_path / "sintonia.wav"
    Sine(440).to_audio_segment(duration=3000).export(sintonia, format="wav")
    mapa = {bloque: str(sintonia) for bloque in ORDEN_BLOQUES}
    monkeypatch.setattr(Settings, "sintonias", property(lambda self: mapa))
    monkeypatch.setattr(Settings, "ruta_sintonia", property(lambda self: str(sintonia)))
    return carpeta_publicacion


def _instalar_claude_falso(modo: str, tmp_path: Path, monkeypatch) -> Path:
    log = tmp_path / "claude_falso.jsonl"
    monkeypatch.setenv("NOTICIA_CLAUDE_FALSO_LOG", str(log))
    if modo == "shim":
        binarios = tmp_path / "bin"
        binarios.mkdir()
        shim = binarios / "claude"
        shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{SCRIPT_FALSO}" "$@"\n')
        shim.chmod(shim.stat().st_mode | stat.S_IXUSR)
        monkeypatch.setenv("PATH", f"{binarios}{os.pathsep}{os.environ['PATH']}")
    else:

        def _llamar_ia(system_prompt, user_prompt):
            registrar_llamada(None, None, user_prompt)
            return responder(user_prompt)

        monkeypatch.setattr(generador, "llamar_ia", _llamar_ia)
    return log


def _ffmpeg_en_utf8(monkeypatch) -> None:
    # masterizado lee el stderr de ffmpeg con la codepage local; en Windows el "Á" del ID3 la rompe.
    def _run(*args, **kwargs):
        return subprocess.run(*args, **{"encoding": "utf-8", **kwargs})

    monkeypatch.setattr(masterizado, "subprocess", SimpleNamespace(run=_run))


def _listar(ruta: Path) -> list[str]:
    return sorted(str(p) for p in ruta.rglob("*")) if ruta.exists() else []


@pytest.mark.parametrize("modo", ["shim", "inproc"])
def test_episodio_offline(modo, tmp_path, monkeypatch, sin_red):
    if modo == "shim" and sys.platform == "win32":
        pytest.skip("modo shim solo en POSIX: subprocess no resuelve un script `claude` sin .exe")
    _exigir_ffmpeg()
    if sys.platform == "win32":
        _ffmpeg_en_utf8(monkeypatch)

    antes = {d: _listar(ROOT / d) for d in ("output", "temp")}
    _escribir_feeds(tmp_path, monkeypatch)
    carpeta_publicacion = _aislar_io(tmp_path, monkeypatch)
    log = _instalar_claude_falso(modo, tmp_path, monkeypatch)
    monkeypatch.setattr(orquestador, "resolver_motores", lambda *a, **k: [_MotorSintetico()])

    resumen = asyncio.run(orquestador.ejecutar(FECHA, publicar=True))

    assert resumen.codigo == orquestador.Codigo.OK
    carpeta = tmp_path / "output" / "episodios" / FECHA.isoformat()
    assert "Titular de prueba" in (carpeta / "guion.md").read_text(encoding="utf-8")
    noticias = json.loads((carpeta / "noticias.json").read_text(encoding="utf-8"))
    assert all(noticias[categoria] for categoria in CATEGORIAS_NOTICIAS)

    mp3 = carpeta_publicacion / "episodios" / f"{FECHA.isoformat()}.mp3"
    assert MP3(mp3).info.length > 0
    assert MP3(resumen.ruta_mp3).info.length > 0
    assert ID3(mp3).get("TIT2") is not None

    items = ET.parse(carpeta_publicacion / "feed.xml").getroot().findall("./channel/item")
    assert len(items) == 1
    enclosure = items[0].find("enclosure")
    assert enclosure.get("url").endswith(".mp3")
    assert int(enclosure.get("length")) == mp3.stat().st_size

    llamadas = [json.loads(linea) for linea in log.read_text(encoding="utf-8").splitlines()]
    assert len(llamadas) >= 3
    if modo == "shim":
        for llamada in llamadas:
            argv = llamada["argv"]
            assert argv[argv.index("--tools") + 1] == ""
            assert Path(llamada["cwd"]).resolve() != ROOT.resolve()

    for d, listado in antes.items():
        assert _listar(ROOT / d) == listado, f"el e2e ha escrito en {d}/ del repo"
