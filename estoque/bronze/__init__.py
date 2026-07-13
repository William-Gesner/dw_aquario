"""
Camada Bronze do módulo Estoque.

Cópia crua das tabelas do Sapiens (mesmo servidor do Comercial/Produção/
Laudos RMA), sem nenhuma transformação de negócio. Filtra CODEMP = 1
(Aquário) e, onde aplicável, CODFIL = 1 -- mesma regra padrão do projeto.

Arquivos:
    tabelas.py     : catálogo das 3 tabelas exclusivas do Estoque. Também
                     documenta (sem duplicar a definição) as 4 tabelas que
                     o Estoque usa mas que já são mantidas pelo Comercial
                     (E075DER, E075PRO, E095FOR) e pela Produção (E210MVP)
                     -- não são re-extraídas aqui.
    extrator.py    : motor genérico, mesmo padrão do Comercial/Produção/
                     Laudos RMA.
    conferencia.py : compara COUNT(*) Bronze x Sapiens, tabela por tabela.

Nenhum arquivo Excel (TempoDisponivelCC.xlsx, aba CP -- usado no
vbicustopadrao.py legado) entra nesta camada -- mesma decisão de escopo
do Laudos RMA/Produção: só tabelas do Sapiens migram agora.
"""
