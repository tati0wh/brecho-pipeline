-- Uma linha por drop, com o resumo do evento e o funil de clientes:
-- quantas viram alguma peça -> colocaram no carrinho -> compraram.
-- O funil desconsidera as clientes suspeitas de bot.

with eventos as (

    select * from {{ ref('fct_drop_eventos') }}

),

resumo as (

    select
        id_drop,
        min(momento_evento)                                                    as inicio,
        max(momento_evento)                                                    as fim,
        count(*)                                                               as eventos,
        count(distinct id_peca)                                                as pecas,
        count(distinct id_peca) filter (where tipo = 'comprou')                as pecas_vendidas,
        coalesce(sum(preco) filter (where tipo = 'comprou'), 0)                as receita,
        count(*) filter (where tipo = 'compra_recusada')                       as compras_recusadas,
        count(distinct id_cliente) filter (where e_cliente_suspeita_bot)       as clientes_suspeitas_bot,
        round(avg(latencia_segundos), 3)                                       as latencia_media_segundos,
        count(distinct id_cliente) filter (where not e_cliente_suspeita_bot and tipo = 'visualizou_peca')       as clientes_viram,
        count(distinct id_cliente) filter (where not e_cliente_suspeita_bot and tipo = 'adicionou_ao_carrinho') as clientes_carrinho,
        count(distinct id_cliente) filter (where not e_cliente_suspeita_bot and tipo = 'comprou')               as clientes_compraram
    from eventos
    group by id_drop

)

select
    id_drop,
    inicio,
    fim,
    round(extract(epoch from fim - inicio)::numeric, 1)                as duracao_segundos,
    eventos,
    pecas,
    pecas_vendidas,
    round(100.0 * pecas_vendidas / nullif(pecas, 0), 1)                as pct_pecas_vendidas,
    receita,
    compras_recusadas,
    clientes_suspeitas_bot,
    latencia_media_segundos,
    clientes_viram,
    clientes_carrinho,
    clientes_compraram,
    round(100.0 * clientes_carrinho / nullif(clientes_viram, 0), 1)    as pct_viram_para_carrinho,
    round(100.0 * clientes_compraram / nullif(clientes_carrinho, 0), 1) as pct_carrinho_para_compra
from resumo
