"""Bateria 1: medição de latência basal com payloads in-band."""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

from globus_compute_sdk import Client, Executor

try:
    from .utils import load_config, write_results_csv
except ImportError:
    from utils import load_config, write_results_csv


def in_band_worker(payload: bytes) -> dict[str, Any]:
    """Retorna o tamanho recebido e o tempo gasto no worker."""
    start_worker = time.perf_counter()
    tamanho_bytes = len(payload)
    end_worker = time.perf_counter()

    return {
        "tamanho_bytes": tamanho_bytes,
        "tempo_worker_segundos": end_worker - start_worker,
    }


def run_bateria(config_path: str | Path = "config.yaml") -> Path:
    """Executa a bateria 1 e grava seus resultados em CSV."""
    config = load_config(config_path)
    endpoint_id = config["endpoint_id"]
    repetitions = config["repetitions"].get("bateria_1")

    if not isinstance(repetitions, int) or repetitions <= 0:
        raise ValueError("'repetitions.bateria_1' deve ser um inteiro positivo.")

    results: list[dict[str, Any]] = []
    client = Client()

    print("Iniciando Bateria 1: Latência Basal (In-Band)")
    with Executor(endpoint_id=endpoint_id, client=client) as executor:
        for size_index, tamanho_bytes in enumerate(
            config["payload_sizes_bytes"], start=1
        ):
            payload = b"A" * tamanho_bytes
            print(
                f"\nPayload {size_index}: {tamanho_bytes} bytes "
                f"({repetitions} repetições)"
            )

            for repetition in range(1, repetitions + 1):
                task_id = f"b1-{size_index:02d}-{repetition:03d}"
                submitted_at = time.perf_counter()

                try:
                    future = executor.submit(in_band_worker, payload)
                    worker_result = future.result()
                    returned_at = time.perf_counter()

                    rtt_total = returned_at - submitted_at
                    tempo_worker = worker_result["tempo_worker_segundos"]
                    results.append(
                        {
                            "bateria": "bateria_1",
                            "cenario": "in_band",
                            "id_tarefa": task_id,
                            "tamanho_bytes": worker_result["tamanho_bytes"],
                            "rtt_total_segundos": round(rtt_total, 6),
                            "tempo_worker_segundos": round(tempo_worker, 6),
                            "overhead_rede_nuvem_segundos": round(
                                rtt_total - tempo_worker, 6
                            ),
                            "status": "Sucesso",
                        }
                    )
                    print(
                        f"[{task_id}] RTT: {rtt_total:.3f}s | "
                        f"Overhead: {rtt_total - tempo_worker:.3f}s"
                    )
                except Exception as error:
                    returned_at = time.perf_counter()
                    results.append(
                        {
                            "bateria": "bateria_1",
                            "cenario": "in_band",
                            "id_tarefa": task_id,
                            "tamanho_bytes": tamanho_bytes,
                            "rtt_total_segundos": round(
                                returned_at - submitted_at, 6
                            ),
                            "tempo_worker_segundos": "",
                            "overhead_rede_nuvem_segundos": "",
                            "status": f"Falha: {error}",
                        }
                    )
                    print(f"[{task_id}] Falha: {error}")

    output_path = write_results_csv(
        results,
        "bateria_1.csv",
        results_directory=config.get("results_directory", "./resultados"),
    )
    print(f"\nResultados salvos em: {output_path}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Executa a Bateria 1 de latência basal in-band."
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Caminho do arquivo YAML de configuração.",
    )
    args = parser.parse_args()
    run_bateria(args.config)


if __name__ == "__main__":
    main()
