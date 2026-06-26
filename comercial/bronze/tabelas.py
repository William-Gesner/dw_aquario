"""
Catálogo das 33 tabelas Sapiens que formam a camada Bronze do Comercial.

Cada entrada descreve:
    tabela      : nome exato da tabela/view no Sapiens. Na Bronze, fica com o
                  MESMO nome (cópia crua, sem transformação).
    chaves_pk   : PK real da tabela no Sapiens (usada no MERGE incremental).
                  None só para USU_V660SUB, que é VIEW e não tem PK física.
    coluna_data : coluna usada no filtro de janela de 60 dias na carga
                  incremental. None = tabela sempre via full_reload (não
                  achamos coluna de data confiável -- são dimensões pequenas,
                  custo de recarregar tudo é baixo).
    tem_codfil  : se True, a query também filtra CODFIL = 1 (além de
                  CODEMP = 1, que é aplicado em TODAS as tabelas).
    observacao  : contexto/alerta levantado durante a validação do código
                  legado (comercial/extract/*.py). None quando não há nada
                  relevante a registrar.

Estratégia de carga (ver core/loader.py -> carregar_bronze()):
    1ª carga          -> full, filtrando CODEMP = 1 (e CODFIL = 1 quando
                         tem_codfil = True).
    cargas seguintes  -> incremental (MERGE), janela de 60 dias pela
                         coluna_data -- ou full sempre, se coluna_data
                         for None.
"""

TABELAS = [

    # ===== 7 GRANDES / TRANSACIONAIS =====

    {
        "tabela": "E120IPD",
        "chaves_pk": ["CODEMP", "CODFIL", "NUMPED", "SEQIPD"],
        "coluna_data": "DATGER",
        "tem_codfil": True,
        "observacao": None,
    },
    {
        "tabela": "E120PED",
        "chaves_pk": ["CODEMP", "CODFIL", "NUMPED"],
        "coluna_data": "DATGER",
        "tem_codfil": True,
        "observacao": (
            "ALERTA: expedicao/vbiexpedicao.py mostra que QTDABE (qtd em "
            "aberto) muda conforme o pedido avança, sem DATGER necessariamente "
            "mudar -- pedido pode trocar de SITPED sem atualizar a data. "
            "Confirmar com o cliente antes de confiar 100% no incremental "
            "desta tabela na conferência Bronze."
        ),
    },
    {
        "tabela": "E140IPV",
        "chaves_pk": ["CODEMP", "CODFIL", "CODSNF", "NUMNFV", "SEQIPV"],
        "coluna_data": "DATGER",
        "tem_codfil": True,
        "observacao": None,
    },
    {
        "tabela": "E140ISV",
        "chaves_pk": ["CODEMP", "CODFIL", "CODSNF", "NUMNFV", "SEQISV"],
        "coluna_data": "DATGER",
        "tem_codfil": True,
        "observacao": None,
    },
    {
        "tabela": "E140NFV",
        "chaves_pk": ["CODEMP", "CODFIL", "CODSNF", "NUMNFV"],
        "coluna_data": "DATGER",
        "tem_codfil": True,
        "observacao": None,
    },
    {
        "tabela": "E440IPC",
        "chaves_pk": ["CODEMP", "CODFIL", "CODFOR", "NUMNFC", "CODSNF", "SEQIPC"],
        "coluna_data": "DATGER",
        "tem_codfil": True,
        "observacao": None,
    },
    {
        "tabela": "E440NFC",
        "chaves_pk": ["CODEMP", "CODFIL", "CODFOR", "NUMNFC", "CODSNF"],
        "coluna_data": "DATGER",
        "tem_codfil": True,
        "observacao": None,
    },

    # ===== DIMENSÕES (PK confirmada via Oracle: ALL_CONSTRAINTS) =====

    {
        "tabela": "E001TNS",
        "chaves_pk": ["CODEMP", "CODTNS"],
        "coluna_data": None,
        "tem_codfil": False,
        "observacao": "Sem coluna de data identificada -- full_reload sempre.",
    },
    {
        "tabela": "E012FAM",
        "chaves_pk": ["CODEMP", "CODFAM"],
        "coluna_data": None,
        "tem_codfil": False,
        "observacao": None,
    },
    {
        "tabela": "E013AGP",
        "chaves_pk": ["CODEMP", "CODAGP"],
        "coluna_data": None,
        "tem_codfil": False,
        "observacao": None,
    },
    {
        "tabela": "E022CLF",
        "chaves_pk": ["CODCLF"],
        "coluna_data": None,
        "tem_codfil": False,
        "observacao": "PK sem CODEMP -- tabela global (confirmado via Oracle).",
    },
    {
        "tabela": "E026RAM",
        "chaves_pk": ["CODRAM"],
        "coluna_data": None,
        "tem_codfil": False,
        "observacao": "PK sem CODEMP -- tabela global.",
    },
    {
        "tabela": "E028CPG",
        "chaves_pk": ["CODEMP", "CODCPG"],
        "coluna_data": "DATATU",
        "tem_codfil": False,
        "observacao": "DATATU já usada como 'última atualização' em vbicondpgto.py.",
    },
    {
        "tabela": "E066FPG",
        "chaves_pk": ["CODEMP", "CODFPG"],
        "coluna_data": None,
        "tem_codfil": False,
        "observacao": None,
    },
    {
        "tabela": "E069GRE",
        "chaves_pk": ["CODGRE"],
        "coluna_data": None,
        "tem_codfil": False,
        "observacao": "PK sem CODEMP -- tabela global.",
    },
    {
        "tabela": "E073TRA",
        "chaves_pk": ["CODTRA"],
        "coluna_data": None,
        "tem_codfil": False,
        "observacao": "PK sem CODEMP -- tabela global.",
    },
    {
        "tabela": "E075DER",
        "chaves_pk": ["CODEMP", "CODPRO", "CODDER"],
        "coluna_data": None,
        "tem_codfil": False,
        "observacao": None,
    },
    {
        "tabela": "E075PRO",
        "chaves_pk": ["CODEMP", "CODPRO"],
        "coluna_data": None,
        "tem_codfil": False,
        "observacao": None,
    },
    {
        "tabela": "E085CLI",
        "chaves_pk": ["CODCLI"],
        "coluna_data": "DATATU",
        "tem_codfil": False,
        "observacao": (
            "PK sem CODEMP -- tabela global. DATATU já usada como "
            "'última atualização' em vbicliente.py."
        ),
    },
    {
        "tabela": "E085HCL",
        "chaves_pk": ["CODCLI", "CODEMP", "CODFIL"],
        "coluna_data": None,
        "tem_codfil": True,
        "observacao": (
            "Nome sugere histórico -- confirmar na conferência Bronze se é "
            "1 linha por cliente/filial ou se pode ter mais de uma."
        ),
    },
    {
        "tabela": "E090REP",
        "chaves_pk": ["CODREP"],
        "coluna_data": None,
        "tem_codfil": False,
        "observacao": (
            "PK sem CODEMP -- tabela global. DATCAD existe mas é data de "
            "cadastro, não de atualização -- não confiável p/ capturar updates."
        ),
    },
    {
        "tabela": "E095FOR",
        "chaves_pk": ["CODFOR"],
        "coluna_data": None,
        "tem_codfil": False,
        "observacao": "PK sem CODEMP -- tabela global.",
    },
    {
        "tabela": "E140IDE",
        "chaves_pk": ["CODEMP", "CODFIL", "CODSNF", "NUMNFV"],
        "coluna_data": None,
        "tem_codfil": True,
        "observacao": None,
    },
    {
        "tabela": "E140PVD",
        "chaves_pk": ["CODEMP", "CODFIL", "CODSNF", "NUMNFV", "SEQIPV"],
        "coluna_data": None,
        "tem_codfil": True,
        "observacao": None,
    },
    {
        "tabela": "USU_T017RVR",
        "chaves_pk": ["USU_CODRVR"],
        "coluna_data": "USU_DATGER",
        "tem_codfil": False,
        "observacao": (
            "Tabela customizada Aquário. USU_DATGER já usada como "
            "DT_CADASTRO em vbiregionais.py."
        ),
    },
    {
        "tabela": "USU_T101CRI",
        "chaves_pk": ["USU_CODCRI"],
        "coluna_data": None,
        "tem_codfil": False,
        "observacao": None,
    },
    {
        "tabela": "USU_T101MET",
        "chaves_pk": ["CODEMP", "MESANO", "CODTIP", "SEQREG"],
        "coluna_data": "USU_DATGER",
        "tem_codfil": False,
        "observacao": (
            "PK e coluna de auditoria já confirmadas via vbimetas.py "
            "(modelo v1.2, Junho/2026)."
        ),
    },
    {
        "tabela": "USU_T101TIP",
        "chaves_pk": ["USU_CODTIP"],
        "coluna_data": None,
        "tem_codfil": False,
        "observacao": None,
    },
    {
        "tabela": "USU_TPCAMNC",
        "chaves_pk": ["USU_CODMNC"],
        "coluna_data": None,
        "tem_codfil": False,
        "observacao": "Modelo de negócio do cliente (alias MODNEG em vbicliente.py).",
    },
    {
        "tabela": "USU_TPCAPFC",
        "chaves_pk": ["USU_CODPFC"],
        "coluna_data": None,
        "tem_codfil": False,
        "observacao": "Perfil do cliente (alias PERFIL em vbicliente.py).",
    },
    {
        "tabela": "USU_TPCRCDG",
        "chaves_pk": ["USU_CODEMP", "USU_CODGRA"],
        "coluna_data": None,
        "tem_codfil": False,
        "observacao": "Descrição da graduação (alias DGRA em vbicliente.py).",
    },
    {
        "tabela": "USU_TPCRCPC",
        "chaves_pk": ["USU_CODCLI"],
        "coluna_data": None,
        "tem_codfil": False,
        "observacao": "Graduação do cliente (alias GRA em vbicliente.py).",
    },
    {
        "tabela": "USU_V660SUB",
        "chaves_pk": None,
        "coluna_data": None,
        "tem_codfil": False,
        "observacao": (
            "É VIEW no Sapiens, sem PK física -- MERGE não se aplica. "
            "Não é usada por nenhum dos 7 scripts hoje; só entra na Bronze "
            "por causa da view USU_V660SUB_VW (fase 2). Sempre full_reload."
        ),
    },
]

# ----- VALIDAÇÃO -----

assert len(TABELAS) == 33, f"Esperado 33 tabelas no catálogo, encontrado {len(TABELAS)}"


# ----- FUNÇÃO AUXILIAR -----

def buscar_tabela(nome: str) -> dict:
    """Retorna a configuração de uma tabela do catálogo pelo nome exato."""
    for t in TABELAS:
        if t["tabela"] == nome:
            return t
    raise KeyError(f"Tabela '{nome}' não encontrada no catálogo da Bronze.")