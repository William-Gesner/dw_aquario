"""
Catálogo das 34 tabelas Sapiens que formam a camada Bronze do Comercial.

Cada entrada descreve:
    tabela      : nome exato da tabela/view no Sapiens. Na Bronze, fica com o
                  MESMO nome (cópia crua, sem transformação).
    chaves_pk   : PK real da tabela no Sapiens (usada no MERGE incremental).
                  None só para USU_V660SUB, que é VIEW e não tem PK física.
    coluna_data : coluna usada no filtro de janela de 60 dias na carga
                  incremental. None = tabela sempre via full_reload (não
                  achamos coluna de data confiável -- são dimensões pequenas,
                  custo de recarregar tudo é baixo).
    tem_codemp  : se True, a query filtra CODEMP = 1.
                  se False, a tabela é global no Sapiens e não tem essa coluna
                  (confirmado via ALL_TAB_COLUMNS em 04/07/2026).
    tem_codfil  : se True, a query também filtra CODFIL = 1 (além de
                  CODEMP = 1). Só True quando tem_codemp também é True.
    observacao  : contexto/alerta levantado durante a validação do código
                  legado (comercial/extract/*.py). None quando não há nada
                  relevante a registrar.

Estratégia de carga (ver core/loader.py -> carregar_bronze()):
    1ª carga          -> full, filtrando CODEMP = 1 (e CODFIL = 1 quando
                         tem_codfil = True). Sem filtro algum quando
                         tem_codemp = False.
    cargas seguintes  -> incremental (MERGE), janela de 60 dias pela
                         coluna_data -- ou full sempre, se coluna_data
                         for None.

Validação tem_codemp (04/07/2026):
    Confirmado via query em ALL_TAB_COLUMNS (owner = 'SAPIENS').
    Tabelas sem CODEMP (globais): E022CLF, E026RAM, E069GRE, E073TRA,
    E085CLI, E090REP, E095FOR, USU_TPCAMNC, USU_TPCAPFC, USU_TPCRCDG,
    USU_TPCRCPC, USU_T017RVR, USU_T101CRI, USU_T101MET, USU_T101TIP.
"""

TABELAS = [

    # ===== 7 GRANDES / TRANSACIONAIS =====

    {
        "tabela": "E120IPD",
        "chaves_pk": ["CODEMP", "CODFIL", "NUMPED", "SEQIPD"],
        "coluna_data": "DATGER",
        "tem_codemp": True,
        "tem_codfil": True,
        "observacao": None,
    },
    {
        "tabela": "E120PED",
        "chaves_pk": ["CODEMP", "CODFIL", "NUMPED"],
        "coluna_data": "DATGER",
        "tem_codemp": True,
        "tem_codfil": True,
        "observacao": (
            "ALERTA: QTDABE (qtd em aberto) muda conforme o pedido avança, "
            "sem DATGER necessariamente mudar -- pedido pode trocar de SITPED "
            "sem atualizar a data. Confirmar com o cliente antes de confiar "
            "100% no incremental desta tabela na conferência Bronze."
        ),
    },
    {
        "tabela": "E140IPV",
        "chaves_pk": ["CODEMP", "CODFIL", "CODSNF", "NUMNFV", "SEQIPV"],
        "coluna_data": "DATGER",
        "tem_codemp": True,
        "tem_codfil": True,
        "observacao": None,
    },
    {
        "tabela": "E140ISV",
        "chaves_pk": ["CODEMP", "CODFIL", "CODSNF", "NUMNFV", "SEQISV"],
        "coluna_data": "DATGER",
        "tem_codemp": True,
        "tem_codfil": True,
        "observacao": None,
    },
    {
        "tabela": "E140NFV",
        "chaves_pk": ["CODEMP", "CODFIL", "CODSNF", "NUMNFV"],
        "coluna_data": "DATGER",
        "tem_codemp": True,
        "tem_codfil": True,
        "observacao": None,
    },
    {
        "tabela": "E440IPC",
        "chaves_pk": ["CODEMP", "CODFIL", "CODFOR", "NUMNFC", "CODSNF", "SEQIPC"],
        "coluna_data": "DATGER",
        "tem_codemp": True,
        "tem_codfil": True,
        "observacao": None,
    },
    {
        "tabela": "E440NFC",
        "chaves_pk": ["CODEMP", "CODFIL", "CODFOR", "NUMNFC", "CODSNF"],
        "coluna_data": "DATGER",
        "tem_codemp": True,
        "tem_codfil": True,
        "observacao": None,
    },

    # ===== DIMENSÕES COM CODEMP (confirmado via ALL_TAB_COLUMNS) =====

    {
        "tabela": "E001TNS",
        "chaves_pk": ["CODEMP", "CODTNS"],
        "coluna_data": None,
        "tem_codemp": True,
        "tem_codfil": False,
        "observacao": "Sem coluna de data identificada -- full_reload sempre.",
    },
    {
        "tabela": "E012FAM",
        "chaves_pk": ["CODEMP", "CODFAM"],
        "coluna_data": None,
        "tem_codemp": True,
        "tem_codfil": False,
        "observacao": None,
    },
    {
        "tabela": "E013AGP",
        "chaves_pk": ["CODEMP", "CODAGP"],
        "coluna_data": None,
        "tem_codemp": True,
        "tem_codfil": False,
        "observacao": None,
    },
    {
        "tabela": "E028CPG",
        "chaves_pk": ["CODEMP", "CODCPG"],
        "coluna_data": "DATATU",
        "tem_codemp": True,
        "tem_codfil": False,
        "observacao": "DATATU já usada como 'última atualização' em vbicondpgto.py.",
    },
    {
        "tabela": "E066FPG",
        "chaves_pk": ["CODEMP", "CODFPG"],
        "coluna_data": None,
        "tem_codemp": True,
        "tem_codfil": False,
        "observacao": None,
    },
    {
        "tabela": "E075DER",
        "chaves_pk": ["CODEMP", "CODPRO", "CODDER"],
        "coluna_data": None,
        "tem_codemp": True,
        "tem_codfil": False,
        "observacao": None,
    },
    {
        "tabela": "E075PRO",
        "chaves_pk": ["CODEMP", "CODPRO"],
        "coluna_data": None,
        "tem_codemp": True,
        "tem_codfil": False,
        "observacao": None,
    },
    {
        "tabela": "E085HCL",
        "chaves_pk": ["CODCLI", "CODEMP", "CODFIL"],
        "coluna_data": None,
        "tem_codemp": True,
        "tem_codfil": True,
        "observacao": (
            "Nome sugere histórico -- confirmar na conferência Bronze se é "
            "1 linha por cliente/filial ou se pode ter mais de uma."
        ),
    },
    {
        "tabela": "E140IDE",
        "chaves_pk": ["CODEMP", "CODFIL", "CODSNF", "NUMNFV"],
        "coluna_data": None,
        "tem_codemp": True,
        "tem_codfil": True,
        "observacao": None,
    },
    {
        "tabela": "E140PVD",
        "chaves_pk": ["CODEMP", "CODFIL", "CODSNF", "NUMNFV", "SEQIPV"],
        "coluna_data": None,
        "tem_codemp": True,
        "tem_codfil": True,
        "observacao": None,
    },

    # ===== DIMENSÕES GLOBAIS — SEM CODEMP (confirmado via ALL_TAB_COLUMNS) =====

    {
        "tabela": "E022CLF",
        "chaves_pk": ["CODCLF"],
        "coluna_data": None,
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": "Tabela global (confirmado via ALL_TAB_COLUMNS). Sem filtro de empresa.",
    },
    {
        "tabela": "E026RAM",
        "chaves_pk": ["CODRAM"],
        "coluna_data": None,
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": "Tabela global (confirmado via ALL_TAB_COLUMNS). Sem filtro de empresa.",
    },
    {
        "tabela": "E069GRE",
        "chaves_pk": ["CODGRE"],
        "coluna_data": None,
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": "Tabela global (confirmado via ALL_TAB_COLUMNS). Sem filtro de empresa.",
    },
    {
        "tabela": "E073TRA",
        "chaves_pk": ["CODTRA"],
        "coluna_data": None,
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": "Tabela global (confirmado via ALL_TAB_COLUMNS). Sem filtro de empresa.",
    },
    {
        "tabela": "E085CLI",
        "chaves_pk": ["CODCLI"],
        "coluna_data": "DATATU",
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": (
            "Tabela global (confirmado via ALL_TAB_COLUMNS). "
            "DATATU já usada como última atualização em vbicliente.py."
        ),
    },
    {
        "tabela": "E090REP",
        "chaves_pk": ["CODREP"],
        "coluna_data": None,
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": (
            "Tabela global (confirmado via ALL_TAB_COLUMNS). "
            "DATCAD existe mas é data de cadastro, não de atualização "
            "-- não confiável p/ capturar updates."
        ),
    },
    {
        "tabela": "E095FOR",
        "chaves_pk": ["CODFOR"],
        "coluna_data": None,
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": "Tabela global (confirmado via ALL_TAB_COLUMNS). Sem filtro de empresa.",
    },

    # ===== TABELAS CUSTOMIZADAS AQUÁRIO (USU_*) =====

    {
        "tabela": "USU_T017RVR",
        "chaves_pk": ["USU_CODRVR"],
        "coluna_data": "USU_DATGER",
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": (
            "Tabela customizada Aquário. Sem CODEMP (confirmado via ALL_TAB_COLUMNS). "
            "USU_DATGER já usada como DT_CADASTRO em vbiregionais.py."
        ),
    },
    {
        "tabela": "USU_T101CRI",
        "chaves_pk": ["USU_CODCRI"],
        "coluna_data": None,
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": "Sem CODEMP (confirmado via ALL_TAB_COLUMNS).",
    },
    {
        "tabela": "USU_T101MET",
        "chaves_pk": ["CODEMP", "MESANO", "CODTIP", "SEQREG"],
        "coluna_data": "USU_DATGER",
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": (
            "ATENÇÃO: ALL_TAB_COLUMNS não retornou CODEMP para esta tabela, "
            "mas a PK física inclui CODEMP (confirmado via vbimetas.py v1.2). "
            "Validar manualmente se a coluna existe com outro nome ou se a "
            "query deve filtrar por outro campo de empresa."
        ),
    },
    {
        "tabela": "USU_T101TIP",
        "chaves_pk": ["USU_CODTIP"],
        "coluna_data": None,
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": "Sem CODEMP (confirmado via ALL_TAB_COLUMNS).",
    },
    {
        "tabela": "USU_TPCAMNC",
        "chaves_pk": ["USU_CODMNC"],
        "coluna_data": None,
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": (
            "Modelo de negócio do cliente (alias MODNEG em vbicliente.py). "
            "Sem CODEMP (confirmado via ALL_TAB_COLUMNS)."
        ),
    },
    {
        "tabela": "USU_TPCAPFC",
        "chaves_pk": ["USU_CODPFC"],
        "coluna_data": None,
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": (
            "Perfil do cliente (alias PERFIL em vbicliente.py). "
            "Sem CODEMP (confirmado via ALL_TAB_COLUMNS)."
        ),
    },
    {
        "tabela": "USU_TPCRCDG",
        "chaves_pk": ["USU_CODEMP", "USU_CODGRA"],
        "coluna_data": None,
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": (
            "Descrição da graduação (alias DGRA em vbicliente.py). "
            "Sem coluna CODEMP -- usa USU_CODEMP como chave de empresa "
            "(confirmado via ALL_TAB_COLUMNS). Sem filtro de empresa na extração."
        ),
    },
    {
        "tabela": "USU_TPCRCPC",
        "chaves_pk": ["USU_CODCLI"],
        "coluna_data": None,
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": (
            "Graduação do cliente (alias GRA em vbicliente.py). "
            "Sem CODEMP (confirmado via ALL_TAB_COLUMNS)."
        ),
    },
    {
        "tabela": "R999USU",
        "chaves_pk": ["CODUSU"],
        "coluna_data": None,
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": (
            "Tabela de usuários do ERP (sistema Sapiens, prefixo R = tabela de "
            "sistema, não de módulo). Usada por vbiregionais.py (legado) via "
            "JOIN em USU_USUCOR/USU_USUASS de USU_T017RVR para obter nome de "
            "coordenador/assistente da regional. Estava AUSENTE deste catálogo "
            "até 06/07/2026 -- achada na auditoria de dependências dos 7 "
            "scripts legados. "
            "Validado via ALL_TAB_COLUMNS em 06/07/2026: não tem CODEMP/CODFIL "
            "(tem NUMEMP e CODFIL, mas ambos VARCHAR2 -- convenção diferente da "
            "usada nas demais tabelas de módulo, onde CODEMP/CODFIL são NUMBER). "
            "tem_codemp e tem_codfil ficam False DE PROPÓSITO: o vbiregionais.py "
            "legado faz o JOIN em R999USU sem nenhum filtro de empresa/filial, "
            "pois precisa resolver o nome de QUALQUER usuário que apareça como "
            "coordenador/assistente, independente da filial de cadastro dele -- "
            "filtrar aqui faria coordenadores de outras filiais aparecerem como "
            "'NÃO IDENTIFICADO' na Prata. Sem coluna de data -- full_reload sempre."
        ),
    },
    {
        "tabela": "USU_V660SUB",
        "chaves_pk": None,
        "coluna_data": None,
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": (
            "É VIEW no Sapiens, sem PK física -- MERGE não se aplica. "
            "Não é usada por nenhum dos 7 scripts hoje; só entra na Bronze "
            "por causa da view USU_V660SUB_VW (fase 2). Sempre full_reload."
        ),
    },
]

# ----- VALIDAÇÃO -----

assert len(TABELAS) == 34, f"Esperado 34 tabelas no catálogo, encontrado {len(TABELAS)}"


# ----- FUNÇÃO AUXILIAR -----

def buscar_tabela(nome: str) -> dict:
    """Retorna a configuração de uma tabela do catálogo pelo nome exato."""
    for t in TABELAS:
        if t["tabela"] == nome:
            return t
    raise KeyError(f"Tabela '{nome}' não encontrada no catálogo da Bronze.")