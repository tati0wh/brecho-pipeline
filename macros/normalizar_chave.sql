{#
  Gera uma "chave de comparação" para textos livres:
  minúsculas, sem acentos, e qualquer coisa que não seja letra ou número
  vira um espaço só.

      "Maria Filó"  -> "maria filo"
      "M. Officer"  -> "m officer"
      "H&M"         -> "h m"

  Duas grafias com a mesma chave são tratadas como o mesmo valor.
#}
{% macro normalizar_chave(coluna) -%}
    nullif(trim(regexp_replace(lower(unaccent({{ coluna }})), '[^a-z0-9]+', ' ', 'g')), '')
{%- endmacro %}
