{#
  Macros de limpeza técnica, usadas por todos os modelos de staging.
  Assim, anúncios do CSV histórico e do marketplace passam exatamente
  pela mesma limpeza, escrita num lugar só.
#}

{# Textos curtos (marca, nome, tamanho...): corrige encoding, troca quebras
   de linha e espaços repetidos por um espaço só, e texto vazio vira nulo. #}
{% macro limpar_texto_curto(coluna) -%}
    nullif(trim(regexp_replace(public.corrigir_encoding({{ coluna }}), '\s+', ' ', 'g')), '')
{%- endmacro %}

{# Textos longos (descrição): corrige encoding e só tira os espaços das pontas,
   mantendo as quebras de linha, que organizam o texto. #}
{% macro limpar_texto_longo(coluna) -%}
    nullif(trim(public.corrigir_encoding({{ coluna }})), '')
{%- endmacro %}

{# Preços: a vírgula é usada como decimal E como milhar ("1,000,00" = mil reais).
   Só a última vírgula é decimal: as anteriores são removidas, a última vira
   ponto, e o texto vira número. #}
{% macro converter_preco(coluna) -%}
    cast(nullif(replace(regexp_replace(trim({{ coluna }}), ',(?=.*,)', '', 'g'), ',', '.'), '') as numeric(10, 2))
{%- endmacro %}
