"""
Camada Bronze do módulo Comercial.

Cópia crua das tabelas do Sapiens, sem nenhuma transformação de negócio.
Filtra apenas CODEMP = 1 (Aquário) e, onde aplicável, CODFIL = 1.

Arquivos:
    tabelas.py  : catálogo das 33 tabelas (PK, coluna de data, observações)
    extrator.py : motor genérico que lê o catálogo, monta a query certa
                  para cada tabela (full na 1ª carga, incremental de 60 dias
                  depois) e chama core.loader.carregar_bronze()
"""