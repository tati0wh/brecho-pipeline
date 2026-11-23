-- Aviso: sugestões de ALTA confiança que ainda não foram revisadas.
-- Não trava o pipeline; serve de lembrete para olhar a fila de revisão.

{{ config(severity='warn') }}

select marca_chave, sugestao, similaridade
from {{ ref('revisao_marcas_parecidas') }}
where confianca = 'alta'
