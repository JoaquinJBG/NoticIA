.DEFAULT_GOAL := ayuda
.PHONY: ayuda preparar test lint formato guion audio episodio limpiar

# Guion de entrada para `make audio`: por defecto, el más reciente de output/.
GUION ?= $(shell ls -t output/guion_*.md 2>/dev/null | head -1)
SALIDA ?= output/NoticIA_audio.mp3

ayuda:
	@echo "NoticIA — atajos"
	@echo
	@echo "  make preparar   Instala dependencias y comprueba que todo está en su sitio"
	@echo "  make test       Ejecuta la suite de tests"
	@echo "  make lint       ruff check + comprobación de formato"
	@echo "  make formato    Aplica ruff format"
	@echo
	@echo "  make guion      Genera solo el guion (Claude), sin audio -> output/guion_<fecha>.md"
	@echo "  make audio      Locuta y masteriza un guion ya escrito, sin regenerarlo"
	@echo "                    GUION=ruta.md  (por defecto: el más reciente de output/)"
	@echo "                    SALIDA=out.mp3 (por defecto: $(SALIDA))"
	@echo "  make episodio   Pipeline completo: ingesta + guion + locución + mastering"
	@echo
	@echo "  make limpiar    Borra los fragmentos temporales de audio"

preparar:
	@./scripts/preparar.sh

test:
	@uv run pytest -q

lint:
	@uv run ruff check
	@uv run ruff format --check src/noticia tests

formato:
	@uv run ruff format src/noticia tests

guion:
	@uv run noticia --solo-guion

audio:
ifeq ($(strip $(GUION)),)
	@echo "No hay ningún guion en output/. Genera uno con 'make guion' o pasa GUION=ruta.md" >&2
	@exit 1
endif
	@echo "Locutando $(GUION) -> $(SALIDA)"
	@uv run noticia --solo-audio --guion "$(GUION)" --salida "$(SALIDA)"

episodio:
	@uv run noticia

limpiar:
	@rm -f temp/fragmento_*.mp3
	@echo "Fragmentos temporales borrados."
