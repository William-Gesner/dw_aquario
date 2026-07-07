"""
Camada Bronze do módulo OPEX.

Cópia crua das tabelas do Sapiens (banco de Controladoria, servidor
separado do ERP principal), sem nenhuma transformação de negócio.

Diferente das demais áreas, filtra CODEMP IN (1, 50) -- exceção
documentada: o OPEX consolida duas razões sociais do mesmo grupo Aquário
(confirmado com o cliente em 07/07/2026). Nenhuma das 5 tabelas tem
CODFIL (confirmado via ALL_TAB_COLUMNS).

Arquivos:
    tabelas.py     : catálogo das 5 tabelas (PK, coluna de data, observações)
    extrator.py    : motor genérico -- lê do banco de Controladoria via
                     core.db.get_engine_controladoria() e grava no
                     DW_BRONZE via core.db.get_engine_bronze() (servidores
                     diferentes, sem DB LINK -- ver core/loader.py
                     carregar_bronze(engine_escrita=...))
    conferencia.py : compara COUNT(*) Bronze x Controladoria, tabela por
                     tabela
"""
