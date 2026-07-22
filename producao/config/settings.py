"""
Carregamento e exposição das variáveis de ambiente do módulo Produção.

Mesmo servidor Oracle do Comercial/Laudos RMA (não precisa de credencial
separada, diferente do OPEX) -- usa core.db.get_engine() normalmente.

Variáveis de ambiente necessárias (.env): já cobertas pelas usadas por
outras áreas (ORACLE_SCHEMA_BRONZE, ORACLE_SCHEMA_PRATA,
ORACLE_CLIENT_LIB_DIR, ORACLE_USER/ORACLE_PASSWORD).
"""

# ----- IMPORTS -----

import os
from pathlib import Path

from dotenv import load_dotenv

# ----- CONFIGURAÇÃO DA RAIZ DO PROJETO -----

# Detecta a raiz do projeto (3 níveis acima: settings.py -> config -> producao -> raiz)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", _PROJECT_ROOT))

# ----- CARREGAMENTO DO .ENV -----

load_dotenv(PROJECT_ROOT / ".env")

# ----- SCHEMAS DE DESTINO — MIGRAÇÃO MEDALHÃO -----

schema_bronze = os.environ["ORACLE_SCHEMA_BRONZE"]
schema_prata = os.environ["ORACLE_SCHEMA_PRATA"]

# ----- VARIÁVEIS DE INFRAESTRUTURA -----

ORACLE_CLIENT_LIB_DIR = os.environ["ORACLE_CLIENT_LIB_DIR"]

# ----- FILTROS ESTRUTURAIS FIXOS DO PROJETO AQUÁRIO -----

# Aquário = CODEMP 1 sempre (regra padrão do projeto -- sem exceção aqui,
# diferente do OPEX).
CODEMP_AQUARIO = 1
CODFIL_AQUARIO = 1

# ----- JANELA DE INCREMENTAL DA BRONZE -----

JANELA_INCREMENTAL_DIAS = 60

# ----- CORTE DE DATA DA PRATA -----

# Decisão confirmada com o usuário em 21/07/2026: TODAS as tabelas FATO
# da Produção com grão de data usam 01/01/2021 -- inclusive as que o
# legado cortava em 01/01/2018 (FAT_PARADAS_PRODUCAO, blocos DESEMPENHO/
# CONSUMO de FAT_DESEMPENHO_PRODUCAO) e as que o legado não cortava
# nenhuma (FAT_CUSTO_CC_PRODUCAO, bloco CUSTO_CC de
# FAT_DESEMPENHO_PRODUCAO) -- diferente da regra geral da Fase 2 (só
# aplicar corte novo quando o legado não tinha nenhum), aqui foi pedido
# explicitamente o padrão único de 2021 pra toda a área.
DATA_CORTE_PRODUCAO = "01/01/2021"

# ----- CAMINHOS DE ARQUIVOS EXTERNOS -----

# Pasta local na VM (drive Z:) onde ficam os arquivos Excel -- mesmo
# caminho já usado pelo legado (producao/config/settings.py).
PASTA_DADOS_EXTERNOS = Path(r"Z:\Dados")

# TempoDisponivelCC.xlsx -- usado por DOIS módulos (Estoque e Produção).
#   Aba BD : meta de utilização por CC e dia   -> vbiutilizacaometa.py (ESTE módulo)
#   Aba CP : custo padrão por produto          -> vbicustopadrao.py    (ESTE módulo e Estoque)
EXCEL_TEMPO_DISPONIVEL = PASTA_DADOS_EXTERNOS / "TempoDisponivelCC.xlsx"
