-- Staging do CSV histórico: limpeza técnica, sem regras de negócio.
-- A limpeza em si está nas macros de macros/limpeza.sql, as mesmas usadas
-- para os anúncios do marketplace.

with origem as (

    select * from {{ source('raw', 'roupas_usadas') }}

)

select
    'hist-' || unnamed_0                              as id_peca,
    'historico'                                       as origem,
    cast(null as text)                                as id_vendedora,
    cast(null as timestamp)                           as data_cadastro,

    {{ limpar_texto_curto('marca') }}                 as marca,
    {{ limpar_texto_curto('nome_da_peca') }}          as nome_da_peca,
    {{ limpar_texto_curto('tamanho') }}               as tamanho,
    {{ limpar_texto_curto('condicao') }}              as condicao,
    {{ limpar_texto_curto('cores') }}                 as cores,
    {{ limpar_texto_longo('descricao') }}             as descricao,
    {{ converter_preco('preco_com_desconto') }}       as preco_com_desconto,
    {{ converter_preco('preco_sem_desconto') }}       as preco_sem_desconto,

    _arquivo_origem,
    _linha_origem,
    _carregado_em
from origem
