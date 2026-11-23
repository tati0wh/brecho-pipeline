-- Aplica todas as regras de negócio sobre a staging.
-- Para cada campo padronizado guardamos o valor original e o método usado,
-- assim qualquer decisão pode ser explicada e revisada.

{{ config(materialized='table') }}

with pecas as (

    select
        *,
        {{ normalizar_chave('marca') }}        as marca_chave,
        {{ normalizar_chave('condicao') }}     as condicao_chave,
        {{ normalizar_chave('tamanho') }}      as tamanho_chave,
        ' ' || coalesce({{ normalizar_chave('nome_da_peca') }}, '') || ' ' as nome_busca,
        ' ' || coalesce({{ normalizar_chave('descricao') }}, '') || ' '    as descricao_busca
    from {{ ref('stg_roupas_usadas') }}

),

base as (

    select
        p.*,
        coalesce(mar.marca_padronizada, 'Não informada') as marca_padronizada,
        coalesce(mar.metodo, 'nao_informado')            as metodo_marca
    from pecas p
    left join {{ ref('int_marcas') }} mar
        on mar.marca_chave = p.marca_chave

)

select
    b.id_peca,
    b.nome_da_peca,

    -- tipo de peça
    tp.tipo_peca,
    tp.metodo_tipo_peca,
    tp.palavra_gatilho_tipo,

    -- marca
    b.marca                                     as marca_original,
    b.marca_padronizada,
    b.metodo_marca,
    inf.marca_inferida,
    inf.fonte_inferencia                        as fonte_marca_inferida,

    -- condição
    b.condicao                                  as condicao_original,
    con.condicao_padronizada,
    con.ordem_conservacao,

    -- tamanho
    b.tamanho                                   as tamanho_original,
    tam.tamanho_padronizado,
    tam.tamanho_numerico,
    case
        when b.tamanho is null                                 then 'Não informado'
        when tam.tamanho_chave is null                         then 'Não mapeado'
        when tam.tipo_rotulo = 'unico'                         then 'Único'
        when tp.tipo_peca = 'Sapato'                           then 'Calçado'
        when tam.tipo_rotulo in ('meses', 'anos', 'recem_nascido') then 'Infantil'
        when tam.tipo_rotulo = 'numero' and tam.tamanho_numerico <= 16 then 'Infantil'
        when tam.tipo_rotulo = 'numero'                        then 'Adulto (numeração)'
        when tam.tipo_rotulo = 'letra'                         then 'Adulto (letras)'
    end                                         as sistema_tamanho,

    -- cor
    b.cores                                     as cores_original,
    cor.grupo_cor,
    cor.metodo_cor,
    cor.palavras_gatilho_cor,

    b.descricao,
    b.preco_com_desconto,
    b.preco_sem_desconto,

    b._arquivo_origem,
    b._linha_origem,
    b._carregado_em
from base b
left join {{ ref('int_tipo_peca') }} tp
    on tp.id_peca = b.id_peca
left join {{ ref('int_cores') }} cor
    on cor.id_peca = b.id_peca
left join {{ ref('map_condicao') }} con
    on con.condicao_chave = b.condicao_chave
left join {{ ref('map_tamanho') }} tam
    on tam.tamanho_chave = b.tamanho_chave
-- marca inferida: só para peças sem marca; o nome vale mais que a descrição,
-- e termos mais longos ("tommy hilfiger") ganham de termos curtos
left join lateral (
    select
        mi.marca_inferida,
        case when b.nome_busca like '% ' || mi.termo_chave || ' %' then 'nome' else 'descricao' end as fonte_inferencia
    from {{ ref('map_marca_inferida') }} mi
    where b.marca_padronizada = 'Sem marca'
      and (b.nome_busca like '% ' || mi.termo_chave || ' %'
           or b.descricao_busca like '% ' || mi.termo_chave || ' %')
    order by (b.nome_busca like '% ' || mi.termo_chave || ' %') desc, length(mi.termo_chave) desc
    limit 1
) inf on true
