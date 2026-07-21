"""
Camada Prata do módulo OPEX.

Lê exclusivamente da Bronze (DW_BRONZE) -- nunca do Sapiens/Controladoria
direto. Replica fielmente a regra de negócio do legado
(aquario/opex/extract/vbiopex.py), só trocando a origem e o nome da
tabela de destino.

Diferente da Bronze do OPEX (que precisa de 2 engines -- Controladoria
para leitura, servidor principal para escrita, sem DB LINK entre eles),
a Prata só precisa de 1 engine: get_engine_prata() -- porque a origem
agora é a Bronze, que já está no mesmo servidor físico da Prata (só
schema diferente). O usuário DW_PRATA já tem SELECT sobre DW_BRONZE
(mesmo padrão usado pelas outras áreas, ex.: comercial/prata/fat_metas.py).

Arquivos:
    tabelas.py               : catálogo/documentação da tabela nova x legado
    fat_orcamento_opex.py    : query + carga de FAT_ORCAMENTO_OPEX (era
                                USU_VBIAOPEX_ORCAMENTO no legado)

Ver dw_aquario/doc_nova_arquitetura.md, seção "OPEX", para o histórico
completo das decisões desta área.
"""
