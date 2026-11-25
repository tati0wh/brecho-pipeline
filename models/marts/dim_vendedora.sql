-- Dimensão de vendedoras: uma linha por vendedora do marketplace,
-- com o volume de anúncios e indicadores de qualidade do cadastro.
--
-- Os indicadores mostram quanto trabalho o pipeline tem com cada vendedora:
--   pct_sem_tamanho   -> anúncios sem tamanho informado
--   pct_sem_cor       -> anúncios sem cor informada (cor teve de ser inferida)
--   pct_marca_regra   -> anúncios cuja marca só foi resolvida por uma regra do map_marca

with vendedoras as (

    select * from {{ ref('stg_vendedoras') }}

),

anuncios as (

    select
        id_vendedora,
        count(*)                                                        as qtd_anuncios,
        min(data_cadastro)                                              as primeiro_anuncio,
        max(data_cadastro)                                              as ultimo_anuncio,
        round(avg(preco_com_desconto), 2)                               as preco_medio,
        round(100.0 * avg(case when tamanho_original is null then 1 else 0 end), 1) as pct_sem_tamanho,
        round(100.0 * avg(case when metodo_cor <> 'informado' then 1 else 0 end), 1) as pct_sem_cor,
        round(100.0 * avg(case when metodo_marca = 'mapeamento' then 1 else 0 end), 1) as pct_marca_regra
    from {{ ref('int_roupas_padronizadas') }}
    where origem = 'marketplace'
    group by id_vendedora

)

select
    v.id_vendedora,
    v.nome,
    v.cidade,
    v.estado,
    v.data_cadastro,
    v.estilo_escrita,
    coalesce(a.qtd_anuncios, 0)   as qtd_anuncios,
    a.primeiro_anuncio,
    a.ultimo_anuncio,
    a.preco_medio,
    a.pct_sem_tamanho,
    a.pct_sem_cor,
    a.pct_marca_regra
from vendedoras v
left join anuncios a
    on a.id_vendedora = v.id_vendedora
