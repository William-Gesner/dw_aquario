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
(diferente do OPEX). ATENÇÃO -- isso é o escopo de NEGÓCIO da empresa
(CODEMP), não uma instrução para a Bronze filtrar CODFIL na extração:
ver Regra 6 do doc_nova_arquitetura.md e a correção de 17/07/2026 em
USU_TLAUITE/USU_TLAUGER/USU_VZRASLAU abaixo (tem_codfil virou False --
vbilaudos.py legado sempre casava filial dinamicamente, nunca fixava
em 1).

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
        "tem_codfil": False,
        "coluna_codfil": "USU_CODFIL",
        "observacao": (
            "Item do laudo (fato principal do vbilaudos.py legado). A query "
            "legada NÃO filtrava USU_CODEMP explicitamente (só herdava via "
            "JOIN) -- mesmo caso do E044CCU no OPEX. Filtramos "
            "USU_CODEMP=1 explicitamente na Bronze, seguindo a regra "
            "estrutural do projeto. CORRIGIDO em 17/07/2026: tem_codfil "
            "virou False -- vbilaudos.py legado não tem NENHUM filtro de "
            "USU_CODFIL no WHERE (só filtra T6.DATENT >= 01/01/2023); "
            "USU_CODFIL só aparece em JOINs dinâmicos (T0.USU_CODFIL = "
            "T1.USU_CODFIL com USU_TLAUGER, T0.USU_CODFIL = T15.FILNFV "
            "com USU_VZRASLAU), nunca fixado em 1. Mesmo padrão de bug já "
            "corrigido no Comercial -- ver Regra 6 do "
            "doc_nova_arquitetura.md."
        ),
    },
    {
        "tabela": "USU_TLAUGER",
        "chaves_pk": ["USU_CODEMP", "USU_CODFIL", "USU_CODLAU"],
        "coluna_data": "USU_DATALT",
        "tem_codemp": True,
        "coluna_codemp": "USU_CODEMP",
        "tem_codfil": False,
        "coluna_codfil": "USU_CODFIL",
        "observacao": (
            "Cabeçalho do laudo. Mesma observação de USU_TLAUITE quanto ao "
            "filtro de empresa. CORRIGIDO em 17/07/2026: mesmo motivo do "
            "USU_TLAUITE -- vbilaudos.py legado casa USU_CODFIL "
            "dinamicamente (T0.USU_CODFIL = T1.USU_CODFIL), nunca fixa em 1."
        ),
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
        "coluna_data": None,
        "tem_codemp": True,
        "coluna_codemp": "USU_CODEMP",
        "tem_codfil": False,
        "observacao": (
            "Cor. Tem USU_CODEMP como coluna, mas a PK real é só USU_CODCOR "
            "(confirmado via ALL_CONS_COLUMNS em 07/07/2026). "
            "CORRIGIDO em 20/07/2026: coluna_data era 'USU_DATALT', com "
            "incremental de 60 dias -- mas é tabela de referência estática "
            "(16 linhas, última alteração real em 2019), então nenhum ciclo "
            "incremental nunca via motivo pra reler. Isso zerava a tabela na "
            "Bronze (upsert com 0 linhas extraídas não apaga o que já existe, "
            "mas nesse caso a 1ª carga real nunca chegou a persistir -- "
            "mesmo mecanismo do bug do E085CLI no Comercial). Achado na "
            "conferência do FAT_LAUDOS: 35 mil linhas divergentes, todas com "
            "USU_DESCOR nulo na Prata vs valor real no legado. coluna_data "
            "virou None -- Bronze relê a tabela inteira (16 linhas, "
            "irrelevante em custo) a cada ciclo."
        ),
    },
    {
        "tabela": "USU_TLAUPRB",
        "chaves_pk": ["USU_CODPRB"],
        "coluna_data": None,
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": (
            "Problema. Tabela global -- sem CODEMP (confirmado via "
            "ALL_TAB_COLUMNS em 07/07/2026). CORRIGIDO em 20/07/2026: mesmo "
            "motivo do USU_TLAUCOR -- 14 linhas, última alteração real em "
            "2014, sempre fora da janela de 60 dias. coluna_data virou None."
        ),
    },
    {
        "tabela": "USU_TLAUSIT",
        "chaves_pk": ["USU_CODSIT"],
        "coluna_data": None,
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": (
            "Situação do laudo. Tabela global -- sem CODEMP (confirmado via "
            "ALL_TAB_COLUMNS em 07/07/2026). CORRIGIDO em 20/07/2026: mesmo "
            "motivo do USU_TLAUCOR -- 9 linhas, última alteração real em "
            "2020, sempre fora da janela de 60 dias. coluna_data virou None."
        ),
    },
    {
        "tabela": "USU_TLAUTIP",
        "chaves_pk": ["USU_CODTIP"],
        "coluna_data": None,
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": (
            "Tipo de laudo. Tabela global -- sem CODEMP (confirmado via "
            "ALL_TAB_COLUMNS em 07/07/2026). CORRIGIDO em 20/07/2026: mesmo "
            "motivo do USU_TLAUCOR -- 3 linhas, última alteração real em "
            "2015, sempre fora da janela de 60 dias. coluna_data virou None."
        ),
    },
    {
        "tabela": "R910USU",
        "chaves_pk": ["CODENT"],
        "coluna_data": "DATALT",
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": (
            "Tabela de usuários do sistema. MESMO NOME que a tabela usada "
            "no OPEX -- aqui a query lê do servidor principal, lá lê da "
            "Controladoria, mas as DUAS gravam na MESMA tabela física "
            "DW_BRONZE.R910USU (schema único do projeto). ATUALIZADO em "
            "18/07/2026: a hipótese anterior ('cada uma com sua própria "
            "cópia na Bronze') estava errada -- confirmado no E044CCU "
            "(mesmo padrão, mesmo par de áreas) que os dois servidores "
            "têm o dado espelhado/sincronizado, não duplicado por "
            "acidente. Risco real: a limpeza de órfãos de uma área "
            "apagando silenciosamente o que só a outra escreve -- "
            "corrigido preventivamente em core/loader.py (DELETE agora "
            "escopado ao filtro de quem chama) mesmo sem esse caso "
            "específico ter estourado ainda aqui. Estrutura validada "
            "independentemente em 07/07/2026 (sem CODEMP, igual à versão "
            "da Controladoria)."
        ),
    },
    {
        "tabela": "USU_VZRASLAU",
        "chaves_pk": None,
        "coluna_data": None,
        "tem_codemp": True,
        "coluna_codemp": "EMPNFV",
        "tem_codfil": False,
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
            "FILNFV (nomes herdados do join com nota fiscal de venda). "
            "CORRIGIDO em 17/07/2026: tem_codfil virou False -- em "
            "vbilaudos.py, o JOIN com USU_VZRASLAU casa "
            "T0.USU_CODFIL = T15.FILNFV dinamicamente (T0 = USU_TLAUITE, "
            "sem filtro fixo de filial); em vbirastreabilidade.py "
            "(consumidor futuro desta mesma tabela), o casamento com "
            "QRC/PVD também é dinâmico (QRC.USU_CODFIL = PVD.FILNFV), mas "
            "ali IPV.CODFIL=1 já está fixado no WHERE -- ou seja, o "
            "escopo de filial é decidido pela query CONSUMIDORA em cada "
            "caso, não pela Bronze. Ver também USU_T140QRC na "
            "Rastreabilidade (caso em que tem_codfil=True é correto, por "
            "causa dessa mesma dinâmica vista do outro lado)."
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


# ----- TABELAS COM MAIS DE UM ESCRITOR NA BRONZE -----
#
# Diferente de TABELAS_COMPARTILHADAS_COM_COMERCIAL (onde o Laudos RMA só
# DEPENDE, sem extrair): a tabela abaixo É extraída aqui de propósito, em
# paralelo com o OPEX, pro MESMO destino na Bronze -- cada um só enxerga
# uma fatia (servidor Oracle diferente). Ver observação da tabela, e
# doc_nova_arquitetura.md pro caso real encontrado no E044CCU (mesmo
# padrão) em 18/07/2026.
#
# Usado por conferencias/dw_bronze/conferencia_laudos.py: nessa tabela,
# Bronze > universo próprio do Laudos RMA seria ESPERADO (a fatia extra
# viria do OPEX) -- só Bronze < universo próprio é erro de verdade.
TABELAS_MULTI_ESCRITOR = {
    "R910USU": "OPEX também extrai esta tabela (via Controladoria) -- ver observação da tabela.",
}


# ----- FUNÇÃO AUXILIAR -----

def buscar_tabela(nome: str) -> dict:
    """Retorna a configuração de uma tabela do catálogo pelo nome exato."""
    for t in TABELAS:
        if t["tabela"] == nome:
            return t
    raise KeyError(f"Tabela '{nome}' não encontrada no catálogo da Bronze Laudos RMA.")
