import os
import time
import csv
from globus_compute_sdk import Client, Executor

gcc = Client()
endpoint_id = "6ec518b5-1591-4d19-9de5-c3f72fb37d01"


# Função que será executada no Endpoint
def in_band_worker(payload_bytes):
    import time
    start_exe = time.time()
    tamanho_recebido = len(payload_bytes)
    end_exe = time.time()

    return {
        "tamanho_bytes": tamanho_recebido,
        "start_exe": start_exe,
        "end_exe": end_exe
    }


# =====================================================================
# CONFIGURAÇÃO DE PASTAS
# Coloque aqui o caminho (relativo ou absoluto) das pastas que
# contêm os seus lotes de 100 arquivos.
# Ex: "./dados_10kb", "C:/TCC/dados_100kb"
# =====================================================================
pastas_teste = [
    "./arquivos/10KB",
    # "./arquivos/100KB",
    # "./arquivos/1MB",
    # "./arquivos/5MB",
    #"./arquivos/10MB"
]

# Lista para armazenar as métricas e depois salvar no Excel/CSV
dados_telemetria = []

print("Iniciando Bateria de Testes: Tráfego In-Band (Lotes de 100 Arquivos)\n")

with Executor(endpoint_id=endpoint_id, client=gcc) as ex:
    for pasta in pastas_teste:
        if not os.path.isdir(pasta):
            print(f"⚠️ Aviso: A pasta '{pasta}' não foi encontrada. Pulando...")
            continue

        # Lista todos os arquivos válidos dentro da pasta
        arquivos = [f for f in os.listdir(pasta) if os.path.isfile(os.path.join(pasta, f))]
        print(f"\n--- Processando a pasta '{pasta}' com {len(arquivos)} arquivos ---")

        for nome_arquivo in arquivos:
            caminho_completo = os.path.join(pasta, nome_arquivo)

            with open(caminho_completo, "rb") as f:
                payload = f.read()

            tamanho_bytes = len(payload)
            t_envio = time.time()

            try:
                # Submete a tarefa à nuvem
                future = ex.submit(in_band_worker, payload)
                resultado = future.result()
                t_retorno = time.time()

                # Cálculos de tempo
                rtt_total = t_retorno - t_envio
                tempo_execucao_real = resultado["end_exe"] - resultado["start_exe"]
                overhead_nuvem = rtt_total - tempo_execucao_real

                # Guarda o resultado do arquivo atual na memória
                dados_telemetria.append({
                    "pasta_origem": pasta,
                    "nome_arquivo": nome_arquivo,
                    "tamanho_bytes": tamanho_bytes,
                    "rtt_total_segundos": round(rtt_total, 5),
                    "tempo_execucao_segundos": round(tempo_execucao_real, 6),
                    "overhead_segundos": round(overhead_nuvem, 5),
                    "status": "Sucesso"
                })

                # Print minimalista para acompanhar no terminal sem poluir muito
                print(f"[{nome_arquivo}] RTT: {rtt_total:.3f}s | Overhead: {overhead_nuvem:.3f}s")
            except Exception as e:
                print(f" ❌ Falha no arquivo {nome_arquivo}: Limite excedido ou erro de rede.")
                dados_telemetria.append({
                    "pasta_origem": pasta,
                    "nome_arquivo": nome_arquivo,
                    "tamanho_bytes": tamanho_bytes,
                    "rtt_total_segundos": "",
                    "tempo_execucao_segundos": "",
                    "overhead_segundos": "",
                    "status": "Falha"
                })
        # =====================================================================
        # GERAÇÃO DO ARQUIVO CSV (RESULTADOS FINAIS)
        # =====================================================================
        nome_pasta = os.path.basename(os.path.normpath(pasta))
        nome_arquivo_csv = f"resultados_{nome_pasta}.csv"
        print(f"\nGravando os resultados em '{nome_arquivo_csv}'...")
        with open(nome_arquivo_csv, mode='w', newline='', encoding='utf-8-sig') as arquivo_csv:
            colunas = [
                "pasta_origem", "nome_arquivo", "tamanho_bytes",
                "rtt_total_segundos", "tempo_execucao_segundos",
                "overhead_segundos", "status"
            ]
            escritor = csv.DictWriter(arquivo_csv, fieldnames=colunas, delimiter=';')

            escritor.writeheader()
            for linha in dados_telemetria:
                escritor.writerow(linha)
        dados_telemetria.clear()

print("✅ Bateria finalizada! Você já pode importar o '.csv' para gerar os gráficos.")