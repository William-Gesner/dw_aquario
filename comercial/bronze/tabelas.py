"""
Catálogo das 33 tabelas Sapiens que formam a camada Bronze do Comercial.

Cada entrada descreve:
    tabela      : nome exato da tabela no Sapiens. Na Bronze, fica com o
                  MESMO nome (cópia crua, sem transformação).
    chaves_pk   : PK real da tabela no Sapiens (usada no MERGE incremental).
    coluna_data : coluna usada no filtro de janela de 60 dias na carga
                  incremental. None = tabela sempre via full_reload (não
                  achamos coluna de data confiável -- são dimensões pequenas,
                  custo de recarregar tudo é baixo).
    tem_codemp  : se True, a query filtra a coluna de empresa = 1.
                  se False, a tabela é global no Sapiens e não tem essa coluna
                  (confirmado via ALL_TAB_COLUMNS em 04/07/2026).
    tem_codfil  : se True, a query também filtra CODFIL = 1 (além do filtro
                  de empresa). Só True quando tem_codemp também é True.
    coluna_codemp : nome REAL da coluna de empresa no Sapiens. Opcional --
                  quando ausente, assume "CODEMP" (o padrão na maioria das
                  tabelas). Só precisa ser declarado quando o nome físico é
                  outro, como em USU_T101MET (é "USU_CODEMP", não "CODEMP" --
                  bug de produção corrigido em 06/07/2026, ver observação).
    coluna_codfil : mesma ideia, mas para a coluna de filial. Opcional,
                  assume "CODFIL" quando ausente.
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
        "tem_codfil": False,
        "observacao": "Mesmo motivo do E140NFV -- ver observação completa ali.",
    },
    {
        "tabela": "E120PED",
        "chaves_pk": ["CODEMP", "CODFIL", "NUMPED"],
        "coluna_data": "DATGER",
        "tem_codemp": True,
        "tem_codfil": False,
        "observacao": (
            "ALERTA: QTDABE (qtd em aberto) muda conforme o pedido avança, "
            "sem DATGER necessariamente mudar -- pedido pode trocar de SITPED "
            "sem atualizar a data. Confirmar com o cliente antes de confiar "
            "100% no incremental desta tabela na conferência Bronze. "
            "CORRIGIDO em 17/07/2026: tem_codfil virou False -- mesmo motivo "
            "do E140NFV, ver observação completa ali."
        ),
    },
    {
        "tabela": "E140IPV",
        "chaves_pk": ["CODEMP", "CODFIL", "CODSNF", "NUMNFV", "SEQIPV"],
        "coluna_data": "DATGER",
        "tem_codemp": True,
        "tem_codfil": False,
        "observacao": "Mesmo motivo do E140NFV -- ver observação completa ali.",
    },
    {
        "tabela": "E140ISV",
        "chaves_pk": ["CODEMP", "CODFIL", "CODSNF", "NUMNFV", "SEQISV"],
        "coluna_data": "DATGER",
        "tem_codemp": True,
        "tem_codfil": False,
        "observacao": "Mesmo motivo do E140NFV -- ver observação completa ali.",
    },
    {
        "tabela": "E140NFV",
        "chaves_pk": ["CODEMP", "CODFIL", "CODSNF", "NUMNFV"],
        "coluna_data": "DATGER",
        "tem_codemp": True,
        "tem_codfil": False,
        "observacao": (
            "CORRIGIDO em 17/07/2026: tem_codfil estava True, filtrando "
            "CODFIL=1 na extração -- mas nenhum dos scripts legados que usam "
            "esta tabela (vbicliente.py, vbifaturamento.py) filtra CODFIL, só "
            "CODEMP=1 (CODFIL só aparece em JOIN e como coluna de saída "
            "CODFILIAL). O filtro indevido fazia a Bronze descartar notas de "
            "outras filiais da empresa 1, causando divergência real na "
            "conferência do DIM_CLIENTE (nota de 2018 sob CODFIL=2 sumia da "
            "Bronze, deslocando o ranking de 1ª/2ª/3ª/4ª compra do cliente). "
            "tem_codfil virou False; tem_codemp continua True. Mesmo ajuste "
            "replicado em E120IPD, E120PED, E140IPV, E140ISV, E440IPC e "
            "E440NFC (as outras 6 das 7 grandes/transacionais, pelo mesmo "
            "motivo -- nenhuma delas é filtrada por CODFIL no legado). "
            "Requer dropar a tabela na DW_BRONZE e deixar a próxima execução "
            "refazer a 1ª carga do zero, já com o escopo correto (mesmo "
            "procedimento do fix do USU_T101MET)."
        ),
    },
    {
        "tabela": "E440IPC",
        "chaves_pk": ["CODEMP", "CODFIL", "CODFOR", "NUMNFC", "CODSNF", "SEQIPC"],
        "coluna_data": "DATGER",
        "tem_codemp": True,
        "tem_codfil": False,
        "observacao": "Mesmo motivo do E140NFV -- ver observação completa ali.",
    },
    {
        "tabela": "E440NFC",
        "chaves_pk": ["CODEMP", "CODFIL", "CODFOR", "NUMNFC", "CODSNF"],
        "coluna_data": "DATGER",
        "tem_codemp": True,
        "tem_codfil": False,
        "observacao": "Mesmo motivo do E140NFV -- ver observação completa ali.",
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
        "tem_codfil": False,
        "observacao": (
            "Nome sugere histórico -- confirmar na conferência Bronze se é "
            "1 linha por cliente/filial ou se pode ter mais de uma. "
            "CORRIGIDO em 17/07/2026 (3): tem_codfil virou False -- usada "
            "com 2 escopos diferentes nos scripts Prata: DIM_CLIENTE fixa "
            "'AND H.CODFIL = 1' no próprio JOIN (continua batendo, filtro "
            "está na query, não na Bronze), mas FAT_FATURAMENTO casa "
            "dinamicamente pela filial de cada linha ('I.CODFIL = H.CODFIL') "
            "-- com a Bronze só trazendo filial 1, notas de outra filial "
            "perdiam o enriquecimento (representante etc.). Mesmo motivo "
            "raiz do E140NFV: Bronze deve trazer o universo completo, quem "
            "decide o escopo de filial é a query consumidora."
        ),
    },
    {
        "tabela": "E140IDE",
        "chaves_pk": ["CODEMP", "CODFIL", "CODSNF", "NUMNFV"],
        "coluna_data": None,
        "tem_codemp": True,
        "tem_codfil": False,
        "observacao": (
            "CORRIGIDO em 17/07/2026 (3): tem_codfil estava True, mas o JOIN "
            "com essa tabela em DIM_CLIENTE ('ON NF.CODEMP = I.CODEMP AND "
            "NF.NUMNFV = I.NUMNFV') e em FAT_FATURAMENTO ('AND I.CODFIL = "
            "IDE.CODFIL', casando pela filial da própria nota) nunca "
            "restringiu a filial 1 -- igual no legado. Com a Bronze filtrada, "
            "nota de outra filial perdia o INNER JOIN (DIM_CLIENTE) ou caía "
            "no filtro IDE.SITDOE=3 por causa do LEFT JOIN vindo NULL "
            "(FAT_FATURAMENTO) -- em ambos os casos a linha sumia. Achado na "
            "conferência do DIM_CLIENTE depois do fix do E140NFV: resolveu "
            "os primeiros 92% da divergência, mas sobrou um resíduo estável "
            "(sempre os mesmos ~2.266 clientes) que apontou pra esse JOIN."
        ),
    },
    {
        "tabela": "E140PVD",
        "chaves_pk": ["CODEMP", "CODFIL", "CODSNF", "NUMNFV", "SEQIPV"],
        "coluna_data": None,
        "tem_codemp": True,
        "tem_codfil": False,
        "observacao": "Mesmo motivo do E085HCL -- JOIN dinâmico por filial em FAT_FATURAMENTO, sem restrição a filial 1 no legado.",
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
        "coluna_data": None,
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": (
            "Tabela global (confirmado via ALL_TAB_COLUMNS). "
            "CORRIGIDO em 17/07/2026: coluna_data era 'DATATU', com "
            "incremental de 60 dias -- mas DATATU não captura toda edição "
            "de cadastro (confirmado: cliente com ENDCLI/NENCLI editado no "
            "Sapiens sem DATATU mudar, comparado direto Sapiens x legado -- "
            "os dois batiam entre si, só a Bronze estava com valor antigo, "
            "preso pra sempre porque a janela de 60 dias nunca via motivo "
            "pra reler essa linha). O legado (vbicliente.py) nunca filtrou "
            "por data nessa tabela -- sempre relê a base inteira a cada "
            "execução, MERGE só como estratégia de escrita, não de "
            "leitura. coluna_data virou None: Bronze agora também relê "
            "E085CLI inteira a cada ciclo (~145 mil linhas, barato -- nada "
            "perto das 7 grandes), replicando o comportamento real do "
            "legado em vez de confiar num carimbo de auditoria que não é "
            "confiável pra esses campos."
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
        "chaves_pk": ["USU_CODEMP", "USU_MESANO", "USU_CODTIP", "USU_SEQREG"],
        "coluna_data": "USU_DATGER",
        "tem_codemp": True,
        "tem_codfil": False,
        "coluna_codemp": "USU_CODEMP",
        "observacao": (
            "CORRIGIDO em 06/07/2026 (erro em produção: ORA-00904 SEQREG "
            "invalid identifier). O alerta anterior estava certo: a coluna "
            "de empresa NÃO se chama CODEMP nesta tabela -- é USU_CODEMP "
            "(confirmado via vbimetas.py v1.2, que fazia "
            "'M.USU_CODEMP AS CODEMP'). O catálogo estava com os nomes "
            "ALIASADOS do script legado em vez dos nomes físicos reais da "
            "coluna -- errado pra Bronze, que é cópia crua sem renomear "
            "nada. chaves_pk corrigida pros nomes físicos (USU_CODEMP, "
            "USU_MESANO, USU_CODTIP, USU_SEQREG), e tem_codemp virou True "
            "com coluna_codemp='USU_CODEMP' (ver montar_query() em "
            "extrator.py). ATENÇÃO OPERACIONAL: como tem_codemp ficou False "
            "até agora, a tabela pode ter carregado metas de OUTRAS "
            "empresas do grupo (não só CODEMP=1) -- é necessário dropar "
            "DW_BRONZE.USU_T101MET e deixar a próxima execução refazer a "
            "1ª carga do zero, já com o filtro correto."
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
]

# ----- VALIDAÇÃO -----

assert len(TABELAS) == 33, f"Esperado 33 tabelas no catálogo, encontrado {len(TABELAS)}"

# NOTA: USU_V660SUB (view do Sapiens, sem PK física) foi removida deste
# catálogo em 06/07/2026 -- não é usada por nenhum dos 7 scripts legados do
# Comercial, e a justificativa anterior ("fase 2" / view USU_V660SUB_VW) não
# tinha nenhuma base documentada no projeto. Migrar só o que está
# comprovadamente em uso é a regra; se algum dia ela for necessária, entra
# no catálogo com a real necessidade documentada (e vai precisar de um
# caminho de carga próprio, já que o motor genérico atual exige PK).


# ----- FUNÇÃO AUXILIAR -----

def buscar_tabela(nome: str) -> dict:
    """Retorna a configuração de uma tabela do catálogo pelo nome exato."""
    for t in TABELAS:
        if t["tabela"] == nome:
            return t
    raise KeyError(f"Tabela '{nome}' não encontrada no catálogo da Bronze.")