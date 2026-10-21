"""`claude -p` simulado: mismo contrato de argv y stdin que `motor_claude.generar_texto`.

Se usa como script (modo shim: lo lanza un ejecutable `claude` falso) y como módulo
(modo inproc: `responder`). No importa nada del paquete `tests` para poder ejecutarse suelto.
"""

import json
import os
import re
import sys

_TITULAR = re.compile(r"^\s*- (.+?) \(", re.MULTILINE)


def responder(prompt: str) -> str:
    """Diálogo determinista que cita el primer titular de la lista de noticias del prompt."""
    encontrado = _TITULAR.search(prompt)
    titular = encontrado.group(1) if encontrado else "las noticias de hoy"
    return (
        f"Álex: Empezamos con una noticia importante de hoy: {titular}, y conviene ir por partes.\n"
        "María: Tienes razón, Álex, porque hay varios detalles que merece la pena explicar.\n"
        "Álex: Pues vamos con ello, que tenemos bastante tela que cortar en este bloque.\n"
        "María: Perfecto, y que nadie se pierda lo importante de esta historia."
    )


def _contrato_roto(argv: list[str]) -> str | None:
    if "-p" not in argv:
        return "falta -p"
    if "--tools" not in argv or argv[argv.index("--tools") + 1 : argv.index("--tools") + 2] != [""]:
        return "--tools debe ir seguido de un argumento vacío"
    if "--append-system-prompt" not in argv:
        return "falta --append-system-prompt"
    return None


def registrar_llamada(argv: list[str] | None, cwd: str | None, prompt: str) -> None:
    ruta = os.environ.get("NOTICIA_CLAUDE_FALSO_LOG")
    if not ruta:
        return
    linea = {"argv": argv, "cwd": cwd, "stdin": prompt[:200]}
    with open(ruta, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(linea, ensure_ascii=False) + "\n")


def main() -> int:
    argv = sys.argv[1:]
    prompt = sys.stdin.read()
    registrar_llamada(argv, os.getcwd(), prompt)
    motivo = _contrato_roto(argv)
    if motivo:
        print(f"claude falso: contrato roto: {motivo}", file=sys.stderr)
        return 2
    print(responder(prompt))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    raise SystemExit(main())
