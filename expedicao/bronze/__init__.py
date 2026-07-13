"""
Camada Bronze do módulo Expedição.

Cópia crua das tabelas do Sapiens (mesmo servidor do Comercial/Produção/
Estoque/Laudos RMA), sem nenhuma transformação de negócio. Filtra
CODEMP = 1 (Aquário) e, onde aplicável, CODFIL = 1 -- mesma regra padrão
do projeto.

Arquivos:
    tabelas.py     : catálogo das 2 tabelas exclusivas da Expedição (1
                     com PK + 1 view sem PK, USU_V120EST -- sempre
                     full_reload, mesmo tratamento do USU_VZRASLAU no
                     Laudos RMA). Também documenta (sem duplicar a
                     definição) as 3 tabelas que a Expedição usa mas que
                     já são mantidas pelo Comercial -- não são
                     re-extraídas aqui.
    extrator.py    : motor genérico, mesmo padrão do Comercial/Produção/
                     Estoque/Laudos RMA.
    conferencia.py : compara COUNT(*) Bronze x Sapiens, tabela por
                     tabela.

Fora de escopo (não faz parte da Bronze): as leituras de
BIAQUARIO.USU_BVIACLIENTES/USU_VBIREPRESENTANTES no vbiexpedicao.py
legado são enriquecimento (nome cliente/vendedor) contra o schema
legado antigo -- isso é lógica de Prata, não de Bronze.
"""
