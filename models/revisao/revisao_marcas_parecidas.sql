-- Fila de revisão humana: sugestões do fuzzy matching com similaridade abaixo
-- do aceite automático ({{ var('limiar_aceite_automatico') }}). As de cima disso já
-- foram aplicadas sozinhas (veja revisao_marcas_aceitas_automaticamente).
--
-- Nada aqui muda os dados: é uma lista para uma pessoa revisar.
--   - Se a sugestão estiver certa: copie a coluna linha_para_map_marca para o seeds/map_marca.csv
--   - Se estiver errada: adicione a marca ao seeds/revisao_marcas_rejeitadas.csv
--     (a marca passa a ser considerada "ela mesma" e não recebe mais sugestões)
-- Nos dois casos, a marca sai da fila no próximo dbt build.

select
    marca_chave,
    grafias_encontradas,
    qtd_pecas,
    sugestao,
    similaridade,
    confianca,
    marca_chave || ',' || sugestao || ',erro de digitação (revisado)' as linha_para_map_marca
from {{ ref('int_marcas_sugestoes') }}
where not e_rejeitada
  and not e_aceite_automatico
order by similaridade desc, qtd_pecas desc
