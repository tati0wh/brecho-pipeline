-- Fato de anúncios: uma linha por peça anunciada (histórico e marketplace).
-- Liga-se às dimensões de marca, tipo de peça, condição e vendedora pelas chaves.
-- Anúncios do histórico não têm vendedora nem data de cadastro.
-- Cor e tamanho ficam aqui mesmo, como atributos da peça.

with pecas as (

    select * from {{ ref('int_roupas_padronizadas') }}

)

select
    -- chaves
    id_peca,
    md5(marca_padronizada)        as marca_id,
    id_vendedora,
    md5(tipo_peca)                as tipo_peca_id,
    md5(condicao_padronizada)     as condicao_id,

    -- de onde veio e quando
    origem,
    data_cadastro,
    cast(data_cadastro as date)   as dia_cadastro,

    -- descrição da peça
    nome_da_peca,
    grupo_cor,
    tamanho_padronizado,
    tamanho_numerico,
    sistema_tamanho,

    -- preços
    preco_com_desconto            as preco_venda,
    preco_sem_desconto            as preco_original,
    preco_sem_desconto - preco_com_desconto as desconto_valor,
    case
        when preco_sem_desconto > 0
            then round(100 * (1 - preco_com_desconto / preco_sem_desconto), 1)
    end                           as desconto_percentual,

    -- sinalizadores de qualidade
    preco_sem_desconto is not null                          as tem_preco_original,
    coalesce(preco_com_desconto > preco_sem_desconto, false) as preco_suspeito
from pecas
