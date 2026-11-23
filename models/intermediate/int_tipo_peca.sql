-- Descobre o tipo da peça (vestido, calça, sapato...) a partir das palavras
-- do nome e, se o nome não ajudar, da descrição.
--
-- Regras, em ordem:
--   1. o nome vem antes da descrição;
--   2. palavra forte (prioridade 1) vem antes de palavra fraca (prioridade 2);
--   3. empate: vale a palavra que aparece primeiro no texto.
-- Na descrição só valem palavras fortes, para evitar falsos positivos.
-- A comparação é sempre por palavra inteira.

with pecas as (

    select id_peca, nome_da_peca, descricao
    from {{ ref('stg_roupas_usadas') }}

),

palavras as (

    select p.id_peca, 'nome' as fonte, 1 as ordem_fonte, t.palavra, t.posicao
    from pecas p
    cross join lateral regexp_split_to_table({{ normalizar_chave('p.nome_da_peca') }}, ' ')
        with ordinality as t(palavra, posicao)

    union all

    select p.id_peca, 'descricao' as fonte, 2 as ordem_fonte, t.palavra, t.posicao
    from pecas p
    cross join lateral regexp_split_to_table({{ normalizar_chave('p.descricao') }}, ' ')
        with ordinality as t(palavra, posicao)

),

correspondencias as (

    select
        pa.id_peca,
        pa.fonte,
        pa.ordem_fonte,
        pa.posicao,
        pa.palavra,
        m.tipo_peca,
        m.prioridade
    from palavras pa
    join {{ ref('map_tipo_peca') }} m
        on m.palavra_chave = pa.palavra
    where pa.fonte = 'nome' or m.prioridade = 1

),

escolhida as (

    select distinct on (id_peca) *
    from correspondencias
    order by id_peca, ordem_fonte, prioridade, posicao

)

select
    p.id_peca,
    coalesce(e.tipo_peca, 'Não identificado') as tipo_peca,
    case e.fonte
        when 'nome'      then 'inferido_nome'
        when 'descricao' then 'inferido_descricao'
        else 'nao_identificado'
    end                                         as metodo_tipo_peca,
    e.palavra                                   as palavra_gatilho_tipo
from pecas p
left join escolhida e
    on e.id_peca = p.id_peca
