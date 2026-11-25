"""
Carga incremental: leva para o banco só o que chegou de novo na zona de chegada.

    data/landing/anuncios/data=AAAA-MM-DD/anuncios.jsonl  ->  raw.anuncios
    data/landing/vendedoras.json                           ->  raw.vendedoras

Para cada arquivo de anúncios, a tabela raw._controle_cargas guarda o caminho e
uma "impressão digital" (hash SHA-256) do conteúdo:

    arquivo novo                     -> carrega
    já carregado, conteúdo igual     -> pula
    já carregado, conteúdo diferente -> apaga as linhas antigas desse arquivo e carrega de novo

Por isso a carga é idempotente: rodar duas vezes dá o mesmo resultado, sem duplicar.
Os anúncios entram como vieram (texto), seguindo a regra de que o raw é sagrado.
As vendedoras são o cadastro completo do site: a tabela é substituída a cada carga.

Uso:
    python scripts/carregar_novos.py
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

PASTA_ANUNCIOS = Path("data/landing/anuncios")
ARQUIVO_VENDEDORAS = Path("data/landing/vendedoras.json")

COLUNAS_ANUNCIO = ["id_anuncio", "id_vendedora", "data_cadastro", "marca", "nome_da_peca", "descricao",
                   "tamanho", "condicao", "cores", "preco_com_desconto", "preco_sem_desconto"]


def conectar():
    load_dotenv()
    url = (
        f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
    )
    return create_engine(url)


def preparar_tabelas(conn) -> None:
    conn.execute(text("create schema if not exists raw"))
    colunas = ",\n".join(f"{c} text" for c in COLUNAS_ANUNCIO)
    conn.execute(text(f"""
        create table if not exists raw.anuncios (
            {colunas},
            _arquivo_origem text not null,
            _carregado_em timestamptz not null
        )"""))
    conn.execute(text("""
        create table if not exists raw._controle_cargas (
            arquivo text primary key,
            hash_conteudo text not null,
            qtd_linhas integer not null,
            carregado_em timestamptz not null
        )"""))


def hash_do_arquivo(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def carregar_anuncios(engine) -> None:
    arquivos = sorted(PASTA_ANUNCIOS.glob("data=*/anuncios.jsonl"))
    with engine.begin() as conn:
        preparar_tabelas(conn)
        ja_carregados = dict(conn.execute(text("select arquivo, hash_conteudo from raw._controle_cargas")).all())

    novos = substituidos = pulados = linhas = 0
    for caminho in arquivos:
        nome = caminho.as_posix()
        hash_atual = hash_do_arquivo(caminho)
        if ja_carregados.get(nome) == hash_atual:
            pulados += 1
            continue

        df = pd.read_json(caminho, lines=True, dtype=False)
        df = df.reindex(columns=COLUNAS_ANUNCIO).astype("string")
        df["_arquivo_origem"] = nome
        df["_carregado_em"] = datetime.now(timezone.utc)

        # tudo numa transação só: ou o arquivo entra inteiro, ou nada muda
        with engine.begin() as conn:
            if nome in ja_carregados:
                conn.execute(text("delete from raw.anuncios where _arquivo_origem = :a"), {"a": nome})
                substituidos += 1
            else:
                novos += 1
            df.to_sql("anuncios", conn, schema="raw", if_exists="append", index=False)
            conn.execute(text("""
                insert into raw._controle_cargas (arquivo, hash_conteudo, qtd_linhas, carregado_em)
                values (:a, :h, :q, now())
                on conflict (arquivo) do update
                set hash_conteudo = excluded.hash_conteudo,
                    qtd_linhas    = excluded.qtd_linhas,
                    carregado_em  = excluded.carregado_em
            """), {"a": nome, "h": hash_atual, "q": len(df)})
        linhas += len(df)

    print(f"Anúncios: {novos} arquivo(s) novo(s), {substituidos} substituído(s), "
          f"{pulados} já carregado(s); {linhas} linha(s) inserida(s).")


def carregar_vendedoras(engine) -> None:
    if not ARQUIVO_VENDEDORAS.exists():
        print("Vendedoras: nenhum cadastro encontrado.")
        return
    cadastro = json.loads(ARQUIVO_VENDEDORAS.read_text(encoding="utf-8"))
    df = pd.DataFrame(cadastro["vendedoras"]).astype("string")
    df["_carregado_em"] = datetime.now(timezone.utc)
    df.to_sql("vendedoras", engine, schema="raw", if_exists="replace", index=False)
    print(f"Vendedoras: {len(df)} no cadastro.")


def main() -> None:
    engine = conectar()
    carregar_anuncios(engine)
    carregar_vendedoras(engine)


if __name__ == "__main__":
    main()
