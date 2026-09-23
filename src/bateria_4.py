"""Bateria 4: comparação de download out-of-band em disco e em RAM."""

from __future__ import annotations

import argparse
import os
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable

from globus_compute_sdk import Client, Executor

try:
    from .utils import load_config, write_results_csv
except ImportError:
    from utils import load_config, write_results_csv


def disk_worker(url: str) -> dict[str, Any]:
    """Baixa a URL para um arquivo temporário e remove o arquivo ao terminar."""
    start_worker = time.perf_counter()
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix="globus_compute_",
            suffix=".payload",
            delete=False,
        ) as temporary_file:
            temporary_path = temporary_file.name

        urllib.request.urlretrieve(url, temporary_path)
        tamanho_bytes = os.path.getsize(temporary_path)
        status = "Sucesso"
    except Exception as error:
        tamanho_bytes = 0
        status = f"Falha no download: {error}"
    finally:
        if temporary_path is not None:
            try:
                os.remove(temporary_path)
            except FileNotFoundError:
                pass

    end_worker = time.perf_counter()
    return {
        "tamanho_bytes": tamanho_bytes,
        "tempo_worker_segundos": end_worker - start_worker,
        "status": status,
    }


def ram_worker(url: str) -> dict[str, Any]:
    """Baixa a URL diretamente para a memória volátil do worker."""
    start_worker = time.perf_counter()
    try:
        with urllib.request.urlopen(url) as response:
            payload = response.read()
        tamanho_bytes = len(payload)
        status = "Sucesso"
    except Exception as error:
        tamanho_bytes = 0
        status = f"Falha no download: {error}"

    end_worker = time.perf_counter()
    return {
        "tamanho_bytes": tamanho_bytes,
        "tempo_worker_segundos": end_worker - start_worker,
        "status": status,
    }


def _run_scenario(
    executor: Executor,
    worker: Callable[[str], dict[str, Any]],
    scenario: str,
    urls: list[str],
    repetitions: int,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for url_index, url in enumerate(urls, start=1):
        for repetition in range(1, repetitions + 1):
            task_id = f"b4-{scenario}-url{url_index:02d}-r{repetition:03d}"
            submitted_at = time.perf_counter()
            try:
                future = executor.submit(worker, url)
                worker_result = future.result()
                returned_at = time.perf_counter()
                rtt_total = returned_at - submitted_at
                worker_time = worker_result["tempo_worker_segundos"]
                status = worker_result["status"]
                results.append(
                    {
                        "bateria": "bateria_4",
                        "cenario": scenario,
                        "id_tarefa": task_id,
                        "tamanho_bytes": worker_result["tamanho_bytes"],
                        "rtt_total_segundos": round(rtt_total, 6),
                        "tempo_worker_segundos": round(worker_time, 6),
                        "overhead_rede_nuvem_segundos": round(
                            rtt_total - worker_time, 6
                        ),
                        "status": status,
                    }
                )
                print(
                    f"[{task_id}] RTT: {rtt_total:.3f}s | "
                    f"Worker: {worker_time:.3f}s | Status: {status}"
                )
            except Exception as error:
                returned_at = time.perf_counter()
                results.append(
                    {
                        "bateria": "bateria_4",
                        "cenario": scenario,
                        "id_tarefa": task_id,
                        "tamanho_bytes": 0,
                        "rtt_total_segundos": round(
                            returned_at - submitted_at, 6
                        ),
                        "tempo_worker_segundos": "",
                        "overhead_rede_nuvem_segundos": "",
                        "status": f"Falha no Globus Compute: {error}",
                    }
                )
                print(f"[{task_id}] Falha: {error}")

    return results


def run_bateria(config_path: str | Path = "config.yaml") -> Path:
    """Executa a comparação entre os workers de disco e RAM."""
    config = load_config(config_path)
    endpoint_id = config["endpoint_id"]
    repetitions = config["repetitions"].get("bateria_4")
    if not isinstance(repetitions, int) or repetitions <= 0:
        raise ValueError("'repetitions.bateria_4' deve ser um inteiro positivo.")

    urls = config["github"].get("urls", [])
    if not isinstance(urls, list) or not urls:
        raise ValueError("'github.urls' deve ser uma lista não vazia.")
    if not all(isinstance(url, str) and url for url in urls):
        raise ValueError("'github.urls' deve conter apenas URLs não vazias.")

    client = Client()
    results: list[dict[str, Any]] = []
    print("Iniciando Bateria 4: Mitigação Out-of-Band (Disco vs RAM)")

    with Executor(endpoint_id=endpoint_id, client=client) as executor:
        results.extend(
            _run_scenario(
                executor,
                disk_worker,
                "out_of_band_disco",
                urls,
                repetitions,
            )
        )
        results.extend(
            _run_scenario(
                executor,
                ram_worker,
                "out_of_band_ram",
                urls,
                repetitions,
            )
        )

    return write_results_csv(
        results,
        "bateria_4.csv",
        results_directory=config.get("results_directory", "./resultados"),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Executa a Bateria 4 de mitigação out-of-band."
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Caminho do arquivo YAML de configuração.",
    )
    args = parser.parse_args()
    output_path = run_bateria(args.config)
    print(f"Resultados salvos em: {output_path}")


if __name__ == "__main__":
    main()
