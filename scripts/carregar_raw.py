"""
Carrega o CSV original do brechó no Postgres, na tabela raw.roupas_usadas.

Princípio: o raw é sagrado. Os VALORES entram exatamente como estão no
arquivo, incluindo acentos quebrados, espaços e vírgulas nos preços.
Toda limpeza acontece depois, na staging (dbt).

As únicas mudanças feitas aqui:
  - nomes de colunas em snake_case (para facilitar o SQL);
  - colunas de controle (_arquivo_origem, _linha_origem, _carregado_em).

Uso:
    python scripts/carregar_raw.py data/raw/roupas_usadas.csv
"""
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

TABELA = "roupas_usadas"
SCHEMA = "raw"


def para_snake_case(nome: str) -> str:
    nome = nome.strip()
    nome = re.sub(r"([a-z])([A-Z])", r"\1_\2", nome)  # nomeDaPeca -> nome_Da_Peca
    nome = re.sub(r"[^0-9a-zA-Z]+", "_", nome)        # "Unnamed: 0.1" -> Unnamed_0_1
    return nome.strip("_").lower()


def main(caminho_csv: str) -> None:
    load_dotenv()
    url = (
        f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
    )
    engine = create_engine(url)

    # dtype=str + keep_default_na=False: tudo entra como texto, sem o pandas
    # "adivinhar" tipos nem transformar vazios em NaN.
    df = pd.read_csv(
        caminho_csv,
        sep=";",
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False,
    )

    # A primeira coluna do arquivo não tem nome; o pandas a chama de "Unnamed: 0.1".
    df.columns = [para_snake_case(c) for c in df.columns]

    df["_arquivo_origem"] = Path(caminho_csv).name
    df["_linha_origem"] = range(1, len(df) + 1)
    df["_carregado_em"] = datetime.now(timezone.utc)

    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))

    # Troca todo o conteúdo da tabela: rodar duas vezes dá o mesmo resultado,
    # sem duplicar linhas (carga idempotente). A tabela é esvaziada (TRUNCATE)
    # em vez de apagada, porque as views do dbt dependem dela. Tudo numa
    # transação: se der erro, o conteúdo antigo continua lá.
    with engine.begin() as conn:
        existe = conn.execute(text("select to_regclass(:t)"), {"t": f"{SCHEMA}.{TABELA}"}).scalar()
        if existe:
            conn.execute(text(f"truncate table {SCHEMA}.{TABELA}"))
        df.to_sql(TABELA, conn, schema=SCHEMA, if_exists="append", index=False, chunksize=5000)

    with engine.connect() as conn:
        total = conn.execute(text(f"SELECT COUNT(*) FROM {SCHEMA}.{TABELA}")).scalar()
    print(f"OK: {total} linhas carregadas em {SCHEMA}.{TABELA}")
    print("Colunas:", ", ".join(df.columns))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python scripts/carregar_raw.py <caminho_do_csv>")
    main(sys.argv[1])
