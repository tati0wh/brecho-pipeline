-- Investigação dos itens 61 a 81 da revisão de marcas (rodada 2).
-- Traz o registro completo de cada peça dessas marcas, para decidir
-- se a sugestão do fuzzy matching está certa, errada ou indeterminada.
--
-- Dica: clique numa célula da coluna descricao e leia o texto completo
-- no painel "Valor" do DBeaver.

SELECT
    marca_original,
    nome_da_peca,
    tipo_peca,
    condicao_padronizada,
    tamanho_original,
    cores_original,
    preco_com_desconto,
    preco_sem_desconto,
    descricao
FROM intermediate.int_roupas_padronizadas
WHERE trim(regexp_replace(lower(unaccent(marca_original)), '[^a-z0-9]+', ' ', 'g')) IN (
    'forever 18',                                   -- 61: sugestão Forever 21
    'dress to kill',                                -- 62: sugestão Dress To
    'expressao',                                    -- 63: sugestão Express
    'seven7',                                       -- 64: sugestão Seven
    'um mais um',                                   -- 65: sugestão Mais um
    'a animale',                                    -- 66: sugestão Animale (18 peças)
    'canal 1',                                      -- 67: sugestão Canal
    'x green', 'loja green',                        -- 68: sugestão Green
    'forever',                                      -- 69: sugestão Forever 21
    'by express', 'express tricot', 'express stretch', -- 70: sugestão Express
    'riachuelo alk',                                -- 71: sugestão Riachuelo (7 peças)
    'mara',                                         -- 72: sugestão Mara Mac
    'place',                                        -- 73: sugestão My Place
    'lolita',                                       -- 74: sugestão Lolitta
    'colins',                                       -- 75: sugestão Collins
    'dress',                                        -- 76: sugestão Dress To
    'cholet club',                                  -- 77: sugestão Cholet
    'marcia g', 'garcia',                           -- 78: sugestão Maria Garcia
    'enjoy mix',                                    -- 79: sugestão Enjoy
    'miss carmim',                                  -- 80: sugestão Carmim
    'leelog'                                        -- 81: sugestão Leeloo
)
ORDER BY marca_original, nome_da_peca;
