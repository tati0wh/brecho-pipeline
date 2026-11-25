-- Resultado final das marcas: uma linha por marca (chave normalizada).
--
-- Parte de int_marcas_base e aplica as sugestões do fuzzy matching que foram
-- aceitas automaticamente (similaridade >= {{ var('limiar_aceite_automatico') }}).
--
-- Métodos possíveis, do mais forte para o mais fraco:
--   mapeamento         regra do seed map_marca (decisão humana)
--   regra_letra_unica  a "marca" é uma letra solta -> "Não informada"
--   fuzzy_automatico   erro de digitação corrigido pelo fuzzy matching, sem revisão humana
--   automatico         grafia preferida entre as que têm a mesma chave

with base as (

    select * from {{ ref('int_marcas_base') }}

),

aceitas as (

    select marca_chave, sugestao, similaridade
    from {{ ref('int_marcas_sugestoes') }}
    where e_aceite_automatico

)

select
    b.marca_chave,
    coalesce(a.sugestao, b.marca_padronizada)                    as marca_padronizada,
    case when a.marca_chave is not null then 'fuzzy_automatico' else b.metodo end as metodo,
    b.motivo,
    a.similaridade                                               as similaridade_fuzzy,
    b.qtd_pecas,
    b.qtd_grafias,
    b.grafias_encontradas
from base b
left join aceitas a
    on a.marca_chave = b.marca_chave
