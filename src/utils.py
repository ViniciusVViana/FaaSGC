"""Funções compartilhadas pelas baterias de testes do Globus Compute."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml


REQUIRED_RESULT_COLUMNS = [
    "bateria",
    "cenario",
    "id_tarefa",
    "tamanho_bytes",
    "rtt_total_segundos",
    "tempo_worker_segundos",
    "overhead_rede_nuvem_segundos",
    "status",
]


def load_config(config_path: str | Path = "config.yaml") -> dict[str, Any]:
    """Carrega e valida a configuração YAML do experimento."""
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {path}")

    with path.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    if not isinstance(config, dict):
        raise ValueError("A configuração YAML deve conter um objeto no nível raiz.")

    required_keys = {
        "endpoint_id",
        "payload_sizes_bytes",
        "github",
        "repetitions",
    }
    missing_keys = sorted(required_keys - config.keys())
    if missing_keys:
        raise ValueError(
            "Configuração incompleta. Chaves ausentes: " + ", ".join(missing_keys)
        )

    if not isinstance(config["payload_sizes_bytes"], list):
        raise ValueError("'payload_sizes_bytes' deve ser uma lista.")
    if not all(
        isinstance(size, int) and size > 0
        for size in config["payload_sizes_bytes"]
    ):
        raise ValueError("'payload_sizes_bytes' deve conter inteiros positivos.")

    if not isinstance(config["github"], dict):
        raise ValueError("'github' deve ser um objeto.")
    if not isinstance(config["repetitions"], dict):
        raise ValueError("'repetitions' deve ser um objeto.")

    return config


def write_results_csv(
    rows: Sequence[Mapping[str, Any]],
    filename: str | Path,
    *,
    extra_columns: Sequence[str] = (),
    results_directory: str | Path = "./resultados",
) -> Path:
    """Escreve resultados com as colunas padronizadas do experimento."""
    fieldnames = REQUIRED_RESULT_COLUMNS.copy()
    for column in extra_columns:
        if column not in fieldnames:
            fieldnames.append(column)

    output_path = Path(filename)
    if not output_path.is_absolute():
        output_path = Path(results_directory) / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
            delimiter=";",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row_number, row in enumerate(rows, start=1):
            missing_columns = [
                column for column in REQUIRED_RESULT_COLUMNS if column not in row
            ]
            if missing_columns:
                raise ValueError(
                    f"Linha {row_number} sem colunas obrigatórias: "
                    + ", ".join(missing_columns)
                )
            writer.writerow({column: row.get(column, "") for column in fieldnames})

    return output_path
