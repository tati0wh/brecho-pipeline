"""
O "site de mentira" do marketplace de brechó.

Simula vendedoras cadastrando peças num dia e grava o resultado como o sistema
de um site faria: um arquivo por dia na zona de chegada (landing).

    data/landing/vendedoras.json                      cadastro das vendedoras
    data/landing/anuncios/data=AAAA-MM-DD/anuncios.jsonl   anúncios do dia (um JSON por linha)

Para os anúncios parecerem reais, o simulador parte de peças sorteadas da base
histórica (marcas, nomes, descrições, tamanhos e cores de verdade) e aplica o
"jeito de escrever" de cada vendedora:

    caprichosa  escreve tudo direitinho
    apressada   tudo minúsculo, sem acento e, às vezes, com erro de digitação na marca
    caixa_alta  escreve a marca e o nome em MAIÚSCULAS
    esquecida   às vezes não informa o tamanho ou a cor

O simulador NÃO lê o banco: ele faz o papel do site, que não sabe nada do pipeline.

Uso:
    python scripts/simulador/gerar_anuncios.py                       # hoje, 150 anúncios
    python scripts/simulador/gerar_anuncios.py --data 2026-11-20 --quantidade 200
"""
import argparse
import json
import random
import re
import unicodedata
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker

PASTA_LANDING = Path("data/landing")
ARQUIVO_VENDEDORAS = PASTA_LANDING / "vendedoras.json"
BASE_HISTORICA = Path("data/raw/roupas_usadas.csv")

ESTILOS = ["caprichosa", "caprichosa", "apressada", "apressada", "caixa_alta", "esquecida"]
VENDEDORAS_INICIAIS = 80


# ---------------------------------------------------------------------------
# base histórica: de onde vêm as peças "de verdade"
# ---------------------------------------------------------------------------
def corrigir_encoding(texto: str) -> str:
    """Mesma ideia da função do pipeline: o site novo grava em UTF-8 correto."""
    if not re.search("[ÃÂâ]", texto):
        return texto
    for codificacao in ("cp1252", "latin-1"):
        try:
            return texto.encode(codificacao).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return texto


def carregar_base_historica() -> pd.DataFrame:
    base = pd.read_csv(BASE_HISTORICA, sep=";", encoding="utf-8-sig", dtype=str, keep_default_na=False)
    colunas = ["marca", "nomeDaPeca", "Descricao", "Tamanho", "Condicao", "Cores", "precoComDesconto", "precoSemDesconto"]
    base = base[colunas].copy()
    for coluna in colunas:
        base[coluna] = base[coluna].map(corrigir_encoding).str.strip()
    return base


# ---------------------------------------------------------------------------
# vendedoras: o cadastro do site, que cresce um pouco a cada dia
# ---------------------------------------------------------------------------
def nova_vendedora(fake: Faker, cadastrada_em: date) -> dict:
    return {
        "id_vendedora": f"v-{uuid.uuid4().hex[:8]}",
        "nome": fake.first_name_female() + " " + fake.last_name(),
        "cidade": fake.city(),
        "estado": fake.estado_sigla(),
        "estilo_escrita": random.choice(ESTILOS),
        "data_cadastro": cadastrada_em.isoformat(),
    }


def carregar_vendedoras(fake: Faker, dia: date) -> list[dict]:
    if ARQUIVO_VENDEDORAS.exists():
        cadastro = json.loads(ARQUIVO_VENDEDORAS.read_text(encoding="utf-8"))
    else:
        inicio = dia - timedelta(days=365)
        cadastro = {
            "dias_gerados": [],
            "vendedoras": [nova_vendedora(fake, inicio + timedelta(days=random.randint(0, 364)))
                           for _ in range(VENDEDORAS_INICIAIS)],
        }

    # todo dia chegam de 0 a 3 vendedoras novas, só na primeira vez que o dia
    # é gerado: rodar o mesmo dia de novo não cria vendedoras repetidas
    if dia.isoformat() not in cadastro["dias_gerados"]:
        cadastro["vendedoras"] += [nova_vendedora(fake, dia) for _ in range(random.randint(0, 3))]
        cadastro["dias_gerados"].append(dia.isoformat())

    ARQUIVO_VENDEDORAS.parent.mkdir(parents=True, exist_ok=True)
    ARQUIVO_VENDEDORAS.write_text(json.dumps(cadastro, ensure_ascii=False, indent=2), encoding="utf-8")
    return [v for v in cadastro["vendedoras"] if v["data_cadastro"] <= dia.isoformat()]


# ---------------------------------------------------------------------------
# o "jeito de escrever" de cada vendedora
# ---------------------------------------------------------------------------
def sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def erro_de_digitacao(texto: str) -> str:
    """Troca, repete ou apaga uma letra, como um dedo apressado no celular."""
    if len(texto) < 4:
        return texto
    i = random.randint(1, len(texto) - 2)
    tipo = random.choice(["trocar", "repetir", "apagar"])
    if tipo == "trocar":
        return texto[:i] + texto[i + 1] + texto[i] + texto[i + 2:]
    if tipo == "repetir":
        return texto[:i] + texto[i] + texto[i:]
    return texto[:i] + texto[i + 1:]


def aplicar_estilo(peca: dict, estilo: str) -> dict:
    if estilo == "apressada":
        peca["marca"] = sem_acento(peca["marca"].lower())
        peca["nome_da_peca"] = sem_acento(peca["nome_da_peca"].lower())
        peca["condicao"] = peca["condicao"].lower()
        if random.random() < 0.15:
            peca["marca"] = erro_de_digitacao(peca["marca"])
    elif estilo == "caixa_alta":
        peca["marca"] = peca["marca"].upper()
        peca["nome_da_peca"] = peca["nome_da_peca"].upper()
    elif estilo == "esquecida":
        if random.random() < 0.3:
            peca["tamanho"] = ""
        if random.random() < 0.3:
            peca["cores"] = ""
    return peca


# ---------------------------------------------------------------------------
# preços: variam um pouco em relação à peça sorteada
# ---------------------------------------------------------------------------
def para_numero(texto: str) -> float | None:
    if not texto:
        return None
    return float(re.sub(r",(?=.*,)", "", texto).replace(",", "."))


def para_texto_br(valor: float) -> str:
    """Como o site original: vírgula decimal e, acima de mil, vírgula também no milhar."""
    texto = f"{valor:,.2f}".replace(",", "#").replace(".", ",").replace("#", ",")
    return texto


def variar_preco(texto: str) -> str:
    valor = para_numero(texto)
    if valor is None:
        return ""
    novo = max(5.0, round(valor * random.uniform(0.9, 1.1)) - 0.10)
    return para_texto_br(novo)


# ---------------------------------------------------------------------------
# geração do dia
# ---------------------------------------------------------------------------
def gerar_dia(dia: date, quantidade: int) -> Path:
    fake = Faker("pt_BR")
    base = carregar_base_historica()
    vendedoras = carregar_vendedoras(fake, dia)

    anuncios = []
    for linha in base.sample(n=quantidade, replace=True).to_dict("records"):
        vendedora = random.choice(vendedoras)
        momento = datetime.combine(dia, time(random.randint(7, 23), random.randint(0, 59), random.randint(0, 59)))
        peca = {
            "id_anuncio": str(uuid.uuid4()),
            "id_vendedora": vendedora["id_vendedora"],
            "data_cadastro": momento.isoformat(),
            "marca": linha["marca"],
            "nome_da_peca": linha["nomeDaPeca"],
            "descricao": linha["Descricao"],
            "tamanho": linha["Tamanho"],
            "condicao": linha["Condicao"],
            "cores": linha["Cores"],
            "preco_com_desconto": variar_preco(linha["precoComDesconto"]),
            "preco_sem_desconto": variar_preco(linha["precoSemDesconto"]),
        }
        anuncios.append(aplicar_estilo(peca, vendedora["estilo_escrita"]))

    anuncios.sort(key=lambda a: a["data_cadastro"])
    pasta = PASTA_LANDING / "anuncios" / f"data={dia.isoformat()}"
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / "anuncios.jsonl"
    with arquivo.open("w", encoding="utf-8") as f:
        for anuncio in anuncios:
            f.write(json.dumps(anuncio, ensure_ascii=False) + "\n")
    return arquivo


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera os anúncios de um dia do marketplace.")
    parser.add_argument("--data", default=date.today().isoformat(), help="dia simulado (AAAA-MM-DD)")
    parser.add_argument("--quantidade", type=int, default=150, help="quantos anúncios gerar")
    parser.add_argument("--semente", type=int, help="semente aleatória, para repetir exatamente a mesma simulação")
    args = parser.parse_args()

    if args.semente is not None:
        random.seed(args.semente)
        Faker.seed(args.semente)

    arquivo = gerar_dia(date.fromisoformat(args.data), args.quantidade)
    print(f"OK: {args.quantidade} anúncios gerados em {arquivo}")


if __name__ == "__main__":
    main()
