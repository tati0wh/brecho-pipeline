-- Uma linha por marca (chave normalizada), com o nome oficial escolhido
-- e o método usado para chegar nele.
--
-- Camadas de decisão, da mais forte para a mais fraca:
--   1. mapeamento: existe uma regra no seed map_marca  -> vale a regra
--   2. automatico: grafia mais comum entre as que têm letra maiúscula
--                  (ex.: "Zara" ganha de "zara"); se todas forem minúsculas,
--                  usa a primeira letra de cada palavra em maiúscula.

with pecas as (

    select
        marca,
        {{ normalizar_chave('marca') }} as marca_chave
    from {{ ref('stg_roupas_usadas') }}
    where marca is not null

),

grafias as (

    select
        marca_chave,
        marca,
        count(*) as qtd,
        row_number() over (
            partition by marca_chave
            order by (marca <> lower(marca)) desc, count(*) desc, marca
        ) as preferencia
    from pecas
    where marca_chave is not null
    group by marca_chave, marca

),

resumo as (

    select
        marca_chave,
        sum(qtd)                                          as qtd_pecas,
        count(*)                                          as qtd_grafias,
        string_agg(marca, ' | ' order by qtd desc)        as grafias_encontradas,
        max(case when preferencia = 1 then marca end)     as grafia_preferida
    from grafias
    group by marca_chave

)

select
    r.marca_chave,
    coalesce(
        m.marca_padronizada,
        case
            when r.grafia_preferida = lower(r.grafia_preferida) then initcap(r.grafia_preferida)
            else r.grafia_preferida
        end
    )                                                     as marca_padronizada,
    case when m.marca_chave is not null then 'mapeamento' else 'automatico' end as metodo,
    m.motivo,
    r.qtd_pecas,
    r.qtd_grafias,
    r.grafias_encontradas
from resumo r
left join {{ ref('map_marca') }} m
    on m.marca_chave = r.marca_chave
