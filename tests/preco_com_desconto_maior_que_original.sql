-- Aviso: peças em que o preço do brechó é MAIOR que o preço da peça nova.
-- Provavelmente erro de cadastro. O teste lista essas peças para revisão,
-- mas não trava o pipeline (severity: warn).

{{ config(severity='warn') }}

select
    id_peca,
    nome_da_peca,
    preco_com_desconto,
    preco_sem_desconto
from {{ ref('stg_roupas_usadas') }}
where preco_com_desconto > preco_sem_desconto
