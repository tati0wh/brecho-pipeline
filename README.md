# Marketplace de brechó: pipeline de dados

Projeto de engenharia de dados que organiza e padroniza uma base de roupas
usadas com entradas livres de vendedoras (marcas, tamanhos, cores, condição).

> Em construção. Este README cresce a cada etapa.

## Como rodar

1. Copie `.env.example` para `.env` e defina uma senha.
2. Suba o banco: `docker compose up -d`
3. Crie o ambiente Python e instale as dependências:
   `python -m venv .venv`, ative-o e rode `pip install -r requirements.txt`
4. Coloque o CSV em `data/raw/` e carregue:
   `python scripts/carregar_raw.py data/raw/roupas_usadas.csv`

## Estrutura

```
.
├── data/raw/              # CSV original (fora do Git)
├── scripts/
│   └── carregar_raw.py    # carga do CSV na tabela raw.roupas_usadas
├── docker-compose.yml     # Postgres local
├── .env.example           # modelo de configuração
└── requirements.txt
```

## Decisões

- **O raw não é alterado:** os valores entram como estão no arquivo, inclusive
  com problemas de encoding. A limpeza acontece nas camadas seguintes.
- **Tudo entra como texto:** tipos (preço, por exemplo) são convertidos na
  staging, onde a conversão fica visível e testável.
- **Carga idempotente:** rodar o script de novo substitui a tabela em vez de
  duplicar linhas.
