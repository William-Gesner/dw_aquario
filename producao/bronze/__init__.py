"""
Camada Bronze do módulo Produção.

Cópia crua das tabelas do Sapiens (mesmo servidor do Comercial/Laudos
RMA), sem nenhuma transformação de negócio. Filtra CODEMP = 1 (Aquário)
e, onde aplicável, CODFIL = 1 -- mesma regra padrão do projeto.

Arquivos:
    tabelas.py     : catálogo das 16 tabelas exclusivas da Produção.
                     Também documenta (sem duplicar a definição) as 4
                     tabelas que a Produção usa mas que já são mantidas
                     pelo Comercial -- não são re-extraídas aqui.
    extrator.py    : motor genérico, mesmo padrão do Comercial/Laudos RMA.
    conferencia.py : compara COUNT(*) Bronze x Sapiens, tabela por tabela.

Nenhum arquivo Excel (TempoDisponivelCC.xlsx) entra nesta camada --
mesma decisão de escopo do Laudos RMA: só tabelas do Sapiens migram
agora.
"""
