{#
  Por padrão, o dbt junta o schema do profile com o schema da pasta
  (ficaria "public_staging"). Esta macro faz o dbt usar o nome
  configurado diretamente: os modelos de staging vão para o schema "staging".
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
