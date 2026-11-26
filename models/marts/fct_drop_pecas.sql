-- Uma linha por peça em cada drop: o funil da peça e quanto tempo ela levou
-- para vender, com as dimensões do anúncio (marca, tipo de peça, faixa de preço).
-- Os eventos de clientes suspeitas de bot não entram nas contagens.

with eventos as (

    select * from {{ ref('fct_drop_eventos') }}
    where not e_cliente_suspeita_bot

),

inicio_drop as (

    select id_drop, min(momento_evento) as inicio
    from {{ ref('fct_drop_eventos') }}
    group by id_drop

),

por_peca as (

    select
        id_drop,
        id_peca,
        count(*) filter (where tipo = 'visualizou_peca')        as visualizacoes,
        count(distinct id_cliente) filter (where tipo = 'visualizou_peca') as clientes_que_viram,
        count(*) filter (where tipo = 'curtiu')                  as curtidas,
        count(*) filter (where tipo = 'adicionou_ao_carrinho')   as carrinhos,
        count(*) filter (where tipo = 'compra_recusada')         as compras_recusadas,
        min(momento_evento) filter (where tipo = 'comprou')      as momento_venda,
        max(preco) filter (where tipo = 'comprou')               as preco_venda
    from eventos
    group by id_drop, id_peca

)

select
    p.id_drop,
    p.id_peca,
    a.marca_id,
    a.tipo_peca_id,
    a.preco_venda                                              as preco_anunciado,
    p.visualizacoes,
    p.clientes_que_viram,
    p.curtidas,
    p.carrinhos,
    p.compras_recusadas,
    p.momento_venda is not null                                as vendida,
    p.preco_venda,
    round(extract(epoch from p.momento_venda - i.inicio)::numeric, 1) as segundos_ate_vender
from por_peca p
join inicio_drop i
    on i.id_drop = p.id_drop
left join {{ ref('fct_anuncios') }} a
    on a.id_peca = p.id_peca
