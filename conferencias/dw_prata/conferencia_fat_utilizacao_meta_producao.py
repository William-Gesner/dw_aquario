"""
Conferência FAT_UTILIZACAO_META_PRODUCAO (Prata) x
USU_VBIAPROD_UTILIZACAO_META (legado, schema BIAQUARIO) -- compara os
DADOS, não só a contagem.

Ver conferencia_dim_condicao_pagamento.py para a explicação completa da
técnica (MINUS nos dois sentidos). Só leitura -- não corrige nem apaga
nada.

CORTE DE DATA: a Prata usa 01/01/2021 (DATA_CORTE_PRODUCAO, sobre DATA)
-- corte NOVO, o legado não tinha nenhum. Lado do legado também
filtrado por DATA >= 01/01/2021, mesma lógica das outras conferências
com corte novo desta área -- ver conferencia_fat_custo_cc_producao.py.
Na prática a divergência de contagem tende a ser pequena ou zero (é
meta corrente, não histórico profundo).

PRÉ-REQUISITO: GRANT SELECT ON BIAQUARIO.USU_VBIAPROD_UTILIZACAO_META TO DW_PRATA;

Uso:
    python -m conferencias.dw_prata.conferencia_fat_utilizacao_meta_producao
"""

# ----- IMPORTS -----

from sqlalchemy import text

from core.db import get_engine_prata
from producao.config.settings import DATA_CORTE_PRODUCAO

# ----- CONFIGURAÇÃO -----

SCHEMA_PRATA = "DW_PRATA"
TABELA_PRATA = "FAT_UTILIZACAO_META_PRODUCAO"

SCHEMA_LEGADO = "BIAQUARIO"
TABELA_LEGADO = "USU_VBIAPROD_UTILIZACAO_META"

COLUNAS = ["DATA", "CD_CENTROCUSTO", "DIA_SEMANA", "MIN_DIA", "DIAS_UTEIS", "LIMITE_SUPERIOR"]

LEGADO_COM_CORTE = (
    f"(SELECT {', '.join(COLUNAS)} FROM {SCHEMA_LEGADO}.{TABELA_LEGADO} "
    f"WHERE DATA >= TO_DATE('{DATA_CORTE_PRODUCAO}', 'DD/MM/YYYY'))"
)


# ----- FUNÇÕES -----

def contar(conn, schema: str, tabela: str) -> int:
    return conn.execute(text(f"SELECT COUNT(*) FROM {schema}.{tabela}")).scalar()


def contar_legado_com_corte(conn) -> int:
    return conn.execute(text(f"SELECT COUNT(*) FROM {LEGADO_COM_CORTE} X")).scalar()


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

    with engine.connect() as conn:
        total_prata = contar(conn, SCHEMA_PRATA, TABELA_PRATA)
        total_legado_completo = contar(conn, SCHEMA_LEGADO, TABELA_LEGADO)
        total_legado_corte = contar_legado_com_corte(conn)

        so_na_prata = divergencias(conn, prata_full, LEGADO_COM_CORTE)
        so_no_legado = divergencias(conn, LEGADO_COM_CORTE, prata_full)

    print(f"\n{'='*70}")
    print(f"  CONFERÊNCIA -- {TABELA_PRATA} (Prata) x {TABELA_LEGADO} (legado, >= {DATA_CORTE_PRODUCAO})")
    print(f"{'='*70}")
    print(f"  Linhas na Prata                          : {total_prata:>10,}")
    print(f"  Linhas no legado (histórico completo)    : {total_legado_completo:>10,}")
    print(f"  Linhas no legado (>= {DATA_CORTE_PRODUCAO})            : {total_legado_corte:>10,}")
    print(f"  Só na Prata (sem equivalente idêntico no legado)  : {len(so_na_prata):>6,}")
    print(f"  Só no legado (sem equivalente idêntico na Prata)  : {len(so_no_legado):>6,}")

    if not so_na_prata and not so_no_legado:
        print(f"\n  [OK] Dados idênticos (dentro do corte de {DATA_CORTE_PRODUCAO}) -- todas as colunas de negócio batem.")
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
