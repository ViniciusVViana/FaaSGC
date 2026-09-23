"""Bateria 2: ciclo de vida com registro (cold) e execução (warm)."""

from __future__ import annotations

import argparse
import time
import urllib.request
from pathlib import Path
from typing import Any

from globus_compute_sdk import Client

try:
    from .utils import load_config, write_results_csv
except ImportError:
    from utils import load_config, write_results_csv


def in_band_worker(payload: bytes) -> dict[str, Any]:
    """Mede o tempo do worker para um payload enviado diretamente."""
    start_worker = time.perf_counter()
    tamanho_bytes = len(payload)
    end_worker = time.perf_counter()
    return {
        "tamanho_bytes": tamanho_bytes,
        "tempo_worker_segundos": end_worker - start_worker,
    }


def out_of_band_worker(url: str) -> dict[str, Any]:
    """Baixa a URL no endpoint e mede o tempo total do worker."""
    start_worker = time.perf_counter()
    with urllib.request.urlopen(url) as response:
        payload = response.read()
    end_worker = time.perf_counter()
    return {
        "tamanho_bytes": len(payload),
        "tempo_worker_segundos": end_worker - start_worker,
    }


def _poll_task(
    client: Client,
    task_id: str,
    *,
    interval_seconds: float,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Aguarda a conclusão consultando o estado da tarefa."""
    deadline = time.monotonic() + timeout_seconds
    terminal_states = {"success", "succeeded", "failed", "canceled", "cancelled"}

    while True:
        task = client.get_task(task_id)
        if not isinstance(task, dict):
            raise RuntimeError(f"Resposta inválida para a tarefa {task_id}: {task!r}")

        status = str(task.get("status", "")).lower()
        if status in terminal_states:
            if status not in {"success", "succeeded"}:
                raise RuntimeError(f"Tarefa {task_id} terminou com status: {status}")
            return task
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Tempo limite excedido para a tarefa {task_id}.")
        time.sleep(interval_seconds)


def _run_scenario(
    client: Client,
    *,
    endpoint_id: str,
    function_id: str,
    scenario: str,
    inputs: list[tuple[str, Any, int]],
    registration_time: float,
    poll_interval_seconds: float,
    poll_timeout_seconds: float,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for task_id, argument, expected_size in inputs:
        submitted_at = time.perf_counter()
        try:
            task_id_from_api = client.run(
                argument,
                endpoint_id=endpoint_id,
                function_id=function_id,
            )
            _poll_task(
                client,
                task_id_from_api,
                interval_seconds=poll_interval_seconds,
                timeout_seconds=poll_timeout_seconds,
            )
            worker_result = client.get_result(task_id_from_api)
            returned_at = time.perf_counter()

            rtt_total = returned_at - submitted_at
            worker_time = worker_result["tempo_worker_segundos"]
            results.append(
                {
                    "bateria": "bateria_2",
                    "cenario": scenario,
                    "id_tarefa": task_id,
                    "tamanho_bytes": worker_result["tamanho_bytes"],
                    "rtt_total_segundos": round(rtt_total, 6),
                    "tempo_worker_segundos": round(worker_time, 6),
                    "overhead_rede_nuvem_segundos": round(
                        rtt_total - worker_time, 6
                    ),
                    "status": "Sucesso",
                    "tempo_registro_nuvem": round(registration_time, 6),
                }
            )
            print(
                f"[{task_id}] RTT: {rtt_total:.3f}s | "
                f"Registro: {registration_time:.3f}s"
            )
        except Exception as error:
            returned_at = time.perf_counter()
            results.append(
                {
                    "bateria": "bateria_2",
                    "cenario": scenario,
                    "id_tarefa": task_id,
                    "tamanho_bytes": expected_size,
                    "rtt_total_segundos": round(
                        returned_at - submitted_at, 6
                    ),
                    "tempo_worker_segundos": "",
                    "overhead_rede_nuvem_segundos": "",
                    "status": f"Falha: {error}",
                    "tempo_registro_nuvem": round(registration_time, 6),
                }
            )
            print(f"[{task_id}] Falha: {error}")

    return results


def run_bateria(config_path: str | Path = "config.yaml") -> Path:
    """Executa os cenários in-band e out-of-band da bateria 2."""
    config = load_config(config_path)
    endpoint_id = config["endpoint_id"]
    repetitions = config["repetitions"].get("bateria_2")
    if not isinstance(repetitions, int) or repetitions <= 0:
        raise ValueError("'repetitions.bateria_2' deve ser um inteiro positivo.")

    github_config = config["github"]
    urls = github_config.get("urls", [])
    if not isinstance(urls, list) or not all(isinstance(url, str) for url in urls):
        raise ValueError("'github.urls' deve ser uma lista de URLs.")

    poll_config = config.get("polling", {})
    poll_interval = float(poll_config.get("interval_seconds", 2))
    poll_timeout = float(poll_config.get("timeout_seconds", 3600))
    if poll_interval <= 0 or poll_timeout <= 0:
        raise ValueError("Os tempos de polling devem ser positivos.")

    sizes = config["payload_sizes_bytes"]
    in_band_inputs = [
        (f"b2-in-band-{size_index:02d}-{repetition:03d}", b"A" * size, size)
        for size_index, size in enumerate(sizes, start=1)
        for repetition in range(1, repetitions + 1)
    ]
    out_of_band_inputs = [
        (
            f"b2-out-of-band-{url_index:02d}-{repetition:03d}",
            url,
            0,
        )
        for url_index, url in enumerate(urls, start=1)
        for repetition in range(1, repetitions + 1)
    ]

    client = Client()
    results: list[dict[str, Any]] = []
    print("Iniciando Bateria 2: Ciclo de Vida (Cold vs Warm Start)")

    registration_start = time.perf_counter()
    in_band_function_id = client.register_function(in_band_worker)
    in_band_registration_time = time.perf_counter() - registration_start
    print(f"Registro in-band: {in_band_registration_time:.3f}s")

    results.extend(
        _run_scenario(
            client,
            endpoint_id=endpoint_id,
            function_id=in_band_function_id,
            scenario="in_band",
            inputs=in_band_inputs,
            registration_time=in_band_registration_time,
            poll_interval_seconds=poll_interval,
            poll_timeout_seconds=poll_timeout,
        )
    )

    registration_start = time.perf_counter()
    out_of_band_function_id = client.register_function(out_of_band_worker)
    out_of_band_registration_time = time.perf_counter() - registration_start
    print(f"Registro out-of-band: {out_of_band_registration_time:.3f}s")

    results.extend(
        _run_scenario(
            client,
            endpoint_id=endpoint_id,
            function_id=out_of_band_function_id,
            scenario="out_of_band",
            inputs=out_of_band_inputs,
            registration_time=out_of_band_registration_time,
            poll_interval_seconds=poll_interval,
            poll_timeout_seconds=poll_timeout,
        )
    )

    return write_results_csv(
        results,
        "bateria_2.csv",
        extra_columns=("tempo_registro_nuvem",),
        results_directory=config.get("results_directory", "./resultados"),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Executa a Bateria 2 de ciclo de vida."
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
