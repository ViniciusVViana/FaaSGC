"""Bateria 3: concorrência e saturação com rajadas de tarefas."""

from __future__ import annotations

import argparse
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable

from globus_compute_sdk import Client, Executor

try:
    from .utils import build_github_urls, load_config, write_results_csv
except ImportError:
    from utils import build_github_urls, load_config, write_results_csv


def in_band_worker(payload: bytes) -> dict[str, Any]:
    """Processa um payload recebido diretamente pelo worker."""
    start_worker = time.perf_counter()
    tamanho_bytes = len(payload)
    end_worker = time.perf_counter()
    return {
        "tamanho_bytes": tamanho_bytes,
        "tempo_worker_segundos": end_worker - start_worker,
    }


def out_of_band_worker(url: str) -> dict[str, Any]:
    """Baixa a URL no worker e retorna o tamanho recebido."""
    start_worker = time.perf_counter()
    with urllib.request.urlopen(url) as response:
        payload = response.read()
    end_worker = time.perf_counter()
    return {
        "tamanho_bytes": len(payload),
        "tempo_worker_segundos": end_worker - start_worker,
    }


def _build_burst_inputs(
    scenario: str,
    burst_size: int,
    repetition: int,
    payload_sizes: list[int],
    urls: list[str],
) -> list[tuple[str, Any, int]]:
    if scenario == "in_band":
        if not payload_sizes:
            raise ValueError("É necessário informar payload_sizes_bytes para in-band.")
        return [
            (
                f"b3-{scenario}-{burst_size}-r{repetition:03d}-t{task_number:03d}",
                b"A" * payload_sizes[(task_number - 1) % len(payload_sizes)],
                payload_sizes[(task_number - 1) % len(payload_sizes)],
            )
            for task_number in range(1, burst_size + 1)
        ]

    if not urls:
        raise ValueError("É necessário informar github.paths para out-of-band.")
    return [
        (
            f"b3-{scenario}-{burst_size}-r{repetition:03d}-t{task_number:03d}",
            urls[(task_number - 1) % len(urls)],
            0,
        )
        for task_number in range(1, burst_size + 1)
    ]


def _submit_and_collect_burst(
    executor: Executor,
    worker: Callable[[Any], dict[str, Any]],
    scenario: str,
    burst_size: int,
    inputs: list[tuple[str, Any, int]],
    repetition: int,
) -> list[dict[str, Any]]:
    submitted_at = time.perf_counter()
    futures: list[tuple[str, int, Any, Any]] = []

    for task_id, argument, expected_size in inputs:
        task_submitted_at = time.perf_counter()
        future = executor.submit(worker, argument)
        futures.append((task_id, expected_size, future, task_submitted_at))

    results: list[dict[str, Any]] = []
    for task_id, expected_size, future, task_submitted_at in futures:
        try:
            worker_result = future.result()
            returned_at = time.perf_counter()
            rtt_total = returned_at - task_submitted_at
            worker_time = worker_result["tempo_worker_segundos"]
            results.append(
                {
                    "bateria": "bateria_3",
                    "cenario": scenario,
                    "id_tarefa": task_id,
                    "tamanho_bytes": worker_result["tamanho_bytes"],
                    "rtt_total_segundos": round(rtt_total, 6),
                    "tempo_worker_segundos": round(worker_time, 6),
                    "overhead_rede_nuvem_segundos": round(
                        rtt_total - worker_time, 6
                    ),
                    "status": "Sucesso",
                }
            )
        except Exception as error:
            returned_at = time.perf_counter()
            results.append(
                {
                    "bateria": "bateria_3",
                    "cenario": scenario,
                    "id_tarefa": task_id,
                    "tamanho_bytes": expected_size,
                    "rtt_total_segundos": round(
                        returned_at - task_submitted_at, 6
                    ),
                    "tempo_worker_segundos": "",
                    "overhead_rede_nuvem_segundos": "",
                    "status": f"Falha: {error}",
                }
            )
            print(f"[{task_id}] Falha: {error}")

    burst_duration = time.perf_counter() - submitted_at
    successful_tasks = sum(row["status"] == "Sucesso" for row in results)
    throughput = successful_tasks / burst_duration if burst_duration > 0 else 0
    print(
        f"Rajada {burst_size} ({scenario}, repetição {repetition}): "
        f"{successful_tasks}/{burst_size} concluídas | "
        f"throughput: {throughput:.2f} tarefas/s"
    )
    return results


def run_bateria(config_path: str | Path = "config.yaml") -> Path:
    """Executa as rajadas dos cenários in-band e out-of-band."""
    config = load_config(config_path)
    endpoint_id = config["endpoint_id"]
    repetitions = config["repetitions"].get("bateria_3")
    if not isinstance(repetitions, int) or repetitions <= 0:
        raise ValueError("'repetitions.bateria_3' deve ser um inteiro positivo.")

    concurrency_levels = config.get("concurrency_levels")
    if not isinstance(concurrency_levels, list) or not concurrency_levels:
        raise ValueError("'concurrency_levels' deve ser uma lista não vazia.")
    if not all(isinstance(level, int) and level > 0 for level in concurrency_levels):
        raise ValueError("'concurrency_levels' deve conter inteiros positivos.")

    payload_sizes = config["payload_sizes_bytes"]
    urls = build_github_urls(config)
    results: list[dict[str, Any]] = []
    client = Client()

    print("Iniciando Bateria 3: Concorrência e Saturação")
    with Executor(endpoint_id=endpoint_id, client=client) as executor:
        for scenario, worker in (
            ("in_band", in_band_worker),
            ("out_of_band", out_of_band_worker),
        ):
            for burst_size in concurrency_levels:
                for repetition in range(1, repetitions + 1):
                    inputs = _build_burst_inputs(
                        scenario,
                        burst_size,
                        repetition,
                        payload_sizes,
                        urls,
                    )
                    results.extend(
                        _submit_and_collect_burst(
                            executor,
                            worker,
                            scenario,
                            burst_size,
                            inputs,
                            repetition,
                        )
                    )

    return write_results_csv(
        results,
        "bateria_3.csv",
        results_directory=config.get("results_directory", "./resultados"),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Executa a Bateria 3 de concorrência e saturação."
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
