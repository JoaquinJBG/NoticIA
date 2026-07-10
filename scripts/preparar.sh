#!/usr/bin/env bash
#
# Deja NoticIA listo para funcionar tras clonar el repositorio.
# Es idempotente: se puede ejecutar tantas veces como haga falta.
#
#   ./scripts/preparar.sh
#
# Sale con código != 0 si falta algo que impide trabajar.

set -uo pipefail

BLOQUEANTES=0

ok()      { printf '  \033[32m✔\033[0m %s\n' "$1"; }
aviso()   { printf '  \033[33m!\033[0m %s\n' "$1"; }
fallo()   { printf '  \033[31m✘\033[0m %s\n' "$1"; BLOQUEANTES=$((BLOQUEANTES + 1)); }
titulo()  { printf '\n\033[1m%s\033[0m\n' "$1"; }

cd "$(dirname "$0")/.." || exit 1

printf '\033[1mNoticIA — preparación del entorno\033[0m\n'

# ---------------------------------------------------------------- uv
titulo "Gestor de paquetes"
if command -v uv >/dev/null 2>&1; then
    ok "uv $(uv --version | awk '{print $2}')"
else
    fallo "uv no está instalado. Instálalo con:"
    printf '      curl -LsSf https://astral.sh/uv/install.sh | sh\n'
    printf '\nSin uv no se puede continuar.\n'
    exit 1
fi

# ---------------------------------------------------------------- deps
titulo "Dependencias de Python"
if uv sync --quiet; then
    ok "uv sync completado"
    version_py=$(uv run python -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null)
    if [ -n "$version_py" ]; then
        ok "Python $version_py (requerido: >= 3.12)"
    else
        fallo "No se pudo determinar la versión de Python"
    fi
else
    fallo "uv sync falló"
fi

# ---------------------------------------------------------------- ffmpeg
titulo "Audio (pydub necesita ffmpeg)"
for binario in ffmpeg ffprobe; do
    if command -v "$binario" >/dev/null 2>&1; then
        ok "$binario"
    else
        fallo "$binario no está instalado"
    fi
done
if ! command -v ffmpeg >/dev/null 2>&1; then
    printf '      Debian/Ubuntu/WSL:  sudo apt install ffmpeg\n'
    printf '      macOS:              brew install ffmpeg\n'
fi

# ---------------------------------------------------------------- claude
titulo "Cerebro del guion"
if command -v claude >/dev/null 2>&1; then
    ok "claude CLI $(claude --version 2>/dev/null | awk '{print $1}')"
    aviso "Necesita una sesión de Claude Max iniciada. Si no la tienes, ejecuta: claude"
else
    aviso "claude CLI no encontrado: no podrás GENERAR guiones (sí locutar los ya escritos)."
    printf '      Instalación: https://claude.ai/download\n'
fi
printf '      No hacen falta API keys: el guion usa tu suscripción de Claude Max.\n'

# ---------------------------------------------------------------- gpu
titulo "GPU (solo para el futuro motor de voz, Fase 3C)"
if command -v nvidia-smi >/dev/null 2>&1; then
    tarjeta=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -1)
    if [ -n "$tarjeta" ]; then
        ok "GPU detectada: $tarjeta"
    else
        aviso "nvidia-smi existe pero no reporta ninguna GPU"
    fi
else
    aviso "Sin GPU NVIDIA. El motor de voz actual (edge-tts) funciona igual."
fi

# ---------------------------------------------------------------- tests
titulo "Comprobación final"
if uv run pytest -q >/tmp/noticia_pytest.log 2>&1; then
    ok "$(tail -n 2 /tmp/noticia_pytest.log | grep -oE '[0-9]+ passed.*' | head -1)"
else
    fallo "La suite de tests no pasa. Detalle:"
    tail -n 15 /tmp/noticia_pytest.log | sed 's/^/      /'
fi

# ---------------------------------------------------------------- resumen
printf '\n'
if [ "$BLOQUEANTES" -eq 0 ]; then
    printf '\033[32m✔ Todo listo.\033[0m Prueba: \033[1mmake guion\033[0m o \033[1mmake ayuda\033[0m\n'
    exit 0
fi
printf '\033[31m✘ Faltan %s cosas por resolver (ver arriba).\033[0m\n' "$BLOQUEANTES"
exit 1
