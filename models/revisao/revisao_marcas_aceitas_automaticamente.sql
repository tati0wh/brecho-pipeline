-- Auditoria do aceite automático: tudo o que o fuzzy matching corrigiu sozinho
-- (similaridade >= {{ var('limiar_aceite_automatico') }}).
--
-- Vale conferir de vez em quando. Se alguma estiver errada (uma marca de verdade
-- que só se parece com outra), adicione a marca ao seeds/revisao_marcas_rejeitadas.csv:
-- no próximo dbt build, ela volta a ser tratada como marca própria.
-- Se estiver certa e você quiser torná-la permanente, copie linha_para_map_marca
-- para o seeds/map_marca.csv.

select
    marca_chave,
    grafias_encontradas,
    qtd_pecas,
    sugestao                                                         as marca_aplicada,
    similaridade,
    marca_chave || ',' || sugestao || ',erro de digitação (aceite automático confirmado)' as linha_para_map_marca
from {{ ref('int_marcas_sugestoes') }}
where e_aceite_automatico
order by similaridade, qtd_pecas desc
