-- Eventos dos drops, como chegaram do streaming.
-- O consumidor já descartou os duplicados; aqui só organizamos os tipos
-- e tiramos do JSON os campos que só alguns eventos têm.

select
    id_evento,
    id_drop,
    tipo,
    id_cliente,
    id_peca,
    momento_evento,
    recebido_em,
    -- quanto tempo o evento levou para chegar (tempo de processamento - tempo do evento)
    extract(epoch from recebido_em - momento_evento)::numeric(10, 3)  as latencia_segundos,
    evento ->> 'dispositivo'                                           as dispositivo,
    (evento ->> 'preco')::numeric(10, 2)                               as preco,
    evento ->> 'motivo'                                                as motivo
from {{ source('raw', 'drop_eventos') }}
