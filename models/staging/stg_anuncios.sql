-- Todos os anúncios numa tabela só: o histórico do CSV e os que chegam do
-- marketplace. A coluna "origem" diz de onde veio cada um.
-- Daqui para frente, o pipeline inteiro lê deste modelo.

select * from {{ ref('stg_roupas_usadas') }}

union all

select * from {{ ref('stg_anuncios_marketplace') }}
