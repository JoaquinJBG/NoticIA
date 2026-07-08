import asyncio

import pytest

from noticia import cli


def test_producir_episodio_falla_sin_clave(monkeypatch):
    monkeypatch.setattr(cli.settings, "groq_api_key", None)
    with pytest.raises(RuntimeError):
        asyncio.run(cli.producir_episodio())
