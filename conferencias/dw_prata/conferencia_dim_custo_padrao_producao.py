"""
Conferência DIM_CUSTO_PADRAO_PRODUCAO (Prata) x USU_VBIAPROD_CUSTO_PADRAO
(legado, schema BIAQUARIO) -- compara os DADOS, não só a contagem.

Ver conferencia_dim_condicao_pagamento.py para a explicação completa da
técnica (MINUS nos dois sentidos). Só leitura -- não corrige nem apaga
nada. Sem corte de data (dimensão) -- universo completo dos dois lados.

PRÉ-REQUISITO: GRANT SELECT ON BIAQUARIO.USU_VBIAPROD_CUSTO_PADRAO TO DW_PRATA;

Uso:
    python -m conferencias.dw_prata.conferencia_dim_custo_padrao_producao
"""

# ----- IMPORTS -----

from sqlalchemy import text

from core.db import get_engine_prata

# ----- CONFIGURAÇÃO -----

SCHEMA_PRATA = "DW_PRATA"
TABELA_PRATA = "DIM_CUSTO_PADRAO_PRODUCAO"

SCHEMA_LEGADO = "BIAQUARIO"
TABELA_LEGADO = "USU_VBIAPROD_CUSTO_PADRAO"

COLUNAS = ["CODEMPRESA", "PRODUTO", "CUSTO_PADRAO"]


# ----- FUNÇÕES -----

def contar(conn, schema: str, tabela: str) -> int:
    return conn.execute(text(f"SELECT COUNT(*) FROM {schema}.{tabela}")).scalar()


def divergencias(conn, origem: str, destino: str) -> list:
    colunas_str = ", ".join(COLUNAS)
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
        total_prata = contar(conn, SCHEMA_PRATA, TABELA_PRATA)
        total_legado = contar(conn, SCHEMA_LEGADO, TABELA_LEGADO)

        so_na_prata = divergencias(conn, prata_full, legado_full)
        so_no_legado = divergencias(conn, legado_full, prata_full)

    print(f"\n{'='*70}")
    print(f"  CONFERÊNCIA -- {TABELA_PRATA} (Prata) x {TABELA_LEGADO} (legado)")
    print(f"{'='*70}")
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
