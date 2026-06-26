"""
Conexão com o banco Oracle.
 
Centraliza a criação do engine SQLAlchemy para que todos os scripts de
extração usem a mesma instância (singleton), evitando múltiplas conexões
desnecessárias ao banco de dados.
 
Dependências:
    - oracledb  : driver Oracle para Python
    - SQLAlchemy: ORM/engine de banco de dados
    - dotenv    : leitura das credenciais do arquivo .env
"""

# ----- IMPORTS -----

import os
from pathlib import Path

import oracledb
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

# ----- CONFIGURAÇÕES INICIAIS -----

# Localiza a raiz do projeto (dois níveis acima de core/) e carrega o .env
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

# Instância singleton do engine — inicializada na primeira chamada a get_engine()
_engine: Engine | None = None

# ----- FUNÇÕES -----

def get_engine() -> Engine:
    """Cria e reutiliza o engine Oracle (SQLAlchemy + oracledb)."""
    global _engine

    if _engine is None:
        oracledb.init_oracle_client(lib_dir=os.environ["ORACLE_CLIENT_LIB_DIR"])
        
        usuario       = os.environ["ORACLE_USER"]
        senha         = os.environ["ORACLE_PASSWORD"]
        host          = os.environ["ORACLE_HOST"]
        porta         = int(os.environ["ORACLE_PORT"])
        service_name  = os.environ["ORACLE_SERVICE_NAME"]

        _engine = create_engine(
            f"oracle+oracledb://{usuario}:{senha}@{host}:{porta}/?service_name={service_name}"
        )

    return _engine
