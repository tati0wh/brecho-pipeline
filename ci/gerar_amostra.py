"""
Gera uma base histórica SINTÉTICA, no mesmo formato do CSV original, para o CI.

O CSV original não está no repositório (não é meu para redistribuir). Para que o
GitHub Actions consiga rodar o pipeline inteiro, este script inventa anúncios
usando as próprias tabelas de regras do projeto (os seeds) como dicionário:
marcas, tipos de peça, cores, tamanhos e condições que o pipeline conhece.

E reproduz, de propósito, a bagunça que o pipeline precisa tratar:
    - acentos quebrados (UTF-8 lido como Windows-1252), como "SandÃ¡lia";
    - grafias variadas de marca (maiúsculas, minúsculas, espaços);
    - preços com vírgula decimal e, acima de mil, vírgula no milhar ("1,250,00");
    - campos vazios.

Uso:
    python ci/gerar_amostra.py                     # 500 anúncios em data/raw/roupas_usadas.csv
    python ci/gerar_amostra.py --quantidade 2000
"""
import argparse
import csv
import random
from pathlib import Path

SEEDS = Path("seeds")
DESTINO = Path("data/raw/roupas_usadas.csv")


def ler_seed(nome: str) -> list[dict]:
    with (SEEDS / f"{nome}.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def quebrar_encoding(texto: str) -> str:
    """Simula o problema da base original: UTF-8 lido como Windows-1252."""
    try:
        return texto.encode("utf-8").decode("cp1252")
    except UnicodeDecodeError:
        return texto


def preco_br(valor: float) -> str:
    texto = f"{valor:,.2f}".replace(",", "#").replace(".", ",").replace("#", ",")
    return texto[:-3] if texto.endswith(",00") and random.random() < 0.5 else texto


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera a base histórica sintética para o CI.")
    parser.add_argument("--quantidade", type=int, default=500)
    parser.add_argument("--semente", type=int, default=42)
    args = parser.parse_args()
    random.seed(args.semente)

    marcas = sorted({r["marca_padronizada"] for r in ler_seed("map_marca")} - {"Sem marca"}) + ["Sem marca"] * 3
    tipos = [r["palavra_chave"] for r in ler_seed("map_tipo_peca") if r["prioridade"] == "1"]
    cores = [r["palavra_chave"] for r in ler_seed("map_cor")]
    tamanhos = [r["tamanho_chave"].upper() for r in ler_seed("map_tamanho") if r["tipo_rotulo"] in ("letra", "numero")]
    condicoes = ["Novo com etiqueta", "nova com etiqueta", "Novo sem etiqueta", "gentilmente usada", "Usado"]

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    with DESTINO.open("w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.writer(f, delimiter=";")
        escritor.writerow(["", "Unnamed: 0", "marca", "nomeDaPeca", "precoComDesconto", "precoSemDesconto",
                           "Descricao", "Tamanho", "Condicao", "Cores"])
        for i in range(args.quantidade):
            marca = random.choice(marcas)
            marca = random.choice([marca, marca.lower(), marca.upper(), f" {marca} "])
            tipo = random.choice(tipos).capitalize()
            cor = random.choice(cores)
            nome = f"{tipo} {cor.capitalize()} {marca.strip()}"
            original = round(random.uniform(40, 3000), 2)
            venda = round(original * random.uniform(0.2, 0.45), 2)
            descricao = f"Peça {cor} em ótimo estado. Tecido: algodão.\nMedidas: busto {random.randint(80, 110)} cm."
            if random.random() < 0.3:
                nome, descricao = quebrar_encoding(nome), quebrar_encoding(descricao)
            escritor.writerow([
                i, i, marca, nome, preco_br(venda),
                "" if random.random() < 0.03 else preco_br(original),
                descricao,
                random.choice(tamanhos),
                random.choice(condicoes),
                "" if random.random() < 0.02 else cor.capitalize(),
            ])
    print(f"OK: {args.quantidade} anúncios sintéticos em {DESTINO}")


if __name__ == "__main__":
    main()
