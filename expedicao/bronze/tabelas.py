"""
Catálogo das tabelas Sapiens que formam a camada Bronze da Expedição.

Cada entrada descreve:
    tabela        : nome exato da tabela/view no Sapiens. Na Bronze, fica
                    com o MESMO nome (cópia crua, sem transformação).
    chaves_pk     : PK real, validada via ALL_TAB_COLUMNS/ALL_CONS_COLUMNS
                    em 13/07/2026. None só para USU_V120EST, que é VIEW
                    sem PK física -- ver core/loader.py carregar_bronze():
                    quando chaves_pk é None, a carga é SEMPRE full_reload
                    (nunca tenta MERGE).
    coluna_data   : coluna usada no filtro de janela de 60 dias na carga
                    incremental. None = sem coluna de auditoria confiável
                    -- tabela sempre via full_reload.
    tem_codemp    : se True, a query filtra pela coluna de empresa real.
    coluna_codemp : nome real da coluna de empresa. Ausente quando
                    tem_codemp=False (tabela global do sistema).
    tem_codfil    : se True, filtra também pela coluna de filial real.
    coluna_codfil : nome real da coluna de filial ("CODFIL" quando
                    aplicável).
    observacao    : contexto levantado na validação.

REGRA DE EMPRESA/FILIAL: igual ao resto do projeto -- CODEMP = 1 e
CODFIL = 1 sempre (ver expedicao.config.settings), quando a tabela tem
essas colunas. Sem exceção aqui (diferente do OPEX).

TABELAS COMPARTILHADAS COM O COMERCIAL -- NÃO EXTRAÍDAS AQUI:
    A Expedição também depende de E120PED, E069GRE, E085CLI (usadas em
    vbiexpedicao.py legado). Já são mantidas atualizadas pelo
    comercial/bronze/tabelas.py -- extrair de novo aqui seria trabalho
    redobrado. Definição real fica só no catálogo do Comercial. Listadas
    abaixo só para rastreio de dependência -- ver
    TABELAS_COMPARTILHADAS_COM_COMERCIAL.

FORA DE ESCOPO -- NÃO É TABELA SAPIENS:
    vbiexpedicao.py legado também lê BIAQUARIO.USU_BVIACLIENTES e
    BIAQUARIO.USU_VBIREPRESENTANTES (schema legado antigo) para
    enriquecer NOMCLI/NOMVEN por merge Python. Isso é enriquecimento --
    lógica de Prata, não entra no catálogo da Bronze.
"""

# ----- CATÁLOGO DE TABELAS (EXCLUSIVAS DA EXPEDIÇÃO) -----

TABELAS = [

    {
        "tabela": "R900GRP",
        "chaves_pk": ["GRPID", "MEMID"],
        "coluna_data": None,
        "tem_codemp": False,
        "tem_codfil": False,
        "observacao": (
            "Tabela de grupos/membros de usuário (módulo de segurança do "
            "Sapiens) -- só 2 colunas (GRPID, MEMID), confirmadas via "
            "ALL_TAB_COLUMNS em 13/07/2026, sem CODEMP/CODFIL (tabela "
            "global do sistema, não por empresa). Usada no legado "
            "(vbiexpedicao.py) dentro de um EXISTS pra restringir os "
            "pedidos aos usuários que fecharam (USUFEC) pertencentes aos "
            "grupos do setor de expedição (GRPID 1073741825/1073741912) "
            "-- essa whitelist de GRPID é regra de negócio e fica pra "
            "Prata; aqui na Bronze trazemos o universo completo, sem "
            "filtro algum. PK real confirmada via ALL_CONS_COLUMNS: "
            "GRPID+MEMID. Sem coluna de auditoria -- full_reload sempre. "
            "Volume pequeno (2.527 linhas)."
        ),
    },
    {
        "tabela": "USU_V120EST",
        "chaves_pk": None,
        "coluna_data": None,
        "tem_codemp": True,
        "coluna_codemp": "CODEMP",
        "tem_codfil": True,
        "coluna_codfil": "CODFIL",
        "observacao": (
            "View liberada pela DBS em Junho/2026 (não existia neste "
            "ambiente antes) -- traz QTDPRB (quantidade em prova) pro "
            "fato de pedidos da Expedição, via LEFT JOIN por "
            "CODEMP+CODFIL+NUMPED. Sem PK física -- confirmado em "
            "13/07/2026 via ALL_CONS_COLUMNS (não retornou nenhuma linha "
            "para esta tabela), mesmo tratamento do USU_VZRASLAU no "
            "Laudos RMA: chaves_pk=None, sempre full_reload (ver "
            "core/loader.py). Volume confirmado: 25.308 linhas "
            "(consistente com as ~25.454 citadas no legado)."
        ),
    },

]

# ----- VALIDAÇÃO -----

assert len(TABELAS) == 2, f"Esperado 2 tabelas no catálogo, encontrado {len(TABELAS)}"


# ----- TABELAS COMPARTILHADAS (NÃO EXTRAÍDAS AQUI) -----

# Ver docstring do módulo. Definição real fica em
# comercial/bronze/tabelas.py -- aqui é só documentação de dependência.
TABELAS_COMPARTILHADAS_COM_COMERCIAL = [
    "E120PED",
    "E069GRE",
    "E085CLI",
]


# ----- FUNÇÃO AUXILIAR -----

def buscar_tabela(nome: str) -> dict:
    """Retorna a configuração de uma tabela do catálogo pelo nome exato."""
    for t in TABELAS:
        if t["tabela"] == nome:
            return t
    raise KeyError(f"Tabela '{nome}' não encontrada no catálogo da Bronze Expedição.")
