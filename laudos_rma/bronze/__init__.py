"""
Camada Bronze do módulo Laudos RMA.

Cópia crua das tabelas do Sapiens (mesmo servidor do Comercial), sem
nenhuma transformação de negócio. Filtra CODEMP = 1 (Aquário) e, onde
aplicável, CODFIL = 1 -- mesma regra padrão do projeto.

Arquivos:
    tabelas.py  : catálogo das 9 tabelas exclusivas do Laudos RMA (8 com
                  PK + 1 view sem PK, USU_VZRASLAU -- sempre full_reload).
                  Também documenta (sem duplicar a definição) as 10
                  tabelas que o Laudos RMA usa mas que já são mantidas
                  pelo Comercial -- não são re-extraídas aqui.
    extrator.py : motor genérico, mesmo padrão do Comercial/OPEX.

Nenhum arquivo Excel (IndiceRMA.xlsx, DefeitosProdutosRMA.xlsx) entra
nesta camada -- decisão de escopo confirmada em 07/07/2026: só tabelas do
Sapiens migram agora. Os Excel continuam sendo lidos direto pela Prata,
como no legado.
"""
