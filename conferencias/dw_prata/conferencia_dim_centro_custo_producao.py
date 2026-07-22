"""
Conferência DIM_CENTRO_CUSTO_PRODUCAO (Prata) -- técnica DIFERENTE das
outras conferências do projeto.

----------------------------------------------------------------------
POR QUE ESTA CONFERÊNCIA É DIFERENTE
----------------------------------------------------------------------
Todas as outras conferências da Fase 2 assumem que o legado
(BIAQUARIO.USU_VBIAPROD_CENTROCUSTO, aqui) é a fonte de verdade, e
esperam bater 0 divergências dos dois lados. Essa premissa NÃO vale
para esta tabela: o legado usava chaves_merge sem CODOPR, então
descarta silenciosamente operações duplicadas por centro de custo/
estágio/centro de recurso -- mesmo bug que a 1ª versão desta migração
herdou fielmente (ver dw_aquario/doc_nova_arquitetura.md, seção
"Produção", achado de 21/07/2026: 21 grupos reais com mais de 1
operação, confirmado direto em E720OPR no Sapiens). Comparar a Prata
corrigida contra o legado (não corrigido) SEMPRE vai mostrar "só na
Prata" -- não é erro, é a diferença entre certo e o que sempre esteve
truncado.

Por isso, esta conferência faz DOIS testes com objetivos diferentes:

    TESTE 1 -- Regressão contra o legado (só no legado deve ser 0):
        garante que a Prata não PERDEU nada que o legado já tinha --
        toda linha do legado precisa ter equivalente na Prata (a Prata
        é sempre um superconjunto do legado, nunca um subconjunto).

    TESTE 2 -- Completude contra a fonte de verdade (Bronze/E720OPR):
        a query de referência abaixo é a MESMA lógica de negócio do
        script de carga (dim_centro_custo_producao.py), reexecutada
        aqui de forma independente contra a Bronze. Comparar a Prata
        JÁ CARREGADA contra essa query fresca prova que a carga (upsert,
        conversão de tipo, etc.) preservou exatamente o que a query
        deveria trazer -- pega bug de carga (truncamento, perda de
        linha no MERGE, etc.), mesmo não pegando um eventual erro de
        lógica de negócio que estivesse igual nos dois lados (por
        isso o achado original foi validado à parte, direto no
        Sapiens -- ver seção "Produção" do doc).

Só leitura -- não corrige nem apaga nada.

PRÉ-REQUISITO: GRANT SELECT ON BIAQUARIO.USU_VBIAPROD_CENTROCUSTO TO DW_PRATA;

Uso:
    python -m conferencias.dw_prata.conferencia_dim_centro_custo_producao
"""

# ----- IMPORTS -----

from sqlalchemy import text

from core.db import get_engine_prata
from producao.config.settings import schema_bronze

# ----- CONFIGURAÇÃO -----

SCHEMA_PRATA = "DW_PRATA"
TABELA_PRATA = "DIM_CENTRO_CUSTO_PRODUCAO"

SCHEMA_LEGADO = "BIAQUARIO"
TABELA_LEGADO = "USU_VBIAPROD_CENTROCUSTO"

# CODOPR/DESETG/ABRETG normalizados com NVL(..., ' ') -- alguns casos
# têm "vazio" representado como NULL de um lado (LEFT JOIN sem match,
# ex.: bloco 1 do CODCRE=2540, que já é naturalmente CODETG=0 e não tem
# entrada em E093ETG) e como ' ' literal do outro (bloco 2, hardcoded).
# Mesmo fato real descrito 2x -- sem essa normalização, NULL x ' '
# apareceria como divergência falsa (ver dw_aquario/doc_nova_arquitetura.md,
# seção "Produção", achado de 22/07/2026: CODCRE=2540 já tem cobertura
# natural pelo bloco 1, a entrada na lista hardcoded do bloco 2 é
# redundante, herdada do legado).
COLUNAS = [
    "CODCCU", "DESCCU", "ABRCCU", "CCUPAI", "CODETG",
    "NVL(DESETG, ' ') AS DESETG", "NVL(ABRETG, ' ') AS ABRETG",
    "CODCRE", "DESCRE", "ABRCRE", "NVL(CODOPR, ' ') AS CODOPR", "DESOPR",
    "ABROPR", "UNICRE", "MOVORP",
]

# Mesma query de negócio do dim_centro_custo_producao.py (2 blocos:
# estrutura principal + centros de recurso sem estágio), reexecutada
# aqui como "fonte de verdade" independente contra a Bronze.
QUERY_REFERENCIA_BRONZE = f"""
SELECT
    OPR.CODCCU, CCU.DESCCU, CCU.ABRCCU, CCU.CCUPAI,
    OPR.CODETG, ETG.DESETG, ETG.ABRETG,
    OPR.CODCRE, CRE.DESCRE, CRE.ABRCRE,
    OPR.CODOPR, OPR.DESOPR, OPR.ABROPR, OPR.UNICRE, OPR.MOVORP

FROM {schema_bronze}.E720OPR OPR

LEFT JOIN {schema_bronze}.E044CCU CCU
    ON  CCU.CODEMP = OPR.CODEMP
    AND CCU.CODCCU = OPR.CODCCU

LEFT JOIN {schema_bronze}.E093ETG ETG
    ON  ETG.CODEMP = OPR.CODEMP
    AND ETG.CODETG = OPR.CODETG

LEFT JOIN {schema_bronze}.E725CRE CRE
    ON  CRE.CODEMP = OPR.CODEMP
    AND CRE.CODCRE = OPR.CODCRE

WHERE OPR.CODEMP = 1

UNION ALL

SELECT
    CRE.CODCCU, CCU.DESCCU, CCU.ABRCCU, CCU.CCUPAI,
    0 AS CODETG, ' ' AS DESETG, ' ' AS ABRETG,
    CRE.CODCRE, CRE.DESCRE, CRE.ABRCRE,
    NVL(OPR.CODOPR, ' ') AS CODOPR, OPR.DESOPR, OPR.ABROPR, OPR.UNICRE, OPR.MOVORP

FROM {schema_bronze}.E725CRE CRE

LEFT JOIN {schema_bronze}.E044CCU CCU
    ON  CCU.CODEMP = CRE.CODEMP
    AND CCU.CODCCU = CRE.CODCCU

LEFT JOIN {schema_bronze}.E720OPR OPR
    ON  CRE.CODEMP = OPR.CODEMP
    AND CRE.CODCRE = OPR.CODCRE

WHERE CRE.CODEMP = 1
  AND CRE.CODCRE IN ('7020','7120','7320','7420','7520','8120','3020','3220','2540','2940','2240')
"""


# ----- FUNÇÕES -----

def contar(conn, schema: str, tabela: str) -> int:
    return conn.execute(text(f"SELECT COUNT(*) FROM {schema}.{tabela}")).scalar()


def contar_referencia(conn) -> int:
    return conn.execute(text(f"SELECT COUNT(*) FROM ({QUERY_REFERENCIA_BRONZE}) X")).scalar()


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

    prata_full     = f"{SCHEMA_PRATA}.{TABELA_PRATA}"
    legado_full    = f"{SCHEMA_LEGADO}.{TABELA_LEGADO}"
    referencia_sql = f"({QUERY_REFERENCIA_BRONZE})"

    with engine.connect() as conn:
        total_prata      = contar(conn, SCHEMA_PRATA, TABELA_PRATA)
        total_legado     = contar(conn, SCHEMA_LEGADO, TABELA_LEGADO)
        total_referencia = contar_referencia(conn)

        # TESTE 1 -- regressão contra o legado
        so_no_legado = divergencias(conn, legado_full, prata_full)

        # TESTE 2 -- completude contra a fonte de verdade (Bronze)
        so_na_prata_vs_ref = divergencias(conn, prata_full, referencia_sql)
        so_na_ref_vs_prata = divergencias(conn, referencia_sql, prata_full)

    print(f"\n{'='*70}")
    print(f"  CONFERÊNCIA -- {TABELA_PRATA} (técnica de 2 testes -- ver docstring)")
    print(f"{'='*70}")
    print(f"  Linhas na Prata                    : {total_prata:>10,}")
    print(f"  Linhas no legado (truncado)         : {total_legado:>10,}")
    print(f"  Linhas na query de referência (Bronze) : {total_referencia:>10,}")

    print(f"\n  --- TESTE 1: nada perdido em relação ao legado ---")
    print(f"  Só no legado (deveria ser 0)  : {len(so_no_legado):>6,}")
    if not so_no_legado:
        print(f"  [OK] Toda linha do legado tem equivalente na Prata.")
    else:
        print(f"  [FALHA] Existe dado do legado que sumiu na Prata -- investigar.")
        print(f"  --- Amostra (até 10 de {len(so_no_legado)}) ---")
        for linha in so_no_legado[:10]:
            print(f"    {linha}")

    print(f"\n  --- TESTE 2: Prata bate com a query de referência direto na Bronze ---")
    print(f"  Só na Prata (não está na referência)   : {len(so_na_prata_vs_ref):>6,}")
    print(f"  Só na referência (não está na Prata)   : {len(so_na_ref_vs_prata):>6,}")
    if not so_na_prata_vs_ref and not so_na_ref_vs_prata:
        print(f"  [OK] Prata carregada é idêntica à query de referência -- carga correta.")
    else:
        print(f"  [FALHA] Prata carregada diverge da query de referência -- bug de carga, não de lógica.")
        if so_na_prata_vs_ref:
            print(f"  --- Amostra só na Prata (até 10) ---")
            for linha in so_na_prata_vs_ref[:10]:
                print(f"    {linha}")
        if so_na_ref_vs_prata:
            print(f"  --- Amostra só na referência (até 10) ---")
            for linha in so_na_ref_vs_prata[:10]:
                print(f"    {linha}")

    print(f"\n{'='*70}")
    if not so_no_legado and not so_na_prata_vs_ref and not so_na_ref_vs_prata:
        print(f"  [OK GERAL] DIM_CENTRO_CUSTO_PRODUCAO validada: superset correto do legado,")
        print(f"  e carga fiel à fonte de verdade (Bronze/E720OPR).")
    else:
        print(f"  [ATENÇÃO] Um ou mais testes falharam -- ver detalhes acima.")
    print(f"{'='*70}")
