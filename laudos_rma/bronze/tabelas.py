"""
Catálogo das tabelas Sapiens que formam a camada Bronze do Laudos RMA.

Cada entrada descreve:
    tabela        : nome exato da tabela/view no Sapiens. Na Bronze, fica
                    com o MESMO nome (cópia crua, sem transformação).
    chaves_pk     : PK real, validada via ALL_CONSTRAINTS/ALL_CONS_COLUMNS
                    em 07/07/2026. None só para USU_VZRASLAU, que é VIEW
                    sem PK física -- ver core/loader.py carregar_bronze():
                    quando chaves_pk é None, a carga é SEMPRE full_reload
                    (nunca tenta MERGE).
    coluna_data   : coluna usada no filtro de janela de 60 dias na carga
                    incremental. None = tabela sempre via full_reload.
    tem_codemp    : se True, a query filtra pela coluna de empresa real.
    coluna_codemp : nome real da coluna de empresa. Default seria "CODEMP"
                    mas TODAS as tabelas novas do Laudos RMA usam o
                    prefixo USU_ (USU_CODEMP) -- diferente do Comercial,
                    onde a maioria usa "CODEMP" puro.
    tem_codfil    : se True, filtra também pela coluna de filial real.
    coluna_codfil : nome real da coluna de filial (USU_CODFIL quando
                    aplicável).
    observacao    : contexto levantado na validação.

REGRA DE EMPRESA/FILIAL: igual ao resto do projeto -- CODEMP = 1 e
CODFIL = 1 sempre (ver laudos_rma.config.settings). Sem exceção aqui
(diferente do OPEX).

TABELAS COMPARTILHADAS COM O COMERCIAL -- NÃO EXTRAÍDAS AQUI:
    O Laudos RMA também depende de E440NFC, E095FOR, E075PRO, E075DER,
    E013AGP, E140NFV, E073TRA, E140IPV, E140IDE, E001TNS (usadas em
    vbilaudos.py/vbivendas.py legado). Como DW_BRONZE é um schema único
    (não há "Bronze do Comercial" x "Bronze do Laudos RMA"), essas 10 já
    são mantidas atualizadas pelo comercial/bronze/tabelas.py -- extrair
    de novo aqui seria trabalho redobrado e redundante contra o Sapiens.
    A definição real (PK, coluna_data etc.) fica SÓ no catálogo do
    Comercial, para não ter duas fontes de verdade divergindo. Listadas
    abaixo só para rastreio de dependência -- ver
    TABELAS_COMPARTILHADAS_COM_COMERCIAL.
"""

# ----- CATÁLOGO DE TABELAS (EXCLUSIVAS DO LAUDOS RMA) -----

TABELAS = [

    {
        "tabela": "USU_TLAUITE",
        "chaves_pk": ["USU_CODEMP", "USU_CODFIL", "USU_CODLAU", "USU_SEQIPC", "USU_SEQUNI"],
        "coluna_data": "USU_DATALT",
        "tem_codemp": True,
        "coluna_codemp": "USU_CODEMP",
        "tem_codfil": True,
        "coluna_codfil": "USU_CODFIL",
        "observacao": (
            "Item do laudo (fato principal do vbilaudos.py legado). A query "
            "legada NÃO filtrava USU_CODEMP explicitamente (só herdava via "
            "JOIN) -- mesmo caso do E044CCU no OPEX. Filtramos "
            "USU_CODEMP=1/USU_CODFIL=1 explicitamente na Bronze, seguindo "
            "a regra estrutural do projeto."
        ),
    },
    {
        "tabela": "USU_TLAUGER",
        "chaves_pk": ["USU_CODEMP", "USU_CODFIL", "USU_CODLAU"],
        "coluna_data": "USU_DATALT",
        "tem_codemp": True,
        "coluna_codemp": "USU_CODEMP",
        "tem_codfil": True,
        "coluna_codfil": "USU_CODFIL",
        "observacao": "Cabeçalho do laudo. Mesma observação de USU_TLAUITE quanto ao filtro de empresa.",
    },
    {
        "tabela": "USU_TLAUDEF",
        "chaves_pk": ["USU_CODEMP", "USU_CODPRO", "USU_CODDER", "USU_CODDEF"],
        "coluna_data": "USU_DATALT",
        "tem_codemp": True,
        "coluna_codemp": "USU_CODEMP",
        "tem_codfil": False,
        "observacao": "Defeito (por produto/derivação). Sem coluna de filial.",
    },
    {
        "tabela": "USU_TLAUCOR",
        "chaves_pk": ["USU_CODCOR"],
        "coluna_data": "USU_DATALT",
        "tem_codemp": True,
        "coluna_codemp": "USU_CODEMP",
        "tem_codfil": False,
        "observacao": "Cor. Tem USU_CODEMP como coluna, mas a PK real é só USU_CODCOR (confirmado via ALL_CONS_COLUMNS em 07/07/2026).",
    },
    {
        "tabela": "USU_TLAUPRB",
        "chaves_pk": ["USU_CODPRB"],
        "coluna_data": "USU_DATALT",
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": "Problema. Tabela global -- sem CODEMP (confirmado via ALL_TAB_COLUMNS em 07/07/2026).",
    },
    {
        "tabela": "USU_TLAUSIT",
        "chaves_pk": ["USU_CODSIT"],
        "coluna_data": "USU_DATALT",
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": "Situação do laudo. Tabela global -- sem CODEMP (confirmado via ALL_TAB_COLUMNS em 07/07/2026).",
    },
    {
        "tabela": "USU_TLAUTIP",
        "chaves_pk": ["USU_CODTIP"],
        "coluna_data": "USU_DATALT",
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": "Tipo de laudo. Tabela global -- sem CODEMP (confirmado via ALL_TAB_COLUMNS em 07/07/2026).",
    },
    {
        "tabela": "R910USU",
        "chaves_pk": ["CODENT"],
        "coluna_data": "DATALT",
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": (
            "Tabela de usuários do sistema. MESMO NOME que a tabela usada "
            "no OPEX, mas ali vem do banco de Controladoria (servidor "
            "separado) -- aqui vem do servidor principal (mesmo do "
            "Comercial). São instâncias físicas diferentes, cada uma com "
            "sua própria cópia na Bronze -- não é a mesma linha de código "
            "nem a mesma tabela de origem, mesmo com nome idêntico. "
            "Estrutura validada independentemente em 07/07/2026 (sem "
            "CODEMP, igual à versão da Controladoria)."
        ),
    },
    {
        "tabela": "USU_VZRASLAU",
        "chaves_pk": None,
        "coluna_data": None,
        "tem_codemp": True,
        "coluna_codemp": "EMPNFV",
        "tem_codfil": True,
        "coluna_codfil": "FILNFV",
        "observacao": (
            "É VIEW no Sapiens, sem PK física -- confirmado via "
            "ALL_CONSTRAINTS em 07/07/2026 (não retornou nada). Sempre "
            "full_reload (ver core/loader.py). Usada por vbilaudos.py "
            "(este catálogo) e também por Rastreabilidade (área futura, "
            "conforme comentário no código legado) -- quando migrarmos "
            "Rastreabilidade, ela reaproveita esta mesma tabela na Bronze, "
            "não precisa duplicar. Colunas de empresa/filial não seguem o "
            "padrão CODEMP/CODFIL nem USU_CODEMP/USU_CODFIL -- são EMPNFV/"
            "FILNFV (nomes herdados do join com nota fiscal de venda)."
        ),
    },

]

# ----- VALIDAÇÃO -----

assert len(TABELAS) == 9, f"Esperado 9 tabelas no catálogo, encontrado {len(TABELAS)}"


# ----- TABELAS COMPARTILHADAS (NÃO EXTRAÍDAS AQUI) -----

# Ver docstring do módulo. Definição real fica em
# comercial/bronze/tabelas.py -- aqui é só documentação de dependência.
TABELAS_COMPARTILHADAS_COM_COMERCIAL = [
    "E440NFC",
    "E095FOR",
    "E075PRO",
    "E075DER",
    "E013AGP",
    "E140NFV",
    "E073TRA",
    "E140IPV",
    "E140IDE",
    "E001TNS",
]


# ----- FUNÇÃO AUXILIAR -----

def buscar_tabela(nome: str) -> dict:
    """Retorna a configuração de uma tabela do catálogo pelo nome exato."""
    for t in TABELAS:
        if t["tabela"] == nome:
            return t
    raise KeyError(f"Tabela '{nome}' não encontrada no catálogo da Bronze Laudos RMA.")
