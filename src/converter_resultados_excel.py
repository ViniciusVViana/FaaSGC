"""Converte os resultados CSV para o formato decimal esperado pelo Excel."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


DECIMAL_COLUMNS = {
    "rtt_total_segundos",
    "tempo_worker_segundos",
    "overhead_rede_nuvem_segundos",
    "tempo_registro_nuvem",
}
DECIMAL_PATTERN = re.compile(r"^-?\d+\.\d+$")


def _convert_decimal(value: str, column: str) -> str:
    """Troca o separador decimal somente nas colunas de tempo."""
    if column in DECIMAL_COLUMNS and DECIMAL_PATTERN.fullmatch(value):
        return value.replace(".", ",")
    return value


def convert_csv(input_path: Path, output_path: Path) -> None:
    """Converte um CSV mantendo cabeçalho, delimitador e demais valores."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", newline="", encoding="utf-8-sig") as input_file:
        reader = csv.DictReader(input_file, delimiter=";")
        if reader.fieldnames is None:
            raise ValueError(f"CSV sem cabeçalho: {input_path}")

        rows = [
            {
                column: _convert_decimal(row.get(column, ""), column)
                for column in reader.fieldnames
            }
            for row in reader
        ]

    with output_path.open("w", newline="", encoding="utf-8-sig") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=reader.fieldnames,
            delimiter=";",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def convert_results(
    input_directory: str | Path = "resultados",
    output_directory: str | Path = "resultados_excel",
    *,
    in_place: bool = False,
) -> list[Path]:
    """Converte todos os CSVs da pasta e retorna os arquivos processados."""
    input_path = Path(input_directory)
    if not input_path.is_dir():
        raise FileNotFoundError(f"Pasta de resultados não encontrada: {input_path}")

    destination = input_path if in_place else Path(output_directory)
    csv_files = sorted(input_path.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"Nenhum arquivo CSV encontrado em: {input_path}")

    converted_files: list[Path] = []
    for csv_file in csv_files:
        output_path = destination / csv_file.name
        convert_csv(csv_file, output_path)
        converted_files.append(output_path)
    return converted_files


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Converte os decimais dos resultados CSV para o Excel."
    )
    parser.add_argument(
        "--input-dir",
        default="resultados",
        help="Pasta com os CSVs originais.",
    )
    parser.add_argument(
        "--output-dir",
        default="resultados_excel",
        help="Pasta de destino, usada quando --in-place não é informado.",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Sobrescreve os CSVs originais em vez de criar uma pasta de saída.",
    )
    args = parser.parse_args()

    converted_files = convert_results(
        args.input_dir,
        args.output_dir,
        in_place=args.in_place,
    )
    print(f"{len(converted_files)} arquivo(s) convertido(s):")
    for converted_file in converted_files:
        print(f"- {converted_file}")


if __name__ == "__main__":
    main()
