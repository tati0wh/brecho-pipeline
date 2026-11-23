{#
  Cria no banco a função public.corrigir_encoding(texto).

  O problema: parte dos textos foi salva em UTF-8, lida como se fosse
  Windows-1252 (ou Latin-1) e salva de novo. Assim, "Sandália" virou "SandÃ¡lia".

  A correção desfaz esse caminho: transforma o texto de volta nos bytes
  originais (convert_to) e lê esses bytes como UTF-8 (convert_from).

  Só tenta corrigir textos com os sinais típicos do problema: "Ã" e "Â"
  (letras acentuadas quebradas) ou "â" (aspas e apóstrofos curvos quebrados,
  como "Carterâ€™s"). Um "â" legítimo ("câmera") não vira UTF-8 válido,
  então a conversão falha e o texto original é mantido.
  Se a conversão falhar, devolve o texto original, sem quebrar o pipeline.
#}
{% macro criar_funcao_corrigir_encoding() %}
create or replace function public.corrigir_encoding(texto text)
returns text
language plpgsql
immutable
as $func$
begin
    if texto is null or texto !~ '[ÃÂâ]' then
        return texto;
    end if;

    begin
        return convert_from(convert_to(texto, 'WIN1252'), 'UTF8');
    exception when others then
        begin
            return convert_from(convert_to(texto, 'LATIN1'), 'UTF8');
        exception when others then
            return texto;
        end;
    end;
end;
$func$;
{% endmacro %}
