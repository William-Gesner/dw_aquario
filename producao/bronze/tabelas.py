"""
Catálogo das tabelas Sapiens que formam a camada Bronze da Produção.

Cada entrada descreve:
    tabela        : nome exato da tabela no Sapiens. Na Bronze, fica com
                    o MESMO nome (cópia crua, sem transformação).
    chaves_pk     : PK real, validada via ALL_CONSTRAINTS/ALL_CONS_COLUMNS
                    em 08/07/2026.
    coluna_data   : coluna usada no filtro de janela de 60 dias na carga
                    incremental. None = sem coluna de auditoria confiável
                    (nem "última alteração" nem data de negócio segura o
                    suficiente) -- tabela sempre via full_reload.
    tem_codemp    : se True, a query filtra pela coluna de empresa real.
    coluna_codemp : nome real da coluna de empresa. Todas as tabelas da
                    Produção usam "CODEMP" puro (sem prefixo USU_,
                    diferente do Laudos RMA).
    tem_codfil    : se True, filtra também pela coluna de filial real.
    coluna_codfil : nome real da coluna de filial ("CODFIL" quando
                    aplicável).
    observacao    : contexto levantado na validação.

REGRA DE EMPRESA/FILIAL: igual ao resto do projeto -- CODEMP = 1 e
CODFIL = 1 sempre (ver producao.config.settings). Sem exceção aqui
(diferente do OPEX). Nenhuma query legada filtrava CODEMP/CODFIL
explicitamente nessas tabelas (exceto E720OPR/E725CRE, que já vinham
filtradas em vbicentrocusto.py) -- aplicamos o filtro estrutural do
projeto mesmo assim, mesma política já usada no OPEX e no Laudos RMA.

TABELAS COMPARTILHADAS COM O COMERCIAL -- NÃO EXTRAÍDAS AQUI:
    A Produção também depende de E012FAM, E013AGP, E075DER, E075PRO
    (usadas em vbiproduto.py legado). Já são mantidas atualizadas pelo
    comercial/bronze/tabelas.py -- extrair de novo aqui seria trabalho
    redobrado. Definição real fica só no catálogo do Comercial. Listadas
    abaixo só para rastreio de dependência -- ver
    TABELAS_COMPARTILHADAS_COM_COMERCIAL.

TABELA EXCLUÍDA -- NÃO EXISTE NESTE AMBIENTE:
    EW909MVO era referenciada em vbidesempenho.py, mas só dentro de um
    comentário SQL -- o próprio código legado já documentava que essa
    tabela não existe neste ambiente Sapiens/Senior (a subconsulta real
    estava comentada, nunca executada). Não entra no catálogo.
"""

# ----- CATÁLOGO DE TABELAS (EXCLUSIVAS DA PRODUÇÃO) -----

TABELAS = [

    {
        "tabela": "E018MTV",
        "chaves_pk": ["CODEMP", "CODMTV"],
        "coluna_data": None,
        "tem_codemp": True,
        "coluna_codemp": "CODEMP",
        "tem_codfil": False,
        "observacao": "Motivo de parada. Sem coluna de data -- full_reload sempre.",
    },
    {
        "tabela": "E044CCU",
        "chaves_pk": ["CODEMP", "CODCCU"],
        "coluna_data": "DATALT",
        "tem_codemp": True,
        "coluna_codemp": "CODEMP",
        "tem_codfil": False,
        "observacao": (
            "Centros de custo. MESMO NOME que a tabela usada no OPEX, mas "
            "ali vem do banco de Controladoria (servidor separado) -- "
            "aqui vem do servidor principal (mesmo do Comercial/Laudos "
            "RMA). São instâncias físicas diferentes, cada uma com sua "
            "própria cópia na Bronze -- mesmo caso do R910USU no Laudos "
            "RMA. Estrutura validada independentemente em 08/07/2026."
        ),
    },
    {
        "tabela": "E047NTG",
        "chaves_pk": ["CODEMP", "CODNTG"],
        "coluna_data": None,
        "tem_codemp": True,
        "coluna_codemp": "CODEMP",
        "tem_codfil": False,
        "observacao": "Natureza de gasto. Sem coluna de data -- full_reload sempre.",
    },
    {
        "tabela": "E093ETG",
        "chaves_pk": ["CODEMP", "CODETG"],
        "coluna_data": None,
        "tem_codemp": True,
        "coluna_codemp": "CODEMP",
        "tem_codfil": False,
        "observacao": "Estágio de produção. Sem coluna de data -- full_reload sempre.",
    },
    {
        "tabela": "E210MVP",
        "chaves_pk": ["CODEMP", "CODPRO", "CODDER", "CODDEP", "DATMOV", "SEQMOV"],
        "coluna_data": "DATMOV",
        "tem_codemp": True,
        "coluna_codemp": "CODEMP",
        "tem_codfil": True,
        "coluna_codfil": "CODFIL",
        "observacao": (
            "Movimentação de produtos (consumo de matéria-prima). Tabela "
            "grande (~140 colunas na origem) -- full_reload_streaming na "
            "1ª carga, mesmo tratamento do E120IPD no Comercial."
        ),
    },
    {
        "tabela": "E621MTC",
        "chaves_pk": ["NUMMTC"],
        "coluna_data": "DATATU",
        "tem_codemp": True,
        "coluna_codemp": "CODEMP",
        "tem_codfil": True,
        "coluna_codfil": "CODFIL",
        "observacao": (
            "Mapa de cálculo (orçamento/custo). PK real é só NUMMTC "
            "(confirmado via ALL_CONS_COLUMNS em 08/07/2026) -- CODEMP e "
            "CODFIL existem como coluna mas não fazem parte da PK. Filtro "
            "estrutural aplicado mesmo assim na extração (não no MERGE)."
        ),
    },
    {
        "tabela": "E626ORC",
        "chaves_pk": ["NUMMTC", "CODEMP", "CODCCU", "CODNTG"],
        "coluna_data": None,
        "tem_codemp": True,
        "coluna_codemp": "CODEMP",
        "tem_codfil": False,
        "observacao": "Orçamento por centro de custo. Sem coluna de data -- full_reload sempre.",
    },
    {
        "tabela": "E626TAX",
        "chaves_pk": ["NUMMTC", "CODEMP", "CODCCU", "CODGNG"],
        "coluna_data": None,
        "tem_codemp": True,
        "coluna_codemp": "CODEMP",
        "tem_codfil": False,
        "observacao": "Taxa de custo por centro de custo. Sem coluna de data -- full_reload sempre.",
    },
    {
        "tabela": "E630SPE",
        "chaves_pk": ["NUMMTC", "CODPRO", "CODDER", "CODETG", "CODCCU", "CODORI", "NUMORP", "TIPMPE"],
        "coluna_data": None,
        "tem_codemp": True,
        "coluna_codemp": "CODEMP",
        "tem_codfil": False,
        "observacao": "Saldo/posição de estoque em processo. Sem coluna de data -- full_reload sempre.",
    },
    {
        "tabela": "E720OPR",
        "chaves_pk": ["CODEMP", "CODOPR"],
        "coluna_data": "DATALT",
        "tem_codemp": True,
        "coluna_codemp": "CODEMP",
        "tem_codfil": False,
        "observacao": "Operação de produção. Única tabela nova cuja query legada (vbicentrocusto.py) já filtrava CODEMP explicitamente.",
    },
    {
        "tabela": "E725CRE",
        "chaves_pk": ["CODEMP", "CODCRE"],
        "coluna_data": "DATALT",
        "tem_codemp": True,
        "coluna_codemp": "CODEMP",
        "tem_codfil": False,
        "observacao": "Centro de recurso. Query legada (vbicentrocusto.py) já filtrava CODEMP explicitamente.",
    },
    {
        "tabela": "E900COP",
        "chaves_pk": ["CODEMP", "CODORI", "NUMORP"],
        "coluna_data": "DATGER",
        "tem_codemp": True,
        "coluna_codemp": "CODEMP",
        "tem_codfil": True,
        "coluna_codfil": "CODFIL",
        "observacao": "Cabeçalho da ordem de produção.",
    },
    {
        "tabela": "E900EOQ",
        "chaves_pk": ["CODEMP", "CODORI", "NUMORP", "CODETG", "SEQEOQ"],
        "coluna_data": "DATREA",
        "tem_codemp": True,
        "coluna_codemp": "CODEMP",
        "tem_codfil": False,
        "observacao": (
            "Apontamento de produção por OP/estágio/data -- provavelmente "
            "a maior tabela nova desta área (usada em 4 subconsultas "
            "correlacionadas dentro de vbidesempenho.py). Full_reload_"
            "streaming na 1ª carga, mesmo tratamento do E120IPD."
        ),
    },
    {
        "tabela": "E900OOP",
        "chaves_pk": ["CODEMP", "CODORI", "NUMORP", "CODETG", "SFXETR", "SEQROT", "SFXSEQ"],
        "coluna_data": None,
        "tem_codemp": True,
        "coluna_codemp": "CODEMP",
        "tem_codfil": False,
        "observacao": (
            "Roteiro/operação da OP. Tem colunas de data (DTRINI, DTRFIM, "
            "DATICA, DATFCA), mas são datas de NEGÓCIO (início/fim "
            "planejado ou real), não de auditoria -- um campo pode mudar "
            "sem nenhuma delas mudar junto (mesmo risco já documentado "
            "pro QTDABE do E120PED no Comercial). Full_reload sempre."
        ),
    },
    {
        "tabela": "E900QDO",
        "chaves_pk": ["CODEMP", "CODORI", "NUMORP", "CODPRO", "CODDER"],
        "coluna_data": None,
        "tem_codemp": True,
        "coluna_codemp": "CODEMP",
        "tem_codfil": False,
        "observacao": "Quantidade demandada da OP. Sem coluna de data -- full_reload sempre.",
    },
    {
        "tabela": "E930MPR",
        "chaves_pk": ["CODEMP", "CODFIL", "CODETG", "CODCRE", "IDEBEM", "DATMPR", "CODMTV", "SEQMPR"],
        "coluna_data": "DATMPR",
        "tem_codemp": True,
        "coluna_codemp": "CODEMP",
        "tem_codfil": True,
        "coluna_codfil": "CODFIL",
        "observacao": "Histórico de paradas de equipamento/centro de recurso.",
    },

]

# ----- VALIDAÇÃO -----

assert len(TABELAS) == 16, f"Esperado 16 tabelas no catálogo, encontrado {len(TABELAS)}"


# ----- TABELAS COMPARTILHADAS (NÃO EXTRAÍDAS AQUI) -----

# Ver docstring do módulo. Definição real fica em
# comercial/bronze/tabelas.py -- aqui é só documentação de dependência.
TABELAS_COMPARTILHADAS_COM_COMERCIAL = [
    "E012FAM",
    "E013AGP",
    "E075DER",
    "E075PRO",
]


# ----- FUNÇÃO AUXILIAR -----

def buscar_tabela(nome: str) -> dict:
    """Retorna a configuração de uma tabela do catálogo pelo nome exato."""
    for t in TABELAS:
        if t["tabela"] == nome:
            return t
    raise KeyError(f"Tabela '{nome}' não encontrada no catálogo da Bronze Produção.")
