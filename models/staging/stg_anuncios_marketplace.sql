-- Staging dos anúncios que chegam do marketplace (carga incremental).
-- Mesma limpeza do histórico (macros/limpeza.sql), mais os campos que só
-- o site tem: o código do anúncio, a vendedora e a data de cadastro.

with origem as (

    select * from {{ source('raw', 'anuncios') }}

)

select
    id_anuncio                                        as id_peca,
    'marketplace'                                     as origem,
    id_vendedora,
    cast(data_cadastro as timestamp)                  as data_cadastro,

    {{ limpar_texto_curto('marca') }}                 as marca,
    {{ limpar_texto_curto('nome_da_peca') }}          as nome_da_peca,
    {{ limpar_texto_curto('tamanho') }}               as tamanho,
    {{ limpar_texto_curto('condicao') }}              as condicao,
    {{ limpar_texto_curto('cores') }}                 as cores,
    {{ limpar_texto_longo('descricao') }}             as descricao,
    {{ converter_preco('preco_com_desconto') }}       as preco_com_desconto,
    {{ converter_preco('preco_sem_desconto') }}       as preco_sem_desconto,

    _arquivo_origem,
    cast(null as bigint)                              as _linha_origem,
    _carregado_em
from origem
