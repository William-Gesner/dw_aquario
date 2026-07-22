"""
Carregamento e exposição das variáveis de ambiente do módulo
Rastreabilidade.

Mesmo servidor Oracle do Comercial/Produção/Estoque/Expedição/Laudos RMA
(não precisa de credencial separada, diferente do OPEX) -- usa
core.db.get_engine() normalmente.

Variáveis de ambiente necessárias (.env): já cobertas pelas usadas por
outras áreas (ORACLE_SCHEMA_BRONZE, ORACLE_SCHEMA_PRATA,
ORACLE_CLIENT_LIB_DIR, ORACLE_USER/ORACLE_PASSWORD).
"""

# ----- IMPORTS -----

import os
from pathlib import Path

from dotenv import load_dotenv

# ----- CONFIGURAÇÃO DA RAIZ DO PROJETO -----

# Detecta a raiz do projeto (3 níveis acima: settings.py -> config -> rastreabilidade -> raiz)
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

# O legado (vbirastreabilidade.py) já filtrava DATEMI/USU_DATGER
# >= 01/01/2023 (formato 'RRRR/MM/DD', comparação por TO_CHAR) -- mantido
# igual, não trocado pelo padrão de 2021 usado no Comercial (Regra 2 da
# Fase 2: só aplicamos corte novo quando o legado não tinha nenhum).
DATA_CORTE_RASTREABILIDADE = "2023/01/01"

# ----- CAMINHOS DE ARQUIVOS EXTERNOS -----

# Pasta local na VM (drive Z:) onde ficam os arquivos Excel -- mesmo
# caminho já usado pelo legado (rastreabilidade/config/settings.py).
PASTA_DADOS_EXTERNOS = Path(r"Z:\Dados")

# MetaMix.xlsx -- usado para enriquecer os dados de rastreabilidade com
# MIX e ORIGEM de cada produto (aba: Cadastro, colunas: Cd_Item,
# Cd_Com_Mix, Cd_Com_Ori). O JOIN é feito em Python antes de salvar no
# banco -- replica o comportamento do legado. Decisão de 07/07/2026:
# arquivos Excel ficam FORA da Bronze (ver rastreabilidade/bronze/tabelas.py).
EXCEL_METAMIX = PASTA_DADOS_EXTERNOS / "MetaMix.xlsx"
