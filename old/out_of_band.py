import time
import csv
import os
from globus_compute_sdk import Client, Executor

gcc = Client()
endpoint_id = "524768d2-8974-4e97-8c33-78139815f953"


# =====================================================================
# A FUNÇÃO DO WORKER (Executada no Endpoint)
# Recebe a URL Raw e faz o download usando biblioteca nativa do Python
# =====================================================================
def out_of_band_worker(raw_url):
    import time
    import urllib.request
    import os

    start_exe = time.time()

    # Extrai o nome do arquivo a partir da URL para salvar em disco
    nome_arquivo = raw_url.split('/')[-1]
    caminho_destino = f'./temp_{nome_arquivo}'

    try:
        # Faz o download direto do GitHub contornando o Globus Compute
        urllib.request.urlretrieve(raw_url, caminho_destino)
        tamanho_recebido = os.path.getsize(caminho_destino)

        # LIMPEZA DE AMBIENTE (Deleta o arquivo para garantir idempotência)
        os.remove(caminho_destino)
        status = "Sucesso"
    except Exception as e:
        tamanho_recebido = 0
        status = f"Falha no Download: {str(e)}"

    end_exe = time.time()

    return {
        "tamanho_bytes": tamanho_recebido,
        "start_exe": start_exe,
        "end_exe": end_exe,
        "status": status
    }


# =====================================================================
# CONFIGURAÇÃO DO REPOSITÓRIO GITHUB
# =====================================================================
# Lista das subpastas que você criou dentro do seu repositório
pastas_github = [
    #"10KB",
    #"100KB",
    #"1MB",
    "5MB",
    "10MB"]

# URL base do modo Raw do seu repositório (sem o nome da pasta e do arquivo no final)
base_url = "https://raw.githubusercontent.com/ViniciusVViana/arquivos_endpoint/refs/heads/main"

print("Iniciando Bateria de Testes: Tráfego Out-of-Band Automatizado via GitHub\n")

with Executor(endpoint_id=endpoint_id, client=gcc) as ex:
    for pasta in pastas_github:
        print(f"\n--- Processando o lote da pasta '{pasta}' ---")
        dados_desta_pasta = []

        # Loop para gerar dinamicamente as 100 URLs de arquivo_001.txt até arquivo_100.txt
        for i in range(1, 101):
            # O ':03d' garante a formatação de 3 dígitos com zeros à esquerda (001, 002, ..., 100)
            # ATENÇÃO: Se a extensão dos seus arquivos for outra (ex: .bin), altere aqui para '.bin'
            nome_arquivo = f"arquivo_{i:03d}.txt"

            # Monta a URL final idêntica ao padrão do GitHub Raw
            url_completa = f"{base_url}/{pasta}/{nome_arquivo}"

            t_envio = time.time()

            try:
                # Submete a tarefa enviando apenas a STRING da URL (levíssima)
                future = ex.submit(out_of_band_worker, url_completa)
                resultado = future.result()
                t_retorno = time.time()

                # Decomposição dos tempos
                rtt_total = t_retorno - t_envio
                tempo_execucao_real = resultado["end_exe"] - resultado["start_exe"]
                overhead_nuvem = rtt_total - tempo_execucao_real

                # Salva os resultados formatando com o padrão de planilha brasileira
                dados_desta_pasta.append({
                    "nome_arquivo": nome_arquivo,
                    "tamanho_bytes": resultado["tamanho_bytes"],
                    "rtt_total_segundos": str(round(rtt_total, 5)).replace('.', ','),
                    "tempo_execucao_segundos": str(round(tempo_execucao_real, 6)).replace('.', ','),
                    "overhead_segundos": str(round(overhead_nuvem, 5)).replace('.', ','),
                    "status": resultado["status"]
                })

                print(f"[{nome_arquivo}] RTT: {rtt_total:.3f}s | Status: {resultado['status']}")

            except Exception as e:
                print(f" ❌ Falha crítica no envio do arquivo {nome_arquivo}: {e}")
                dados_desta_pasta.append({
                    "nome_arquivo": nome_arquivo,
                    "tamanho_bytes": 0,
                    "rtt_total_segundos": "",
                    "tempo_execucao_segundos": "",
                    "overhead_segundos": "",
                    "status": f"Erro Globus: {str(e)}"
                })

        # =====================================================================
        # GERAÇÃO DO CSV EXCLUSIVO DESTA PASTA
        # =====================================================================
        nome_arquivo_csv = f"resultados_out_of_band_{pasta}.csv"

        with open(nome_arquivo_csv, mode='w', newline='', encoding='utf-8-sig') as arquivo_csv:
            colunas = [
                "nome_arquivo", "tamanho_bytes",
                "rtt_total_segundos", "tempo_execucao_segundos",
                "overhead_segundos", "status"
            ]
            escritor = csv.DictWriter(arquivo_csv, fieldnames=colunas, delimiter=';')
            escritor.writeheader()
            for linha in dados_desta_pasta:
                escritor.writerow(linha)

        print(f"✅ Resultados salvos em: {nome_arquivo_csv}")

print("\n🚀 Todos os testes Out-of-Band foram concluídos e os CSVs foram gerados!")