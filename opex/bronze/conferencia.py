"""
Conferência Bronze x Controladoria -- compara COUNT(*) tabela por tabela.

Só leitura -- não corrige nem apaga nada. Mesmo padrão da conferência do
Comercial (comercial/bronze/conferencia.py), adaptado pro OPEX: a origem
é o banco de Controladoria (servidor separado), não o ERP principal --
por isso usa core.db.get_engine_controladoria() para contar do lado da
origem, em vez de reaproveitar o mesmo engine da Bronze.

Reaproveita montar_query_pks() (opex/bronze/extrator.py) pra montar o
lado Controladoria da comparação -- mesma lógica de escopo (tem_codemp/
coluna_codemp, CODEMP IN (1,50)), SEM janela de data.

Uso:
    python -m opex.bronze.conferencia
"""

# ----- IMPORTS -----

import traceback

from sqlalchemy import text

from opex.bronze.extrator import TABELAS_DESTE_BLOCO, montar_query_pks
from opex.bronze.tabelas import buscar_tabela
from opex.config.settings import schema_bronze
from core.db import get_engine_bronze, get_engine_controladoria


# ----- CONTAGENS -----

def contar_controladoria(engine, info: dict) -> int:
    """
    Conta o universo completo e atual da tabela na Controladoria, no mesmo
    escopo (coluna_codemp real IN CODEMP_AQUARIO_OPEX) que a Bronze
    deveria ter -- sem janela de data.
    """
    query = f"SELECT COUNT(*) FROM ({montar_query_pks(info)})"
    with engine.connect() as conn:
        return conn.execute(text(query)).scalar()


def contar_bronze(engine, schema: str, tabela: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {schema}.{tabela}")).scalar()


# ----- CONFERÊNCIA DE UMA TABELA -----

def conferir_tabela(engine_controladoria, engine_bronze, nome_tabela: str) -> dict:
    info = buscar_tabela(nome_tabela)

    total_controladoria = contar_controladoria(engine_controladoria, info)
    total_bronze = contar_bronze(engine_bronze, schema_bronze, nome_tabela)
    diferenca = total_bronze - total_controladoria

    status = "OK" if diferenca == 0 else "DIVERGENTE"

    return {
        "tabela": nome_tabela,
        "controladoria": total_controladoria,
        "bronze": total_bronze,
        "diferenca": diferenca,
        "status": status,
    }


# ----- EXECUÇÃO -----

if __name__ == "__main__":
    engine_controladoria = get_engine_controladoria()
    engine_bronze = get_engine_bronze()
    resultados = []

    for nome in TABELAS_DESTE_BLOCO:
        try:
            resultados.append(conferir_tabela(engine_controladoria, engine_bronze, nome))
        except Exception:
            print(f"\n  [ERRO] Falha ao conferir {nome}:")
            traceback.print_exc()
            resultados.append({"tabela": nome, "status": "ERRO"})

    print(f"\n{'='*78}")
    print(f"  {'TABELA':<20} {'CONTROLADORIA':>14} {'BRONZE':>12} {'DIFERENÇA':>12}  STATUS")
    print(f"{'='*78}")

    for r in resultados:
        controladoria = r.get("controladoria", "-")
        bronze        = r.get("bronze", "-")
        diferenca     = r.get("diferenca", "-")

        controladoria_fmt = f"{controladoria:,}" if isinstance(controladoria, int) else controladoria
        bronze_fmt         = f"{bronze:,}" if isinstance(bronze, int) else bronze
        diferenca_fmt       = f"{diferenca:+,}" if isinstance(diferenca, int) else diferenca

        print(f"  {r['tabela']:<20} {controladoria_fmt:>14} {bronze_fmt:>12} {diferenca_fmt:>12}  {r['status']}")

    divergentes = [r for r in resultados if r.get("status") == "DIVERGENTE"]
    erros       = [r for r in resultados if r.get("status") == "ERRO"]

    print(f"{'='*78}")
    print(
        f"  Total: {len(resultados)} tabelas | "
        f"{len(resultados) - len(divergentes) - len(erros)} OK | "
        f"{len(divergentes)} divergente(s) | {len(erros)} erro(s)"
    )
    print(f"{'='*78}")
