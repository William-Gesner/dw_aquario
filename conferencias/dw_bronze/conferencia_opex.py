"""
Conferência Bronze x Controladoria -- OPEX.

Reescrita em 17/07/2026 no mesmo espírito do Comercial (ver
conferencia_comercial.py para o histórico completo do porquê a versão
"só COUNT(*)" não é suficiente sozinha) -- adiciona checagem de conteúdo
sob demanda. Não existe alerta de filial nesta área: nenhuma das 5
tabelas do catálogo do OPEX tem coluna de filial (confirmado via
ALL_TAB_COLUMNS em 07/07/2026, ver opex/bronze/tabelas.py) -- só CODEMP
(e mesmo assim, 2 das 5 são globais, sem CODEMP nenhum).

DIFERENÇA ESTRUTURAL: a origem é o banco de Controladoria (servidor
Oracle separado), não o ERP principal -- por isso usa
core.db.get_engine_controladoria() para o lado Sapiens e
core.db.get_engine_bronze() para o lado Bronze, em vez de um engine só.

Reaproveita montar_query_pks() e montar_query() (opex/bronze/extrator.py)
-- mesma lógica de escopo (tem_codemp/coluna_codemp, CODEMP IN (1,50)).

Só leitura -- não corrige nem apaga nada.

Uso:
    python -m conferencias.dw_bronze.conferencia_opex
        -> contagem (rápida) nas 5 tabelas do catálogo.

    python -m conferencias.dw_bronze.conferencia_opex --conteudo E044CCU
        -> conteúdo (MINUS, dado a dado) só dessa tabela.
"""

# ----- IMPORTS -----

import sys
import traceback

from sqlalchemy import text

from opex.bronze.extrator import TABELAS_DESTE_BLOCO, montar_query, montar_query_pks
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


# ----- COLUNAS REAIS (cópia crua -- mesma lista da Controladoria) -----

def colunas_reais(engine, tabela: str) -> list[str]:
    """Lista as colunas reais da tabela, na ordem física da Controladoria (ALL_TAB_COLUMNS)."""
    query = """
        SELECT column_name
        FROM ALL_TAB_COLUMNS
        WHERE owner = 'SAPIENS' AND table_name = :tabela
        ORDER BY column_id
    """
    with engine.connect() as conn:
        linhas = conn.execute(text(query), {"tabela": tabela}).fetchall()
    if not linhas:
        raise ValueError(
            f"Nenhuma coluna encontrada para SAPIENS.{tabela} em ALL_TAB_COLUMNS "
            f"(Controladoria)."
        )
    return [linha[0] for linha in linhas]


# ----- CONFERÊNCIA DE CONTAGEM (rápida, todas as tabelas) -----

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


# ----- CONFERÊNCIA DE CONTEÚDO (dado a dado, 1 tabela por vez) -----

def conferir_conteudo(engine_controladoria, engine_bronze, nome_tabela: str) -> None:
    """MINUS nos dois sentidos, todas as colunas reais, Bronze x Controladoria."""
    info = buscar_tabela(nome_tabela)

    colunas = colunas_reais(engine_controladoria, nome_tabela)
    colunas_str = ", ".join(colunas)

    query_sapiens = montar_query(info, primeira_carga=True)
    query_bronze = f"SELECT {colunas_str} FROM {schema_bronze}.{nome_tabela}"

    print(f"\n{'='*70}")
    print(f"  CONFERÊNCIA DE CONTEÚDO -- {nome_tabela} (Bronze x Controladoria)")
    print(f"{'='*70}")
    print(f"  Query Controladoria: {query_sapiens}")

    with engine_controladoria.connect() as conn:
        linhas_sapiens = conn.execute(text(query_sapiens)).fetchall()
    with engine_bronze.connect() as conn:
        linhas_bronze = conn.execute(text(query_bronze)).fetchall()

    set_sapiens = set(linhas_sapiens)
    set_bronze = set(linhas_bronze)
    so_no_sapiens = set_sapiens - set_bronze
    so_na_bronze = set_bronze - set_sapiens

    print(f"\n  Só na Controladoria (ausente ou desatualizado na Bronze) : {len(so_no_sapiens):>8,}")
    print(f"  Só na Bronze (sem equivalente idêntico na Controladoria) : {len(so_na_bronze):>8,}")

    if not so_no_sapiens and not so_na_bronze:
        print(f"\n  [OK] Conteúdo idêntico.")
    else:
        print(f"\n  [DIVERGENTE]")
        if so_no_sapiens:
            print(f"\n  --- Amostra: só na Controladoria (até 10 de {len(so_no_sapiens)}) ---")
            for linha in list(so_no_sapiens)[:10]:
                print(f"    {dict(zip(colunas, linha))}")
        if so_na_bronze:
            print(f"\n  --- Amostra: só na Bronze (até 10 de {len(so_na_bronze)}) ---")
            for linha in list(so_na_bronze)[:10]:
                print(f"    {dict(zip(colunas, linha))}")
    print(f"{'='*70}")


# ----- EXECUÇÃO -----

if __name__ == "__main__":
    engine_controladoria = get_engine_controladoria()
    engine_bronze = get_engine_bronze()

    if "--conteudo" in sys.argv:
        idx = sys.argv.index("--conteudo")
        try:
            nome_tabela = sys.argv[idx + 1]
        except IndexError:
            print("  Uso: python -m conferencias.dw_bronze.conferencia_opex --conteudo NOME_TABELA")
            sys.exit(1)

        conferir_conteudo(engine_controladoria, engine_bronze, nome_tabela)
        sys.exit(0)

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
