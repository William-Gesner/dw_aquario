"""
Catálogo das tabelas Sapiens que formam a camada Bronze do Estoque.

Cada entrada descreve:
    tabela        : nome exato da tabela no Sapiens. Na Bronze, fica com
                    o MESMO nome (cópia crua, sem transformação).
    chaves_pk     : PK real, validada via ALL_TAB_COLUMNS/ALL_CONS_COLUMNS
                    em 13/07/2026.
    coluna_data   : coluna usada no filtro de janela de 60 dias na carga
                    incremental. None = sem coluna de auditoria confiável
                    -- tabela sempre via full_reload.
    tem_codemp    : se True, a query filtra pela coluna de empresa real.
    coluna_codemp : nome real da coluna de empresa. Todas as tabelas novas
                    do Estoque usam "CODEMP" puro (sem prefixo USU_,
                    mesmo padrão do Comercial/Produção).
    tem_codfil    : se True, filtra também pela coluna de filial real.
    coluna_codfil : nome real da coluna de filial ("CODFIL" quando
                    aplicável).
    observacao    : contexto levantado na validação.

REGRA DE EMPRESA/FILIAL: igual ao resto do projeto -- CODEMP = 1 e
CODFIL = 1 sempre (ver estoque.config.settings). Sem exceção aqui
(diferente do OPEX). ATENÇÃO -- isso é o escopo de NEGÓCIO da empresa,
não uma instrução para a Bronze filtrar CODFIL na extração: ver Regra 6
do doc_nova_arquitetura.md e a correção de 17/07/2026 em E420IPO/E420OCP
abaixo (tem_codfil virou False -- o legado nunca fixava filial nessas
duas tabelas).

TABELAS COMPARTILHADAS COM O COMERCIAL -- NÃO EXTRAÍDAS AQUI:
    O Estoque também depende de E075DER, E075PRO, E095FOR (usadas em
    vbicompras.py/vbiestoque.py legado). Já são mantidas atualizadas pelo
    comercial/bronze/tabelas.py -- extrair de novo aqui seria trabalho
    redobrado. Definição real fica só no catálogo do Comercial. Listadas
    abaixo só para rastreio de dependência -- ver
    TABELAS_COMPARTILHADAS_COM_COMERCIAL.

TABELAS COMPARTILHADAS COM A PRODUÇÃO -- NÃO EXTRAÍDAS AQUI:
    O Estoque também depende de E210MVP (usada em vbiestoque.py legado
    para posição/movimentação). Já é mantida atualizada pelo
    producao/bronze/tabelas.py. Definição real fica só no catálogo da
    Produção -- ver TABELAS_COMPARTILHADAS_COM_PRODUCAO.

TABELA EXCLUÍDA -- FORA DE ESCOPO (EXCEL):
    vbicustopadrao.py legado lê Z:\\Dados\\TempoDisponivelCC.xlsx (aba
    'CP') -- por decisão de 07/07/2026, arquivos Excel ficam FORA da
    Bronze. A Prata do Estoque continua lendo o Excel direto, como no
    legado.
"""

# ----- CATÁLOGO DE TABELAS (EXCLUSIVAS DO ESTOQUE) -----

TABELAS = [

    {
        "tabela": "E420IPO",
        "chaves_pk": ["CODEMP", "CODFIL", "NUMOCP", "SEQIPO"],
        "coluna_data": None,
        "tem_codemp": True,
        "coluna_codemp": "CODEMP",
        "tem_codfil": False,
        "coluna_codfil": "CODFIL",
        "observacao": (
            "Item da ordem de compra (fato principal do vbicompras.py "
            "legado). PK real validada em 13/07/2026 via ALL_CONS_COLUMNS "
            "-- inclui SEQIPO (sequência do item), que o JOIN do legado "
            "não usava (unia só por NUMOCP+CODEMP+CODFIL). Sem coluna de "
            "auditoria confiável (não existe DATALT/HORALT nesta tabela) "
            "-- DATENT/DATGER/DATVLT são datas de negócio (previsão de "
            "entrega, geração, validade), podem não mudar quando outros "
            "campos (QTDREC, QTDABE, SITIPO) são atualizados em um "
            "recebimento parcial -- mesmo risco já documentado para o "
            "QTDABE do E120PED no Comercial. full_reload sempre. "
            "CORRIGIDO em 17/07/2026: tem_codfil virou False -- "
            "vbicompras.py legado (WHERE T0.SITIPO IN ('1','2')) não tem "
            "NENHUM filtro de CODEMP/CODFIL; CODFIL só aparece no JOIN "
            "com E420OCP (T0.CODFIL = T1.CODFIL, casamento dinâmico, "
            "nunca fixado em 1). Mesmo padrão de bug já corrigido no "
            "Comercial -- ver Regra 6 do doc_nova_arquitetura.md."
        ),
    },
    {
        "tabela": "E420OCP",
        "chaves_pk": ["CODEMP", "CODFIL", "NUMOCP"],
        "coluna_data": None,
        "tem_codemp": True,
        "coluna_codemp": "CODEMP",
        "tem_codfil": False,
        "coluna_codfil": "CODFIL",
        "observacao": (
            "Cabeçalho da ordem de compra. PK real confirmada em "
            "13/07/2026 (CODEMP+CODFIL+NUMOCP). Sem coluna de auditoria "
            "confiável -- DATEMI é a data de emissão (fixa na criação), "
            "DATFEC só é preenchida no fechamento e não necessariamente "
            "muda em toda atualização (ex.: SITOCP mudando por "
            "recebimento parcial sem fechar a OC). full_reload sempre. "
            "CORRIGIDO em 17/07/2026: mesmo motivo do E420IPO -- "
            "vbicompras.py legado nunca fixa CODFIL, só casa "
            "dinamicamente com E420IPO no JOIN."
        ),
    },
    {
        "tabela": "E700CMM",
        "chaves_pk": ["CODEMP", "CODMOD", "CODETG", "SEQMOD"],
        "coluna_data": "DATALT",
        "tem_codemp": True,
        "coluna_codemp": "CODEMP",
        "tem_codfil": False,
        "observacao": (
            "Estrutura de componentes SKD (fato do vbiskd.py legado). "
            "ATENÇÃO: o legado usava chaves_merge=['CODPRO','CODCMP'] "
            "(CODPRO ali é alias de CODMOD) -- NÃO é a PK real. PK real "
            "validada em 13/07/2026 via ALL_CONS_COLUMNS: "
            "CODEMP+CODMOD+CODETG+SEQMOD (inclui estágio e sequência do "
            "componente, que o legado ignorava por completo). Mesmo tipo "
            "de erro já cometido com USU_T101MET no Comercial -- nunca "
            "inferir PK pelo merge/JOIN do legado. Tem DATALT (coluna de "
            "auditoria real, NOT NULL) -- incremental via janela de 60 "
            "dias. Não tem coluna CODFIL."
        ),
    },

]

# ----- VALIDAÇÃO -----

assert len(TABELAS) == 3, f"Esperado 3 tabelas no catálogo, encontrado {len(TABELAS)}"


# ----- TABELAS COMPARTILHADAS (NÃO EXTRAÍDAS AQUI) -----

# Ver docstring do módulo. Definição real fica em
# comercial/bronze/tabelas.py -- aqui é só documentação de dependência.
TABELAS_COMPARTILHADAS_COM_COMERCIAL = [
    "E075DER",
    "E075PRO",
    "E095FOR",
]

# Ver docstring do módulo. Definição real fica em
# producao/bronze/tabelas.py -- aqui é só documentação de dependência.
TABELAS_COMPARTILHADAS_COM_PRODUCAO = [
    "E210MVP",
]


# ----- FUNÇÃO AUXILIAR -----

def buscar_tabela(nome: str) -> dict:
    """Retorna a configuração de uma tabela do catálogo pelo nome exato."""
    for t in TABELAS:
        if t["tabela"] == nome:
            return t
    raise KeyError(f"Tabela '{nome}' não encontrada no catálogo da Bronze Estoque.")
