-- Dimensão de marcas: uma linha por marca padronizada.
-- A chave (marca_id) é um hash do nome: estável entre execuções,
-- então a mesma marca sempre recebe o mesmo id.

with pecas as (

    select * from {{ ref('int_roupas_padronizadas') }}

)

select
    md5(marca_padronizada)                                   as marca_id,
    marca_padronizada                                        as marca,
    case
        when marca_padronizada in ('Sem marca', 'Não informada') then false
        else true
    end                                                      as e_marca_identificada,
    count(*)                                                 as qtd_pecas,
    count(distinct marca_original)                           as qtd_grafias_originais,
    round(avg(preco_com_desconto), 2)                        as preco_medio,
    percentile_cont(0.5) within group (order by preco_com_desconto)::numeric(10, 2) as preco_mediano
from pecas
group by marca_padronizada
