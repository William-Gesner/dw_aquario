"""
Catálogo das 5 tabelas Sapiens (banco de Controladoria) que formam a
camada Bronze do OPEX.

Diferente das demais áreas, a origem NÃO é o ERP principal -- é um
servidor Oracle separado ("Controladoria", 172.16.0.123), acessado via
core.db.get_engine_controladoria(). O schema de origem lá também se
chama SAPIENS.

Cada entrada descreve:
    tabela        : nome exato da tabela no Sapiens (Controladoria). Na
                    Bronze, fica com o MESMO nome (cópia crua, sem
                    transformação).
    chaves_pk     : PK real, validada via ALL_CONSTRAINTS/ALL_CONS_COLUMNS
                    em 07/07/2026 -- NÃO inferida da query legada (ver
                    observação de USU_T650CUS/USU_T650ORC abaixo, onde a
                    PK real diverge do JOIN usado na Prata legada).
    coluna_data   : coluna usada no filtro de janela de 60 dias na carga
                    incremental. Candidato DATALT/USU_DATALT em todas as
                    5 -- mesma convenção de auditoria já vista em outras
                    tabelas do Sapiens (data de alteração).
    tem_codemp    : se True, a query filtra pela coluna de empresa
                    (CODEMP_AQUARIO_OPEX = (1, 50) -- ver
                    opex.config.settings). Se False, tabela global no
                    Sapiens, sem essa coluna (confirmado via
                    ALL_TAB_COLUMNS em 07/07/2026).
    coluna_codemp : nome REAL da coluna de empresa -- varia entre "CODEMP"
                    (E044CCU) e "USU_CODEMP" (USU_T650CUS/USU_T650ORC).
    observacao    : contexto levantado na validação.

Nenhuma das 5 tabelas tem coluna de filial (confirmado via ALL_TAB_COLUMNS
em 07/07/2026) -- por isso não existe tem_codfil/coluna_codfil aqui,
diferente do catálogo do Comercial.

Estratégia de carga (ver core/loader.py -> carregar_bronze()):
    1ª carga          -> full, filtrando a coluna de empresa real quando
                         tem_codemp = True. Sem filtro quando tem_codemp
                         = False.
    cargas seguintes  -> incremental (MERGE via staging -- ver
                         upsert_cross_servidor() em core/loader.py),
                         janela de 60 dias pela coluna_data.

REGRA DE EMPRESA — EXCEÇÃO DOCUMENTADA (confirmado com o cliente em
07/07/2026): diferente das demais áreas (CODEMP = 1 sempre), o OPEX
consolida DUAS razões sociais do grupo Aquário -- CODEMP IN (1, 50).
"""

# ----- CATÁLOGO DE TABELAS -----

TABELAS = [

    {
        "tabela": "USU_T650ORC",
        "chaves_pk": ["USU_CODEMP", "USU_MESANO", "USU_CTADRE", "USU_CODCCU"],
        "coluna_data": "USU_DATALT",
        "tem_codemp": True,
        "coluna_codemp": "USU_CODEMP",
        "observacao": (
            "Orçamento. PK real validada via ALL_CONS_COLUMNS em "
            "07/07/2026 -- NÃO inclui USU_CODMPC, mesmo essa coluna "
            "existindo e sendo usada no JOIN/filtro da Prata legada "
            "(vbiopex.py). Usar a PK real (4 colunas) no MERGE, não as "
            "colunas do JOIN legado."
        ),
    },
    {
        "tabela": "USU_T650CUS",
        "chaves_pk": ["USU_CODEMP", "USU_MESANO", "USU_CODMPC", "USU_CTADRE", "USU_CTAEMP", "USU_CODCCU"],
        "coluna_data": "USU_DATALT",
        "tem_codemp": True,
        "coluna_codemp": "USU_CODEMP",
        "observacao": (
            "Realizado. PK real validada via ALL_CONS_COLUMNS em "
            "07/07/2026 -- tem 6 colunas, incluindo USU_CTAEMP, que o "
            "JOIN da Prata legada (vbiopex.py) NÃO usava para casar com "
            "USU_T650ORC (usava só 5 colunas, sem USU_CTAEMP). Pode ser "
            "motivo de fanout/soma incorreta no SUM(USU_SALMES) da Prata "
            "legada -- investigar quando migrarmos a Prata do OPEX, não é "
            "problema da Bronze (aqui usamos a PK real de 6 colunas)."
        ),
    },
    {
        "tabela": "E044CCU",
        "chaves_pk": ["CODEMP", "CODCCU"],
        "coluna_data": None,
        "tem_codemp": True,
        "coluna_codemp": "CODEMP",
        "observacao": (
            "Centros de custo. A query legada não filtrava CODEMP "
            "explicitamente nesta tabela (só herdava via JOIN com "
            "USU_T650ORC) -- na Bronze filtramos CODEMP IN (1,50) "
            "explicitamente, para garantir que os centros de custo das "
            "duas empresas fiquem disponíveis para a Prata. MESMO NOME "
            "que a tabela do catálogo da Produção -- as duas gravam na "
            "MESMA DW_BRONZE.E044CCU (schema único). CONFIRMADO em "
            "18/07/2026: os dois servidores têm o dado espelhado (a "
            "contagem por CODEMP bate 100% nos dois lados, 12 empresas). "
            "Ver observação completa em producao/bronze/tabelas.py. "
            "CORRIGIDO em 18/07/2026 (2): coluna_data virou None -- DATALT "
            "fica NULL em linha nova (364 linhas confirmadas via "
            "auditoria, mesmo número nos dois servidores) e a tabela NÃO "
            "tem nenhuma outra coluna de data (sem DATGER/HORGER "
            "equivalente, confirmado via amostra de linhas) -- sem "
            "fallback possível, igual ao caso do E085CLI no Comercial. "
            "Tabela pequena (~1.300 linhas no universo completo), custo "
            "de reler tudo a cada ciclo é desprezível."
        ),
    },
    {
        "tabela": "E043PCM",
        "chaves_pk": ["CODMPC", "CTARED"],
        "coluna_data": "DATALT",
        "coluna_data_fallback": "DATGER",
        "tem_codemp": False,
        "coluna_codemp": None,
        "observacao": (
            "Plano de contas. Tabela global -- sem CODEMP (confirmado via "
            "ALL_TAB_COLUMNS em 07/07/2026). CORRIGIDO em 18/07/2026: "
            "DATALT fica NULL em linha nova (94% da tabela -- 290.752 de "
            "310.072 linhas -- confirmado via auditoria; a maioria das "
            "contas nunca é editada depois de criada). Achado via "
            "conferência da Prata: 1 conta gerada em 18/07/2026 (junto "
            "com um cliente novo) nunca apareceu na Bronze porque DATALT "
            "nunca é preenchido na criação, só numa edição futura -- linha "
            "ficava fora da janela de 60 dias pra sempre. "
            "coluna_data_fallback='DATGER' faz o filtro incremental virar "
            "NVL(DATALT, DATGER) -- confirmado que DATGER nunca é NULL "
            "junto com DATALT (0 linhas com os dois nulos). Mesmo "
            "mecanismo aplicado no E028CPG do Comercial -- ver "
            "doc_nova_arquitetura.md."
        ),
    },
    {
        "tabela": "R910USU",
        "chaves_pk": ["CODENT"],
        "coluna_data": "DATALT",
        "tem_codemp": False,
        "coluna_codemp": None,
        "observacao": (
            "Tabela de usuários do sistema (mesmo padrão de R999USU no "
            "Comercial) -- sem CODEMP (confirmado via ALL_TAB_COLUMNS em "
            "07/07/2026). Usada para resolver nome do dono/coordenador do "
            "centro de custo (join duplo no vbiopex.py legado). MESMO "
            "NOME que a tabela do catálogo do Laudos RMA -- as duas "
            "gravam na MESMA DW_BRONZE.R910USU (schema único). Ver "
            "observação completa em laudos_rma/bronze/tabelas.py."
        ),
    },

]

# ----- VALIDAÇÃO -----

assert len(TABELAS) == 5, f"Esperado 5 tabelas no catálogo, encontrado {len(TABELAS)}"


# ----- FUNÇÃO AUXILIAR -----

def buscar_tabela(nome: str) -> dict:
    """Retorna a configuração de uma tabela do catálogo pelo nome exato."""
    for t in TABELAS:
        if t["tabela"] == nome:
            return t
    raise KeyError(f"Tabela '{nome}' não encontrada no catálogo da Bronze OPEX.")
