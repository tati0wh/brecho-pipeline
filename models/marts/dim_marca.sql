-- Dimensão de marcas: uma linha por marca padronizada, no nível mais detalhado
-- (ex.: "Zara Kids"), com a hierarquia para agrupar em níveis mais amplos:
--   marca_mae -> a marca principal da linha ("Zara")
--   grupo     -> a empresa ou varejista dono da marca ("Renner", "C&A")
--   segmento  -> o tipo de linha ("Infantil", "Masculino", "Fitness")
-- e uma faixa de preço calculada pelo preço mediano (limites em dbt_project.yml).
-- A chave (marca_id) é um hash do nome: estável entre execuções.

with pecas as (

    select * from {{ ref('int_roupas_padronizadas') }}

),

marcas as (

    select
        marca_padronizada                                        as marca,
        count(*)                                                 as qtd_pecas,
        count(distinct marca_original)                           as qtd_grafias_originais,
        round(avg(preco_com_desconto), 2)                        as preco_medio,
        percentile_cont(0.5) within group (order by preco_com_desconto)::numeric(10, 2) as preco_mediano
    from pecas
    group by marca_padronizada

)

select
    md5(m.marca)                                             as marca_id,
    m.marca,
    coalesce(h.marca_mae, m.marca)                           as marca_mae,
    h.marca_parceira,
    h.grupo,
    h.segmento,
    coalesce(h.e_collab, false)                              as e_collab,
    m.marca not in ('Sem marca', 'Não informada')            as e_marca_identificada,
    case
        when m.marca in ('Sem marca', 'Não informada')                then 'Não se aplica'
        when m.qtd_pecas < {{ var('minimo_pecas_faixa') }}            then 'Poucos dados'
        when m.preco_mediano >= {{ var('faixa_preco_luxo') }}          then 'Luxo'
        when m.preco_mediano >= {{ var('faixa_preco_premium') }}       then 'Premium'
        when m.preco_mediano >= {{ var('faixa_preco_intermediaria') }} then 'Intermediária'
        else 'Acessível'
    end                                                      as faixa_preco,
    m.qtd_pecas,
    m.qtd_grafias_originais,
    m.preco_medio,
    m.preco_mediano
from marcas m
left join {{ ref('map_marca_hierarquia') }} h
    on h.marca = m.marca
