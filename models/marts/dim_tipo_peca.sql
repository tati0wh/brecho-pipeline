-- Dimensão de tipos de peça: uma linha por tipo, com um agrupamento mais amplo
-- (Roupa, Calçado, Bolsa, Acessório) para análises de alto nível.

with tipos as (

    select distinct tipo_peca
    from {{ ref('int_roupas_padronizadas') }}

)

select
    md5(tipo_peca)  as tipo_peca_id,
    tipo_peca,
    case
        when tipo_peca = 'Sapato'                       then 'Calçado'
        when tipo_peca = 'Bolsa'                        then 'Bolsa'
        when tipo_peca in ('Acessório', 'Chapelaria')   then 'Acessório'
        when tipo_peca in ('Outros', 'Não identificado') then 'Outros'
        else 'Roupa'
    end             as grupo_produto
from tipos
