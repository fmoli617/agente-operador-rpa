"""Ponto central de processamento: consome a fila e roda o pipeline por item."""
import os
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))

from app.fila import Fila
from app.rpa_pipeline import executar_pipeline

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def _carregar_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    config = _carregar_config()
    operador = config["operador"]
    token = os.environ.get("OPERADOR_WS_TOKEN")
    if not token:
        raise RuntimeError("OPERADOR_WS_TOKEN não definido no ambiente")

    fila = Fila()
    while not fila.esta_vazia():
        solicitacao = fila.proximo()
        executar_pipeline(
            solicitacao,
            machine=operador["machine"],
            token=token,
            port=operador["port"],
            cafile=operador.get("cafile"),
        )


if __name__ == "__main__":
    main()
