"""
Carregamento e exposição das variáveis de ambiente do módulo Expedição.

Mesmo servidor Oracle do Comercial/Produção/Estoque/Laudos RMA (não
precisa de credencial separada, diferente do OPEX) -- usa
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

# Detecta a raiz do projeto (3 níveis acima: settings.py -> config -> expedicao -> raiz)
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
