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
ATENÇÃO -- isso é o escopo de NEGÓCIO da empresa (CODEMP), não uma
instrução para a Bronze filtrar CODFIL na extração: ver Regra 6 do
doc_nova_arquitetura.md e a correção de 17/07/2026 em E210MVP/E621MTC/
E900COP/E930MPR abaixo (tem_codfil virou False -- vbidesempenho.py
legado nunca fixava filial nessas 4 tabelas).

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
        "coluna_data": None,
        "tem_codemp": True,
        "coluna_codemp": "CODEMP",
        "tem_codfil": False,
        "observacao": (
            "Centros de custo. MESMO NOME que a tabela usada no OPEX -- "
            "aqui a query lê do servidor principal (CODEMP=1), lá lê da "
            "Controladoria (CODEMP IN (1,50)), mas as DUAS gravam na "
            "MESMA tabela física DW_BRONZE.E044CCU (schema único do "
            "projeto). CONFIRMADO em 18/07/2026: NÃO são cópias "
            "separadas como se pensava antes -- os dois servidores têm "
            "os centros de custo espelhados/sincronizados (contagem por "
            "CODEMP bate 100% nos dois lados, todas as 12 empresas). "
            "Bug real encontrado (1): a limpeza de órfãos da Produção "
            "(que só enxerga CODEMP=1) apagou as 244 linhas de CODEMP=50 "
            "que só o OPEX consegue trazer, achando que eram órfãs. "
            "Corrigido em core/loader.py (remover_orfaos()/remover_orfaos_"
            "cross_servidor() agora escopam o DELETE ao filtro de quem "
            "chama, nunca tocam fora dele) -- ver doc_nova_arquitetura.md. "
            "Bug real encontrado (2): coluna_data virou None -- DATALT "
            "fica NULL em linha nova (364 linhas confirmadas via "
            "auditoria, mesmo número nos dois servidores) e a tabela NÃO "
            "tem nenhuma outra coluna de data (sem DATGER/HORGER "
            "equivalente, confirmado via amostra de linhas) -- sem "
            "fallback possível, igual ao caso do E085CLI no Comercial. "
            "Tabela pequena (~1.300 linhas no universo completo), custo "
            "de reler tudo a cada ciclo é desprezível. Mesmo caso do "
            "R910USU no Laudos RMA. Estrutura validada independentemente "
            "em 08/07/2026."
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
        "tem_codfil": False,
        "coluna_codfil": "CODFIL",
        "observacao": (
            "Movimentação de produtos (consumo de matéria-prima). Tabela "
            "grande (~140 colunas na origem) -- full_reload_streaming na "
            "1ª carga, mesmo tratamento do E120IPD no Comercial. "
            "CORRIGIDO em 17/07/2026: tem_codfil virou False -- bloco "
            "TIPTAB=2 (CONSUMO) de vbidesempenho.py legado nunca referencia "
            "CODFIL do E210MVP em nenhum JOIN ou WHERE (só CODEMP, via "
            "T0.CODEMP nos JOINs). Mesmo padrão de bug já corrigido no "
            "Comercial -- ver Regra 6 do doc_nova_arquitetura.md."
        ),
    },
    {
        "tabela": "E621MTC",
        "chaves_pk": ["NUMMTC"],
        "coluna_data": "DATATU",
        "tem_codemp": True,
        "coluna_codemp": "CODEMP",
        "tem_codfil": False,
        "coluna_codfil": "CODFIL",
        "observacao": (
            "Mapa de cálculo (orçamento/custo). PK real é só NUMMTC "
            "(confirmado via ALL_CONS_COLUMNS em 08/07/2026) -- CODEMP e "
            "CODFIL existem como coluna mas não fazem parte da PK. "
            "CORRIGIDO em 17/07/2026: tem_codfil virou False -- "
            "vbidesempenho.py legado usa E621MTC em 2 pontos (subconsulta "
            "TAXREA no bloco TIPTAB=1, e JOIN no bloco TIPTAB=4), nenhum "
            "dos dois referencia CODFIL -- só CODEMP e NUMMTC. Mesmo "
            "padrão de bug já corrigido no Comercial."
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
        "tem_codfil": False,
        "coluna_codfil": "CODFIL",
        "observacao": (
            "Cabeçalho da ordem de produção. CORRIGIDO em 17/07/2026: "
            "tem_codfil virou False -- vbidesempenho.py legado junta "
            "E900COP (como T0) em 2 blocos (TIPTAB=1 e TIPTAB=2) só por "
            "CODEMP+CODORI+NUMORP, nunca por CODFIL (a tabela nem tem "
            "coluna CODFIL referenciada na query). Mesmo padrão de bug já "
            "corrigido no Comercial."
        ),
    },
    {
        "tabela": "E900EOQ",
        "chaves_pk": ["CODEMP", "CODORI", "NUMORP", "CODETG", "SEQEOQ"],
        "coluna_data": "DATREA",
        "data_sentinela": "1900-12-31",
        "tem_codemp": True,
        "coluna_codemp": "CODEMP",
        "tem_codfil": False,
        "observacao": (
            "Apontamento de produção por OP/estágio/data -- provavelmente "
            "a maior tabela nova desta área (usada em 4 subconsultas "
            "correlacionadas dentro de vbidesempenho.py). Full_reload_"
            "streaming na 1ª carga, mesmo tratamento do E120IPD. "
            "BUG CORRIGIDO EM 09/07/2026: DATREA usa 1900-12-31 como "
            "sentinela de \"sem data definida\" (apontamento ainda "
            "pendente/não finalizado -- mesma convenção já vista em "
            "DATFIN no Laudos RMA legado). Como 1900-12-31 nunca satisfaz "
            "DATREA >= SYSDATE-60, linha nova com esse valor ficava "
            "permanentemente fora do incremental (confirmado via "
            "conferência: 3 linhas nunca chegavam na Bronze, sempre as "
            "mesmas, em execuções sucessivas). data_sentinela faz o "
            "filtro incremental sempre incluir essas linhas também, até "
            "ganharem uma data real."
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
        "tem_codfil": False,
        "coluna_codfil": "CODFIL",
        "observacao": (
            "Histórico de paradas de equipamento/centro de recurso. "
            "CORRIGIDO em 17/07/2026: tem_codfil virou False -- bloco "
            "TIPTAB=3 (PARADAS) de vbidesempenho.py legado (WHERE "
            "T0.DATMPR > data_corte) não filtra CODFIL nenhum, nem no "
            "WHERE nem nos JOINs (E018MTV, E093ETG, E044CCU casam só por "
            "CODEMP). Mesmo padrão de bug já corrigido no Comercial."
        ),
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


# ----- TABELAS COM MAIS DE UM ESCRITOR NA BRONZE -----
#
# Diferente de TABELAS_COMPARTILHADAS_COM_COMERCIAL (onde a Produção só
# DEPENDE, sem extrair): as tabelas abaixo SÃO extraídas aqui de
# propósito, em paralelo com outra área, pro MESMO destino na Bronze --
# porque cada uma só consegue ver uma fatia dos dados (servidor Oracle
# diferente). Ver observação de cada tabela pra detalhe completo, e
# doc_nova_arquitetura.md pro caso real encontrado em 18/07/2026 (bug de
# limpeza de órfãos apagando a fatia da outra área -- corrigido em
# core/loader.py).
#
# Usado por conferencias/dw_bronze/conferencia_producao.py: nessas
# tabelas, Bronze > universo próprio da Produção é ESPERADO (a fatia
# extra vem da outra área) -- só Bronze < universo próprio é erro de
# verdade.
TABELAS_MULTI_ESCRITOR = {
    "E044CCU": "OPEX também extrai esta tabela (CODEMP=50, via Controladoria) -- ver observação da tabela.",
}


# ----- FUNÇÃO AUXILIAR -----

def buscar_tabela(nome: str) -> dict:
    """Retorna a configuração de uma tabela do catálogo pelo nome exato."""
    for t in TABELAS:
        if t["tabela"] == nome:
            return t
    raise KeyError(f"Tabela '{nome}' não encontrada no catálogo da Bronze Produção.")
