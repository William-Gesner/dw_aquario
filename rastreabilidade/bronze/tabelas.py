"""
Catálogo das tabelas Sapiens que formam a camada Bronze da
Rastreabilidade.

Cada entrada descreve:
    tabela        : nome exato da tabela no Sapiens. Na Bronze, fica com
                    o MESMO nome (cópia crua, sem transformação).
    chaves_pk     : PK real, validada via ALL_TAB_COLUMNS/ALL_CONS_COLUMNS
                    em 14/07/2026.
    coluna_data   : coluna usada no filtro de janela de 60 dias na carga
                    incremental.
    tem_codemp    : se True, a query filtra pela coluna de empresa real.
    coluna_codemp : nome real da coluna de empresa. A única tabela nova
                    desta área usa o prefixo USU_ (USU_CODEMP) -- mesmo
                    padrão do Laudos RMA, diferente do Comercial/Produção
                    (CODEMP puro).
    tem_codfil    : se True, filtra também pela coluna de filial real.
    coluna_codfil : nome real da coluna de filial (USU_CODFIL).
    observacao    : contexto levantado na validação.

REGRA DE EMPRESA/FILIAL: igual ao resto do projeto -- CODEMP = 1 e
CODFIL = 1 sempre (ver rastreabilidade.config.settings). Sem exceção
aqui (diferente do OPEX).

TABELAS COMPARTILHADAS COM O COMERCIAL -- NÃO EXTRAÍDAS AQUI:
    A Rastreabilidade também depende de E140IPV, E140NFV, E075PRO,
    E026RAM, E085CLI, E090REP, E120IPD (usadas em vbirastreabilidade.py
    legado). Já são mantidas atualizadas pelo comercial/bronze/tabelas.py
    -- extrair de novo aqui seria trabalho redobrado. Definição real
    fica só no catálogo do Comercial. Listadas abaixo só para rastreio
    de dependência -- ver TABELAS_COMPARTILHADAS_COM_COMERCIAL.

TABELA COMPARTILHADA COM O LAUDOS RMA -- NÃO EXTRAÍDA AQUI:
    A Rastreabilidade também depende de USU_VZRASLAU (view sem PK,
    chaves_pk=None), já prevista desde a migração do Laudos RMA (ver
    laudos_rma/bronze/tabelas.py -- comentário de 07/07/2026 já citava
    esse reaproveitamento futuro). Já é mantida pelo
    laudos_rma/bronze/extrator.py -- ver
    TABELAS_COMPARTILHADAS_COM_LAUDOS_RMA.

FORA DE ESCOPO -- NÃO É TABELA SAPIENS:
    vbirastreabilidade.py legado também lê MetaMix.xlsx (aba 'Cadastro')
    e faz merge em Python pelos campos MIX/ORIGEM. Por decisão de
    07/07/2026, arquivos Excel ficam FORA da Bronze -- a Prata da
    Rastreabilidade continua lendo o Excel direto, como no legado.
"""

# ----- CATÁLOGO DE TABELAS (EXCLUSIVAS DA RASTREABILIDADE) -----

TABELAS = [

    {
        "tabela": "USU_T140QRC",
        "chaves_pk": [
            "USU_CODEMP", "USU_CODFIL", "USU_CODSNF",
            "USU_NUMNFV", "USU_SEQIPV", "USU_CODBAR",
        ],
        "coluna_data": "USU_DATGER",
        "tem_codemp": True,
        "coluna_codemp": "USU_CODEMP",
        "tem_codfil": True,
        "coluna_codfil": "USU_CODFIL",
        "observacao": (
            "Log de geração de código de barras/QR por item de nota "
            "fiscal (fato principal do vbirastreabilidade.py legado). PK "
            "real validada em 14/07/2026 via ALL_CONS_COLUMNS: 6 colunas "
            "(USU_CODEMP+USU_CODFIL+USU_CODSNF+USU_NUMNFV+USU_SEQIPV+"
            "USU_CODBAR) -- o legado não precisava validar essa PK "
            "porque só usava a tabela num LEFT JOIN de igualdade (WHERE), "
            "nunca fez upsert nela. Volume grande: 2.698.648 linhas -- "
            "MAIOR que o E120IPD do Comercial (1,4 milhão) -- 1ª carga "
            "via full_reload_streaming (automático, ver "
            "core/loader.py carregar_bronze()). coluna_data=USU_DATGER "
            "segue a MESMA convenção já usada nas tabelas grandes/"
            "transacionais do Comercial (E120IPD, E140IPV, E140NFV, "
            "todas com coluna_data='DATGER') -- é log de geração "
            "(insere e não altera depois, PK já inclui o próprio código "
            "gerado), não uma dimensão que muda com o tempo. ATENÇÃO: "
            "USU_DATGER é NULLABLE (confirmado via ALL_TAB_COLUMNS) -- se "
            "alguma linha nova chegar com essa coluna NULL, ela nunca "
            "vai satisfazer o filtro incremental (>= SYSDATE-60) e ficará "
            "de fora da Bronze permanentemente (mesmo tipo de risco já "
            "documentado pro E900EOQ na Produção, mas sem sentinela "
            "conhecida aqui). Se a conferência mostrar divergência "
            "persistente, checar primeiro se há linhas com USU_DATGER "
            "NULL no Sapiens que não estejam na Bronze."
        ),
    },

]

# ----- VALIDAÇÃO -----

assert len(TABELAS) == 1, f"Esperado 1 tabela no catálogo, encontrado {len(TABELAS)}"


# ----- TABELAS COMPARTILHADAS (NÃO EXTRAÍDAS AQUI) -----

# Ver docstring do módulo. Definição real fica em
# comercial/bronze/tabelas.py -- aqui é só documentação de dependência.
TABELAS_COMPARTILHADAS_COM_COMERCIAL = [
    "E140IPV",
    "E140NFV",
    "E075PRO",
    "E026RAM",
    "E085CLI",
    "E090REP",
    "E120IPD",
]

# Ver docstring do módulo. Definição real fica em
# laudos_rma/bronze/tabelas.py -- aqui é só documentação de dependência.
TABELAS_COMPARTILHADAS_COM_LAUDOS_RMA = [
    "USU_VZRASLAU",
]


# ----- FUNÇÃO AUXILIAR -----

def buscar_tabela(nome: str) -> dict:
    """Retorna a configuração de uma tabela do catálogo pelo nome exato."""
    for t in TABELAS:
        if t["tabela"] == nome:
            return t
    raise KeyError(f"Tabela '{nome}' não encontrada no catálogo da Bronze Rastreabilidade.")
