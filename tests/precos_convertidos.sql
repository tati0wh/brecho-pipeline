-- Garante que todos os preços da staging podem ser lidos como número.
-- Views só convertem os dados quando são consultadas, então um preço
-- mal formatado pode passar despercebido; este teste força a leitura completa.

select id_peca
from {{ ref('stg_roupas_usadas') }}
where preco_com_desconto < 0
   or preco_sem_desconto < 0
