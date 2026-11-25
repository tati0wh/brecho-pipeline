-- Define o grupo de cor de cada peça.
--
--   1. informado: usa a coluna Cores, preenchida pela vendedora.
--      Se as palavras apontarem para um grupo só ("Azul marinho" -> Azul), vale ele.
--      Se apontarem para mais de um ("Preto e Branco"), a peça é Colorido.
--   2. inferido: se a coluna Cores estiver vazia ou não tiver nenhuma palavra
--      conhecida, procura a primeira palavra de cor no nome e depois na descrição.
-- A comparação é sempre por palavra inteira ("redondo" não vira "red").

with pecas as (

    select id_peca, nome_da_peca, descricao, cores
    from {{ ref('stg_anuncios') }}

),

-- 1. cor informada pela vendedora
informadas as (

    select
        p.id_peca,
        count(distinct m.grupo_cor)                                     as qtd_grupos,
        min(m.grupo_cor)                                                as grupo_unico,
        string_agg(distinct t.palavra, ', ')                            as palavras
    from pecas p
    cross join lateral regexp_split_to_table({{ normalizar_chave('p.cores') }}, ' ') as t(palavra)
    join {{ ref('map_cor') }} m
        on m.palavra_chave = t.palavra
    group by p.id_peca

),

-- 2. cor inferida pelo texto
palavras_texto as (

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

inferidas as (

    select distinct on (pt.id_peca)
        pt.id_peca,
        pt.fonte,
        pt.palavra,
        m.grupo_cor
    from palavras_texto pt
    join {{ ref('map_cor') }} m
        on m.palavra_chave = pt.palavra
    order by pt.id_peca, pt.ordem_fonte, pt.posicao

)

select
    p.id_peca,
    case
        when i.qtd_grupos = 1 then i.grupo_unico
        when i.qtd_grupos > 1 then 'Colorido'
        when inf.grupo_cor is not null then inf.grupo_cor
        else 'Não identificado'
    end as grupo_cor,
    case
        when i.qtd_grupos >= 1      then 'informado'
        when inf.fonte = 'nome'      then 'inferido_nome'
        when inf.fonte = 'descricao' then 'inferido_descricao'
        else 'nao_identificado'
    end as metodo_cor,
    coalesce(i.palavras, inf.palavra) as palavras_gatilho_cor
from pecas p
left join informadas i
    on i.id_peca = p.id_peca
left join inferidas inf
    on inf.id_peca = p.id_peca
