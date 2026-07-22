"""
Camada Prata do módulo Produção.

Lê exclusivamente da Bronze (DW_BRONZE) -- nunca do Sapiens direto.
Replica fielmente a regra de negócio do legado
(aquario/producao/extract/*.py), só trocando a origem, a nomenclatura das
tabelas e o corte de data (ver DATA_CORTE_PRODUCAO em
producao/config/settings.py -- 01/01/2021, decisão explícita do usuário
em 21/07/2026, diferente do corte de 01/01/2018 do legado).

7 tabelas (3 dimensões + 4 fatos), sufixo `_PRODUCAO` em todas -- já
existe DIM_PRODUTO no Comercial, com campos completamente diferentes.

Arquivos:
    tabelas.py                        : catálogo/documentação (nome novo x legado)
    dim_produto_producao.py           : upsert (CODEMP+CODPRO)
    dim_centro_custo_producao.py      : upsert (CODCCU+CODETG+CODCRE)
    dim_custo_padrao_producao.py      : full_reload (Excel -- TempoDisponivelCC.xlsx, aba CP)
    fat_paradas_producao.py           : full_reload
    fat_custo_cc_producao.py          : full_reload
    fat_utilizacao_meta_producao.py   : full_reload (Excel -- TempoDisponivelCC.xlsx, aba BD)
    fat_desempenho_producao.py        : full_reload (fato central, UNION ALL de 4 naturezas)

Ver dw_aquario/doc_nova_arquitetura.md, seção "Produção", para o
histórico completo das decisões desta área.
"""
