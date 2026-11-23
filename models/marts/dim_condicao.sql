-- Dimensão de condição da peça, vinda direto das regras do seed.

select distinct
    md5(condicao_padronizada)   as condicao_id,
    condicao_padronizada        as condicao,
    ordem_conservacao,
    condicao_padronizada in ('Nova com etiqueta', 'Novo sem etiqueta') as e_nova
from {{ ref('map_condicao') }}
