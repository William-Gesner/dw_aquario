"""
Camada Prata do módulo Rastreabilidade.

Lê exclusivamente da Bronze (DW_BRONZE) -- nunca do Sapiens direto.
Replica fielmente a regra de negócio do legado
(aquario/rastreabilidade/extract/vbirastreabilidade.py), só trocando a
origem e o nome da tabela de destino.

Única tabela desta área -- o legado nunca teve dimensão separada (tudo
denormalizado num único resultado, mesmo padrão do OPEX).

Arquivos:
    tabelas.py               : catálogo/documentação da tabela nova x legado
    fat_rastreabilidade.py   : query + carga de FAT_RASTREABILIDADE (era
                                USU_VBIARAST_RASTREABILIDADE no legado)

Ver dw_aquario/doc_nova_arquitetura.md, seção "Rastreabilidade", para o
histórico completo das decisões desta área.
"""
