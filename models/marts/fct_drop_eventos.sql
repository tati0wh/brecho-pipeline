-- Fato de eventos dos drops: uma linha por clique.
-- Cada evento ganha uma marcação de suspeita de bot, calculada com uma
-- janela deslizante: quantos "adicionou_ao_carrinho" a mesma cliente fez
-- nos 10 segundos anteriores (inclusive este).

with eventos as (

    select * from {{ ref('stg_drop_eventos') }}

),

com_janela as (

    select
        *,
        count(*) filter (where tipo = 'adicionou_ao_carrinho') over (
            partition by id_drop, id_cliente
            order by momento_evento
            range between interval '10 seconds' preceding and current row
        ) as carrinhos_ultimos_10s
    from eventos

)

select
    id_evento,
    id_drop,
    tipo,
    id_cliente,
    id_peca,
    momento_evento,
    recebido_em,
    latencia_segundos,
    dispositivo,
    preco,
    motivo,
    carrinhos_ultimos_10s,
    -- uma cliente é suspeita de bot se, em algum momento do drop, passou do limite
    max(carrinhos_ultimos_10s) over (partition by id_drop, id_cliente) > {{ var('limite_bot_carrinhos_10s') }}
        as e_cliente_suspeita_bot
from com_janela
