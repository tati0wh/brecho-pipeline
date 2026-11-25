"""
DAG do pipeline do brechó: o "roteiro" que o Airflow executa todo dia.

    gerar_anuncios  ->  carregar_novos  ->  dbt_build

1. gerar_anuncios: o simulador cria os anúncios do dia (o "site" funcionando)
2. carregar_novos: a carga incremental leva os arquivos novos para o raw
3. dbt_build:      o dbt transforma tudo e roda os testes

Se uma tarefa falha, as seguintes não rodam: o dbt nunca trabalha com uma
carga pela metade. Cada tarefa tenta de novo uma vez antes de falhar.

Para gerar um dia específico (por exemplo, para preencher dias passados),
dispare a DAG pela interface com o parâmetro "data" preenchido (AAAA-MM-DD).
Vazio, ela gera o dia de hoje.
"""
import os
from datetime import datetime, timedelta

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

PROJETO = os.environ.get("PROJETO_DIR", "/opt/brecho")
PYTHON = os.environ.get("PIPELINE_PYTHON", "python")
DBT = os.path.join(os.path.dirname(PYTHON), "dbt")

with DAG(
    dag_id="pipeline_brecho",
    description="Simula o dia do marketplace, carrega os dados novos e roda o dbt.",
    schedule="@daily",
    start_date=datetime(2026, 11, 1),
    catchup=False,
    params={"data": "", "quantidade": 150},
    default_args={"retries": 1, "retry_delay": timedelta(minutes=1)},
    tags=["brecho"],
) as dag:

    gerar_anuncios = BashOperator(
        task_id="gerar_anuncios",
        cwd=PROJETO,
        bash_command=(
            f"{PYTHON} scripts/simulador/gerar_anuncios.py"
            " --quantidade {{ params.quantidade }}"
            "{% if params.data %} --data {{ params.data }}{% endif %}"
        ),
    )

    carregar_novos = BashOperator(
        task_id="carregar_novos",
        cwd=PROJETO,
        bash_command=f"{PYTHON} scripts/carregar_novos.py",
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        cwd=PROJETO,
        bash_command=f"{DBT} build",
    )

    gerar_anuncios >> carregar_novos >> dbt_build
