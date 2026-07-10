import os
import subprocess

import pytest

from noticia import motor_claude


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_generar_texto_construye_cmd_y_pasa_stdin(monkeypatch):
    capturado = {}

    def fake_run(cmd, **kw):
        capturado["cmd"] = cmd
        capturado["input"] = kw["input"]
        return _Proc(returncode=0, stdout="  respuesta  \n")

    monkeypatch.setattr(motor_claude.subprocess, "run", fake_run)
    out = motor_claude.generar_texto("SYS", "USER")

    assert out == "respuesta"  # stdout .strip()
    assert capturado["input"] == "USER"  # user por stdin
    cmd = capturado["cmd"]
    assert cmd[0] == "claude" and "-p" in cmd
    i = cmd.index("--append-system-prompt")
    assert cmd[i + 1] == "SYS"
    j = cmd.index("--model")
    assert cmd[j + 1] == "sonnet"  # default de settings


def test_generar_texto_returncode_no_cero_devuelve_vacio(monkeypatch):
    monkeypatch.setattr(
        motor_claude.subprocess,
        "run",
        lambda cmd, **kw: _Proc(returncode=1, stderr="Invalid API key / no session"),
    )
    assert motor_claude.generar_texto("s", "u") == ""


def test_generar_texto_sin_binario_lanza_runtimeerror(monkeypatch):
    def boom(cmd, **kw):
        raise FileNotFoundError()

    monkeypatch.setattr(motor_claude.subprocess, "run", boom)
    with pytest.raises(RuntimeError):
        motor_claude.generar_texto("s", "u")


def test_generar_texto_timeout_devuelve_vacio(monkeypatch):
    def boom(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd="claude", timeout=1)

    monkeypatch.setattr(motor_claude.subprocess, "run", boom)
    assert motor_claude.generar_texto("s", "u") == ""


def test_generar_texto_desactiva_las_herramientas(monkeypatch):
    """Sin herramientas, Claude no puede escribir el guion a un fichero.

    Con las herramientas activas actuaba como agente: usaba Write para guardar
    el bloque y devolvía solo un resumen.
    """
    capturado = {}

    def fake_run(cmd, **kw):
        capturado["cmd"] = cmd
        return _Proc(returncode=0, stdout="Álex: hola")

    monkeypatch.setattr(motor_claude.subprocess, "run", fake_run)
    motor_claude.generar_texto("SYS", "USER")

    cmd = capturado["cmd"]
    i = cmd.index("--tools")
    assert cmd[i + 1] == ""  # "" = desactivar todas las herramientas


def test_generar_texto_aisla_cwd_en_directorio_temporal(monkeypatch):
    capturado = {}

    def fake_run(cmd, **kw):
        capturado["cwd"] = kw.get("cwd")
        return _Proc(returncode=0, stdout="ok")

    monkeypatch.setattr(motor_claude.subprocess, "run", fake_run)
    motor_claude.generar_texto("SYS", "USER")

    cwd = capturado["cwd"]
    assert cwd
    assert cwd != os.getcwd()
