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

CORTE DE DATA: a Prata usa 01/01/2021 (DATA_CORTE_PRODUCAO) nos blocos
DESEMPENHO/CONSUMO/PARADAS (DTRINI/DATMOV/DATMPR) e no bloco CUSTO_CC
(DATINI, corte novo) -- todos mapeados pra coluna DATREA no resultado
final. Por isso o lado do legado também é filtrado por DATREA >=
01/01/2021 aqui, mesma lógica das outras conferências com corte novo
desta área (ver conferencia_fat_custo_cc_producao.py).

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

        legado_com_corte = (
            f"(SELECT {', '.join(colunas)} FROM {SCHEMA_LEGADO}.{TABELA_LEGADO} "
            f"WHERE DATREA >= TO_DATE('{DATA_CORTE_PRODUCAO}', 'DD/MM/YYYY'))"
        )
        prata_full = f"{SCHEMA_PRATA}.{TABELA_PRATA}"

        total_prata           = contar(conn, SCHEMA_PRATA, TABELA_PRATA)
        total_legado_completo = contar(conn, SCHEMA_LEGADO, TABELA_LEGADO)
        total_legado_corte    = conn.execute(text(f"SELECT COUNT(*) FROM {legado_com_corte} X")).scalar()

        so_na_prata  = divergencias(conn, prata_full, legado_com_corte, colunas)
        so_no_legado = divergencias(conn, legado_com_corte, prata_full, colunas)

    print(f"\n{'='*70}")
    print(f"  CONFERÊNCIA -- {TABELA_PRATA} (Prata) x {TABELA_LEGADO} (legado, >= {DATA_CORTE_PRODUCAO})")
    print(f"{'='*70}")
    print(f"  Colunas comparadas: {len(colunas)}")
    if so_prata_cols:
        print(f"  [AVISO] Colunas só na Prata (fora da comparação): {so_prata_cols}")
    if so_legado_cols:
        print(f"  [AVISO] Colunas só no legado (fora da comparação): {so_legado_cols}")
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
