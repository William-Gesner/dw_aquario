"""
Conferência FAT_DESEMPENHO_PRODUCAO (Prata) x USU_VBIAPROD_DESEMPENHO
(legado, schema BIAQUARIO) -- compara os DADOS, não só a contagem.

Ver conferencia_dim_condicao_pagamento.py para a explicação completa da
técnica base (MINUS nos dois sentidos). Só leitura -- não corrige nem
apaga nada.

COLUNAS DINÂMICAS (não hardcoded): ~37 colunas, risco real de erro de
transcrição manual -- mesma técnica já usada em conferencia_fat_laudos.py
(Laudos RMA) e conferencia_dim_indice_rma.py. Em vez de uma lista
COLUNAS fixa, consulta ALL_TAB_COLUMNS dos dois lados em tempo de
execução e compara a INTERSEÇÃO das colunas (excluindo metadado
técnico).

CORTE DE DATA: a Prata usa 01/01/2021 (DATA_CORTE_PRODUCAO), mas o CAMPO
cortado é DIFERENTE por bloco (TIPTAB) -- não dá pra usar só DATREA pros
4 de uma vez:

    TIPTAB 1 (DESEMPENHO) -- corta por DTRINI (início real da OP), que é
        DIFERENTE do DATREA de saída (data do apontamento) -- uma OP
        iniciada antes do corte pode ter apontamentos com DATREA depois
        do corte, e vice-versa.
    TIPTAB 2 (CONSUMO)    -- corta por DATMOV, que É a própria coluna
        DATMOV de saída (mapeamento direto).
    TIPTAB 3 (PARADAS) e 4 (CUSTO_CC) -- cortam por um campo que já É
        mapeado 1:1 pro DATREA de saída (DATMPR/DATINI), sem essa
        diferença. MAS o OPERADOR é diferente entre os dois: TIPTAB=3 usa
        `>` estrito (exclui o dia exato do corte -- assim sempre foi, no
        legado e na Prata, ver "BUG CORRIGIDO (23/07/2026): corte de
        TIPTAB=3 usa operador diferente" abaixo); TIPTAB=4 usa `>=`
        (inclusive).

BUG CORRIGIDO (23/07/2026): esta conferência aplicava DATREA >= corte
pros 4 blocos de uma vez -- pra TIPTAB=1/2 isso gera falsos positivos
("só no legado"), porque compara um campo (DATREA) diferente do que a
extração realmente usa pra cortar (DTRINI/DATMOV). Corrigido filtrando
o lado do legado por TIPTAB, cada um com o campo certo -- mesma lógica
usada na extração (fat_desempenho_producao.py).

----------------------------------------------------------------------
JANELA DE ESTABILIZAÇÃO (23/07/2026): não compara os últimos 2 dias
----------------------------------------------------------------------
A fábrica não para -- Sapiens recebe lançamentos o tempo todo, e é comum
um apontador registrar hoje um consumo/apontamento com data de ontem ou
anteontem (lançamento atrasado, data de negócio != data de gravação no
banco). Como o legado (BIAQUARIO) e a Prata são extraídos em momentos
DIFERENTES (nunca exatamente simultâneos), qualquer linha lançada no
Sapiens entre os dois momentos aparece só de um lado -- não por bug de
lógica, mas porque os dois lados fotografaram o Sapiens em instantes
diferentes de uma fonte que nunca para de mudar. Testado na prática em
23/07/2026: pausar o legado e rodar a Prata alguns minutos depois NÃO
elimina a divergência -- ela muda de linha (sempre as mais recentes),
confirmando que é isso, não um bug de query.

Solução: a comparação (só a comparação -- a tabela em si continua com
tudo, sem esse filtro) ignora os últimos JANELA_ESTABILIZACAO_DIAS dias.
Depois desse prazo, os lançamentos atrasados já devem ter sido gravados
dos dois lados -- se ainda sobrar divergência de um período já
"assentado" (mais antigo que a janela), aí sim é bug de verdade, não
timing.

CORRIGIDO (23/07/2026): o teto da janela NÃO usa o mesmo campo do corte
de baixo pro TIPTAB=1. O corte de baixo usa DTRINI (início da OP) porque
é isso que a extração usa pra decidir se a OP entra ou não no recorte de
2021. Mas pra saber se uma LINHA específica já "assentou" (não vai
ganhar companhia nova), o campo certo é DATREA (data do apontamento
daquela linha) -- uma OP pode ter começado há meses (DTRINI antigo) e
ainda assim ganhar apontamentos novos hoje. Achado real (23/07/2026):
uma OP com DTRINI de 17/07 tinha 2 apontamentos reais no mesmo dia
(22/07, SEQEOQ diferentes) -- um mais antigo, outro lançado há pouco.
Usando DTRINI como teto, a linha "parecia" assentada (17/07 já tem mais
de 2 dias) mas na verdade o segundo apontamento (22/07) ainda era
recente demais -- causando SUM(QTDPRV) dobrado só na Prata (fan-out do
JOIN com E900QDO quando o GROUP BY agrupa 2 apontamentos do mesmo dia).
Confirmado que Bronze e Sapiens tinham os DOIS apontamentos idênticos --
não é duplicação de dado, é o legado ainda não ter recalculado essa
linha desde que o 2º apontamento apareceu. Corrigido usando DATREA
(não DTRINI) no teto do TIPTAB=1 -- DATMOV (TIPTAB=2) e DATREA
(TIPTAB=3/4) já estavam certos, são campos por linha desde o início.

CORRIGIDO (23/07/2026): TIPTAB=2 precisa excluir o MÊS CORRENTE inteiro,
não só os últimos N dias. `QTDTOP` (fat_desempenho_producao.py) é uma
soma de TODOS os apontamentos do mesmo mês/ano daquele estágio (casamento
por TO_CHAR(DATREA,'MM/YYYY'), não por dia) -- enquanto o mês não fecha,
qualquer novo apontamento lançado muda QTDTOP de TODAS as linhas de
CONSUMO daquele mês/estágio, mesmo linhas com DATMOV de 1-2 semanas atrás
(já "velhas" pelo critério de dia, mas ainda dentro do mês em aberto).
Achado real: linha com DATMOV=17/07 (10 dias antes do teste, já fora da
janela de 2 dias) ainda divergia (QTDTOP=2506 na Prata x 1847 no legado)
porque um apontamento novo de outro dia do mesmo mês mudou a soma.
Janela de 2 dias não resolve isso -- corrigido excluindo o TIPTAB=2 do
mês corrente inteiro (comparação só entra em vigor a partir do 1º dia do
mês seguinte).

BUG CORRIGIDO (23/07/2026): corte de TIPTAB=3 usa operador diferente do
TIPTAB=4. Sobrou 1 única divergência depois de todos os fixes acima:
uma linha PARADAS com DATREA=01/01/2021 exato -- o primeiro dia do
corte. A extração usa `T0.DATMPR > corte` (estritamente maior, exclui o
dia exato) no bloco PARADAS -- mesmo operador do legado (`vbidesempenho.py`
usa `>` ali também, sempre foi assim, não é bug de migração). Já o bloco
CUSTO_CC usa `T2.DATINI >= corte` (inclusive). O corte de baixo desta
conferência usava `>=` pros dois blocos igualmente -- reinserindo
artificialmente essa linha de fronteira no lado do legado (ela nunca
devia estar no recorte, nem lá nem cá). Corrigido usando `>` só pro
TIPTAB=3, `>=` pro TIPTAB=4 -- mesmos operadores da extração.

PRÉ-REQUISITO: GRANT SELECT ON BIAQUARIO.USU_VBIAPROD_DESEMPENHO TO DW_PRATA;

Uso:
    python -m conferencias.dw_prata.conferencia_fat_desempenho_producao
"""

# ----- IMPORTS -----

from sqlalchemy import text

from core.db import get_engine_prata
from producao.config.settings import DATA_CORTE_PRODUCAO

# ----- CONFIGURAÇÃO -----

SCHEMA_PRATA = "DW_PRATA"
TABELA_PRATA = "FAT_DESEMPENHO_PRODUCAO"

SCHEMA_LEGADO = "BIAQUARIO"
TABELA_LEGADO = "USU_VBIAPROD_DESEMPENHO"

# Metadado técnico da Prata -- nunca existe no legado, fica fora da comparação.
COLUNAS_EXCLUIDAS = {"DW_DATA_PROCESSAMENTO", "DW_DATA_INGESTAO"}

# Não compara os últimos N dias -- lançamento atrasado no Sapiens (data de
# negócio != data de gravação) faz um lado ter uma linha que o outro ainda
# não capturou, sem ser bug (ver docstring "JANELA DE ESTABILIZAÇÃO" acima).
JANELA_ESTABILIZACAO_DIAS = 2


def filtro_por_tiptab(regras: dict[int, str]) -> str:
    """
    Monta a condição por TIPTAB -- `regras` é {tiptab: "condicao_sql"},
    permitindo campo/operador diferentes por bloco (ver docstring
    "CORTE DE DATA" -- TIPTAB=3 usa `>` estrito, os outros usam `>=`).
    """
    return " OR ".join(f"(TIPTAB = {tiptab} AND {cond})" for tiptab, cond in regras.items())


# ----- FUNÇÕES -----

def colunas_reais(conn, schema: str, tabela: str) -> set:
    """Lista as colunas reais de uma tabela via ALL_TAB_COLUMNS."""
    query = """
        SELECT column_name
        FROM ALL_TAB_COLUMNS
        WHERE owner = :schema AND table_name = :tabela
    """
    linhas = conn.execute(text(query), {"schema": schema, "tabela": tabela}).fetchall()
    if not linhas:
        raise ValueError(f"Nenhuma coluna encontrada para {schema}.{tabela} em ALL_TAB_COLUMNS.")
    return {linha[0] for linha in linhas}


def contar(conn, schema: str, tabela: str) -> int:
    return conn.execute(text(f"SELECT COUNT(*) FROM {schema}.{tabela}")).scalar()


def divergencias(conn, origem: str, destino: str, colunas: list[str]) -> list:
    colunas_str = ", ".join(colunas)
    query = f"""
        SELECT {colunas_str} FROM {origem}
        MINUS
        SELECT {colunas_str} FROM {destino}
    """
    return conn.execute(text(query)).fetchall()


# ----- EXECUÇÃO -----

if __name__ == "__main__":
    engine = get_engine_prata()

    with engine.connect() as conn:
        cols_prata  = colunas_reais(conn, SCHEMA_PRATA, TABELA_PRATA)
        cols_legado = colunas_reais(conn, SCHEMA_LEGADO, TABELA_LEGADO)
        colunas     = sorted((cols_prata & cols_legado) - COLUNAS_EXCLUIDAS)

        so_prata_cols  = sorted(cols_prata - cols_legado - COLUNAS_EXCLUIDAS)
        so_legado_cols = sorted(cols_legado - cols_prata)

        # Corte de baixo (01/01/2021) por TIPTAB -- mesmo campo E MESMO
        # OPERADOR que a extração usa pra cortar (ver docstring "CORTE DE
        # DATA"). TIPTAB=3 usa `>` estrito (igual à extração e ao legado),
        # os outros usam `>=`.
        _corte_data = f"TO_DATE('{DATA_CORTE_PRODUCAO}', 'DD/MM/YYYY')"
        corte_baixo = filtro_por_tiptab({
            1: f"DTRINI >= {_corte_data}",
            2: f"DATMOV >= {_corte_data}",
            3: f"DATREA > {_corte_data}",
            4: f"DATREA >= {_corte_data}",
        })
        # Janela de estabilização (<= hoje - N dias) -- CUIDADO: pro TIPTAB=1,
        # o teto usa DATREA (data do apontamento em si), NÃO DTRINI (início
        # da OP). Achado em 23/07/2026: uma OP pode ter começado há dias
        # (DTRINI antigo) e ainda assim ganhar apontamentos novos HOJE --
        # usar DTRINI aqui deixava passar linhas com DATREA de ontem/hoje
        # achando que já tinham "assentado" só porque a OP era antiga.
        # DTRINI é atributo da OP (não muda por linha); DATREA é por linha
        # -- é isso que precisa estar "velho" pra garantir estabilidade.
        #
        # TIPTAB=2 é tratado à parte (não usa filtro_por_tiptab): QTDTOP é
        # soma do MÊS CORRENTE inteiro (ver docstring "CORRIGIDO ...
        # TIPTAB=2 precisa excluir o MÊS CORRENTE"), então o teto pra esse
        # bloco exclui o mês em andamento inteiro, não só os últimos N dias.
        janela_topo = (
            f"(TIPTAB = 1 AND DATREA <= TRUNC(SYSDATE) - {JANELA_ESTABILIZACAO_DIAS}) "
            f"OR (TIPTAB = 2 AND DATMOV < TRUNC(SYSDATE, 'MM')) "
            f"OR (TIPTAB IN (3, 4) AND DATREA <= TRUNC(SYSDATE) - {JANELA_ESTABILIZACAO_DIAS})"
        )

        # CODEMP = 1 do lado do legado -- a query de vbidesempenho.py (bloco
        # CONSUMO) nunca filtrou CODEMP explicitamente, então o legado
        # acumulou registros de outras empresas (ex.: CODEMP=50) que nunca
        # deveriam ter entrado (Regra 6 -- todo o projeto assume CODEMP=1).
        # A Prata nunca teve esse problema porque a Bronze já filtra
        # CODEMP=1 na origem (ver producao/bronze/tabelas.py, E210MVP). Sem
        # esse filtro aqui, esses registros apareciam como "só no legado" --
        # ruído fora de escopo, não divergência real.
        legado_estavel = (
            f"(SELECT {', '.join(colunas)} FROM {SCHEMA_LEGADO}.{TABELA_LEGADO} "
            f"WHERE CODEMP = 1 AND ({corte_baixo}) AND ({janela_topo}))"
        )
        prata_estavel = (
            f"(SELECT {', '.join(colunas)} FROM {SCHEMA_PRATA}.{TABELA_PRATA} "
            f"WHERE ({janela_topo}))"
        )

        total_prata           = contar(conn, SCHEMA_PRATA, TABELA_PRATA)
        total_legado_completo = contar(conn, SCHEMA_LEGADO, TABELA_LEGADO)
        total_legado_corte    = conn.execute(text(f"SELECT COUNT(*) FROM {legado_estavel} X")).scalar()
        total_prata_estavel   = conn.execute(text(f"SELECT COUNT(*) FROM {prata_estavel} X")).scalar()

        so_na_prata  = divergencias(conn, prata_estavel, legado_estavel, colunas)
        so_no_legado = divergencias(conn, legado_estavel, prata_estavel, colunas)

    print(f"\n{'='*70}")
    print(f"  CONFERÊNCIA -- {TABELA_PRATA} (Prata) x {TABELA_LEGADO} (legado, >= {DATA_CORTE_PRODUCAO})")
    print(f"  Janela de estabilização: ignora os últimos {JANELA_ESTABILIZACAO_DIAS} dias dos 2 lados")
    print(f"{'='*70}")
    print(f"  Colunas comparadas: {len(colunas)}")
    if so_prata_cols:
        print(f"  [AVISO] Colunas só na Prata (fora da comparação): {so_prata_cols}")
    if so_legado_cols:
        print(f"  [AVISO] Colunas só no legado (fora da comparação): {so_legado_cols}")
    print(f"  Linhas na Prata (total, sem filtro)      : {total_prata:>10,}")
    print(f"  Linhas no legado (histórico completo)    : {total_legado_completo:>10,}")
    print(f"  Linhas na Prata (dentro da janela estável)  : {total_prata_estavel:>10,}")
    print(f"  Linhas no legado (>= {DATA_CORTE_PRODUCAO}, dentro da janela estável) : {total_legado_corte:>10,}")
    print(f"  Só na Prata (sem equivalente idêntico no legado)  : {len(so_na_prata):>6,}")
    print(f"  Só no legado (sem equivalente idêntico na Prata)  : {len(so_no_legado):>6,}")

    if not so_na_prata and not so_no_legado:
        print(f"\n  [OK] Dados idênticos (dentro do corte de {DATA_CORTE_PRODUCAO} e da janela estável) -- todas as colunas de negócio batem.")
    else:
        print(f"\n  [DIVERGENTE] Diferenças encontradas.")

        if so_na_prata:
            print(f"\n  --- Amostra: só na Prata (até 10 de {len(so_na_prata)}) ---")
            for linha in so_na_prata[:10]:
                print(f"    {linha}")

        if so_no_legado:
            print(f"\n  --- Amostra: só no legado (até 10 de {len(so_no_legado)}) ---")
            for linha in so_no_legado[:10]:
                print(f"    {linha}")

    print(f"{'='*70}")
