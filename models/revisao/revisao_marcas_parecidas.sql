-- Fila de revisão: marcas raras que parecem ser erro de digitação de uma marca comum.
--
-- Como funciona:
--   1. "referências" são marcas com pelo menos {{ var('minimo_pecas_referencia') }} peças
--      (provavelmente escritas certo, já que aparecem muito);
--   2. "candidatas" são as marcas raras que ainda não têm regra no seed map_marca;
--   3. para cada candidata, compara com todas as referências usando similaridade
--      de trigramas (pg_trgm), com e sem espaços ("levis" x "levi s");
--   4. se a similaridade passar de {{ var('limiar_similaridade') }}, a melhor referência vira sugestão.
--
-- Nada aqui muda os dados: é uma lista para uma pessoa revisar.
--   - Se a sugestão estiver certa: copie a coluna linha_para_map_marca para o seeds/map_marca.csv
--   - Se estiver errada: adicione a marca ao seeds/revisao_marcas_rejeitadas.csv
--     (a marca passa a ser considerada "ela mesma" e não recebe mais sugestões)
-- Nos dois casos, a marca sai da fila no próximo dbt build.

with marcas as (

    select * from {{ ref('int_marcas') }}

),

referencias as (

    select marca_chave, marca_padronizada, qtd_pecas
    from marcas
    where qtd_pecas >= {{ var('minimo_pecas_referencia') }}

),

candidatas as (

    select marca_chave, marca_padronizada, qtd_pecas, grafias_encontradas
    from marcas
    where qtd_pecas < {{ var('minimo_pecas_referencia') }}
      and metodo = 'automatico'

),

pares as (

    select
        c.marca_chave,
        c.grafias_encontradas,
        c.qtd_pecas,
        c.marca_padronizada                                         as marca_atual,
        r.marca_padronizada                                         as sugestao,
        r.qtd_pecas                                                 as qtd_pecas_sugestao,
        greatest(
            similarity(c.marca_chave, r.marca_chave),
            similarity(replace(c.marca_chave, ' ', ''), replace(r.marca_chave, ' ', ''))
        )                                                           as similaridade
    from candidatas c
    cross join referencias r
    where c.marca_padronizada <> r.marca_padronizada

),

melhor_sugestao as (

    select distinct on (marca_chave) *
    from pares
    where similaridade >= {{ var('limiar_similaridade') }}
    order by marca_chave, similaridade desc, qtd_pecas_sugestao desc

)

select
    m.marca_chave,
    m.grafias_encontradas,
    m.qtd_pecas,
    m.sugestao,
    round(m.similaridade::numeric, 2)                               as similaridade,
    case
        when m.similaridade >= 0.8 then 'alta'
        when m.similaridade >= 0.65 then 'media'
        else 'baixa'
    end                                                             as confianca,
    m.marca_chave || ',' || m.sugestao || ',erro de digitação (revisado)' as linha_para_map_marca
from melhor_sugestao m
left join {{ ref('revisao_marcas_rejeitadas') }} rej
    on rej.marca_chave = m.marca_chave
where rej.marca_chave is null
order by m.similaridade desc, m.qtd_pecas desc
