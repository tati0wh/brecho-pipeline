-- Staging: limpeza técnica, sem regras de negócio.
-- Aqui só corrigimos encoding, espaços, tipos e vazios.
-- A padronização de marcas, tamanhos e cores fica para a camada seguinte.

with origem as (

    select * from {{ source('raw', 'roupas_usadas') }}

),

texto_corrigido as (

    select
        unnamed_0,
        public.corrigir_encoding(marca)              as marca,
        public.corrigir_encoding(nome_da_peca)       as nome_da_peca,
        preco_com_desconto,
        preco_sem_desconto,
        public.corrigir_encoding(descricao)          as descricao,
        public.corrigir_encoding(tamanho)            as tamanho,
        public.corrigir_encoding(condicao)           as condicao,
        public.corrigir_encoding(cores)              as cores,
        _arquivo_origem,
        _linha_origem,
        _carregado_em
    from origem

),

limpo as (

    select
        cast(unnamed_0 as integer)                                     as id_peca,

        -- textos curtos: troca quebras de linha e espaços repetidos por um espaço só
        nullif(trim(regexp_replace(marca, '\s+', ' ', 'g')), '')        as marca,
        nullif(trim(regexp_replace(nome_da_peca, '\s+', ' ', 'g')), '') as nome_da_peca,
        nullif(trim(regexp_replace(tamanho, '\s+', ' ', 'g')), '')      as tamanho,
        nullif(trim(regexp_replace(condicao, '\s+', ' ', 'g')), '')     as condicao,
        nullif(trim(regexp_replace(cores, '\s+', ' ', 'g')), '')        as cores,

        -- descrição: mantém as quebras de linha (elas organizam o texto), só tira as pontas
        nullif(trim(descricao), '')                                     as descricao,

        -- preços: a vírgula é usada como decimal E como milhar ("1,000,00" = mil reais).
        -- Por isso, só a última vírgula é decimal: as anteriores são removidas,
        -- e a última vira ponto. Depois o texto vira número.
        cast(nullif(replace(regexp_replace(trim(preco_com_desconto), ',(?=.*,)', '', 'g'), ',', '.'), '') as numeric(10, 2)) as preco_com_desconto,
        cast(nullif(replace(regexp_replace(trim(preco_sem_desconto), ',(?=.*,)', '', 'g'), ',', '.'), '') as numeric(10, 2)) as preco_sem_desconto,

        _arquivo_origem,
        _linha_origem,
        _carregado_em
    from texto_corrigido

)

select * from limpo
