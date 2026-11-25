-- Cadastro das vendedoras do marketplace.

select
    id_vendedora,
    {{ limpar_texto_curto('nome') }}      as nome,
    {{ limpar_texto_curto('cidade') }}    as cidade,
    upper(trim(estado))                   as estado,
    estilo_escrita,
    cast(data_cadastro as date)           as data_cadastro,
    _carregado_em
from {{ source('raw', 'vendedoras') }}
