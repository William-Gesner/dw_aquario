"""
Camada Bronze do módulo Rastreabilidade.

Cópia crua das tabelas do Sapiens (mesmo servidor do Comercial/Produção/
Estoque/Expedição/Laudos RMA), sem nenhuma transformação de negócio.
Filtra CODEMP = 1 (Aquário) e, onde aplicável, CODFIL = 1 -- mesma regra
padrão do projeto.

Arquivos:
    tabelas.py     : catálogo de 1 única tabela exclusiva da
                     Rastreabilidade (USU_T140QRC). Também documenta (sem
                     duplicar a definição) as 7 tabelas que já são
                     mantidas pelo Comercial e a 1 (USU_VZRASLAU) já
                     mantida pelo Laudos RMA -- não são re-extraídas
                     aqui.
    extrator.py    : motor genérico, mesmo padrão do Comercial/Produção/
                     Estoque.
    conferencia.py : compara COUNT(*) Bronze x Sapiens.

Fora de escopo (não faz parte da Bronze): o merge com MetaMix.xlsx
(campos MIX/ORIGEM) no vbirastreabilidade.py legado é enriquecimento via
Excel -- mesma decisão de escopo já aplicada em Laudos RMA/Produção/
Estoque: só tabelas do Sapiens migram agora.
"""
