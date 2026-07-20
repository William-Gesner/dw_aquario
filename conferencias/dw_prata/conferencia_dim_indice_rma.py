"""
Conferência DIM_INDICE_RMA (Prata) x USU_VBIARMA_INDICE_RMA (legado,
schema BIAQUARIO) -- compara os DADOS, não só a contagem.

Ver conferencia_dim_condicao_pagamento.py (Comercial) para a explicação
completa da técnica (MINUS nos dois sentidos). Só leitura -- não corrige
nem apaga nada.

DIFERENTE das outras conferências desta área: aqui a lista de colunas
NÃO é hardcoded. dim_indice_rma.py lê o Excel (IndiceRMA.xlsx, aba
Planilha1) sem selecionar/renomear colunas explicitamente -- então o
conjunto real de colunas depende do que está na planilha (não documentado
linha a linha em código, ao contrário das outras 4 tabelas desta área).
Hardcodar uma lista aqui seria arriscar comparar com o nome errado sem
perceber. Em vez disso, as colunas comparadas são calculadas em tempo de
execução via ALL_TAB_COLUMNS -- a interseção do que existe nos dois
lados, excluindo metadado técnico.

PRÉ-REQUISITO: GRANT SELECT ON BIAQUARIO.USU_VBIARMA_INDICE_RMA TO DW_PRATA;

Uso:
    python -m conferencias.dw_prata.conferencia_dim_indice_rma
"""

# ----- IMPORTS -----

from sqlalchemy import text

from core.db import get_engine_prata

# ----- CONFIGURAÇÃO -----

SCHEMA_PRATA = "DW_PRATA"
TABELA_PRATA = "DIM_INDICE_RMA"

SCHEMA_LEGADO = "BIAQUARIO"
TABELA_LEGADO = "USU_VBIARMA_INDICE_RMA"

# Colunas técnicas/metadado -- nunca entram na comparação de negócio
COLUNAS_EXCLUIDAS = {"DW_DATA_PROCESSAMENTO", "DW_DATA_INGESTAO"}


# ----- FUNÇÕES -----

def colunas_da_tabela(conn, owner: str, tabela: str) -> set:
    query = "SELECT column_name FROM ALL_TAB_COLUMNS WHERE owner = :owner AND table_name = :tabela"
    linhas = conn.execute(text(query), {"owner": owner, "tabela": tabela}).fetchall()
    return {linha[0] for linha in linhas}


def colunas_comuns(conn, schema_prata: str, tabela_prata: str, schema_legado: str, tabela_legado: str) -> list:
    """
    Interseção das colunas que existem nas DUAS tabelas (via
    ALL_TAB_COLUMNS), excluindo metadado técnico -- evita risco de
    hardcodar um nome de coluna errado numa tabela cuja estrutura real
    vem de um Excel não documentado linha a linha no código.
    """
    cols_prata = colunas_da_tabela(conn, schema_prata, tabela_prata) - COLUNAS_EXCLUIDAS
    cols_legado = colunas_da_tabela(conn, schema_legado, tabela_legado) - COLUNAS_EXCLUIDAS
    comuns = cols_prata & cols_legado

    so_prata = cols_prata - cols_legado
    so_legado = cols_legado - cols_prata
    if so_prata:
        print(f"  [AVISO] Colunas só na Prata (fora da comparação): {sorted(so_prata)}")
    if so_legado:
        print(f"  [AVISO] Colunas só no legado (fora da comparação): {sorted(so_legado)}")

    return sorted(comuns)


def contar(conn, schema: str, tabela: str) -> int:
    return conn.execute(text(f"SELECT COUNT(*) FROM {schema}.{tabela}")).scalar()


def divergencias(conn, origem: str, destino: str, colunas: list) -> list:
    colunas_str = ", ".join(f'"{c}"' for c in colunas)
    query = f"""
        SELECT {colunas_str} FROM {origem}
        MINUS
        SELECT {colunas_str} FROM {destino}
    """
    return conn.execute(text(query)).fetchall()


# ----- EXECUÇÃO -----

if __name__ == "__main__":
    engine = get_engine_prata()

    prata_full = f"{SCHEMA_PRATA}.{TABELA_PRATA}"
    legado_full = f"{SCHEMA_LEGADO}.{TABELA_LEGADO}"

    with engine.connect() as conn:
        colunas = colunas_comuns(conn, SCHEMA_PRATA, TABELA_PRATA, SCHEMA_LEGADO, TABELA_LEGADO)

        total_prata = contar(conn, SCHEMA_PRATA, TABELA_PRATA)
        total_legado = contar(conn, SCHEMA_LEGADO, TABELA_LEGADO)

        so_na_prata = divergencias(conn, prata_full, legado_full, colunas)
        so_no_legado = divergencias(conn, legado_full, prata_full, colunas)

    print(f"\n{'='*70}")
    print(f"  CONFERÊNCIA -- {TABELA_PRATA} (Prata) x {TABELA_LEGADO} (legado)")
    print(f"{'='*70}")
    print(f"  Colunas comparadas: {len(colunas)}")
    print(f"  Linhas na Prata  : {total_prata:>10,}")
    print(f"  Linhas no legado : {total_legado:>10,}")
    print(f"  Só na Prata (sem equivalente idêntico no legado)  : {len(so_na_prata):>6,}")
    print(f"  Só no legado (sem equivalente idêntico na Prata)  : {len(so_no_legado):>6,}")

    if not so_na_prata and not so_no_legado:
        print(f"\n  [OK] Dados idênticos -- todas as colunas de negócio batem.")
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
