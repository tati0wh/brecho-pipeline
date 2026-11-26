-- Cada peça aparece uma única vez em cada drop no fct_drop_pecas.
-- O teste falha se encontrar alguma combinação (drop, peça) repetida.

select id_drop, id_peca, count(*) as repeticoes
from {{ ref('fct_drop_pecas') }}
group by id_drop, id_peca
having count(*) > 1
