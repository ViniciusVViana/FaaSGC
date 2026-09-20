# TCC: Análise de Desempenho e Avaliação de Latência no Globus Compute



Repositório destinado aos códigos-fonte, scripts de telemetria e dados brutos do Trabalho de Conclusão de Curso (TCC) em Ciência da Computação.



**Instituição:** Universidade Estadual do Oeste do Paraná (UNIOESTE) - Campus Cascavel  

**Autor:** Vinicius Vieira Viana  

**Orientador:** Prof. Guilherme Galante  

**Ano:** 2026  



---



## 📌 Sobre o Projeto



Este projeto investiga os gargalos de desempenho e latência na execução de funções federadas (Federated Function as a Service - FFaaS) no paradigma do *Computing Continuum*. O foco do estudo é a plataforma **Globus Compute**, analisando o impacto do volume de dados na comunicação direta com o serviço de nuvem (*in-band*).



Como solução arquitetural, o trabalho propõe e avalia uma estratégia de mitigação baseada em estagiamento de dados externo (*out-of-band data staging*), visando contornar a sobrecarga da infraestrutura central e viabilizar o uso do *framework* para o tráfego de grandes volumes de informações.



## 📂 Estrutura do Repositório



* `src/`: Contém os scripts em Python utilizados nos experimentos.

&#x20; * `client/`: Scripts do cliente submissor, responsáveis por disparar as requisições assíncronas e coletar os *timestamps* (Round-Trip Time).

&#x20; * `endpoint\_workers/`: Códigos das funções FaaS que são executadas nos *endpoints* locais (abordagens *in-band* e *out-of-band*).

* `data/`: Diretório destinado aos *payloads* de teste e aos arquivos `.csv` gerados com os resultados das métricas de latência. *(Nota: arquivos muito grandes não são versionados).*

* `notebooks/`: *Jupyter Notebooks* utilizados para a análise estatística dos dados e geração dos gráficos apresentados no documento do TCC.

* `requirements.txt`: Lista de bibliotecas e dependências necessárias para a execução do projeto.



## ⚙️ Tecnologias Utilizadas



* **Linguagem:** Python 3.x

* **Framework Serverless/FFaaS:** Globus Compute SDK

* **Análise de Dados:** Pandas, Matplotlib



## 🚀 Como Executar (Em breve)



As instruções detalhadas para configuração do *endpoint* local, autenticação no *Globus Auth* e execução das baterias de testes serão adicionadas conforme a consolidação dos scripts.

