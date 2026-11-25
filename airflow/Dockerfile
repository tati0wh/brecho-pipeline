# Imagem do Airflow com o que o pipeline precisa para rodar lá dentro.
FROM apache/airflow:3.3.2-python3.12

# O dbt e as bibliotecas do projeto ficam num ambiente Python SEPARADO do Airflow.
# Os dois têm muitas dependências, e instalar tudo junto costuma gerar conflito
# de versões. Assim, cada um fica com as suas.
COPY requirements.txt /tmp/requirements.txt
RUN python -m venv /home/airflow/pipeline-venv \
 && /home/airflow/pipeline-venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt
