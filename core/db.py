"""
Conexão com o banco Oracle.

Centraliza a criação dos engines SQLAlchemy para Bronze e Prata.
Como ambos os schemas estão no mesmo banco físico (dbprod/srvoda01),
a diferença entre eles é apenas o usuário que conecta:

    get_engine_bronze() -> conecta como DW_BRONZE
    get_engine_prata()  -> conecta como DW_PRATA

Cada engine é um singleton — criado uma vez e reutilizado em todas
as chamadas subsequentes, evitando múltiplas conexões desnecessárias.

Variáveis de ambiente necessárias (.env):
    ORACLE_HOST          : host do banco (ex.: dbprod)
    ORACLE_PORT          : porta do listener (ex.: 1521)
    ORACLE_SERVICE_NAME  : service name (ex.: dbprod)
    ORACLE_CLIENT_LIB_DIR: caminho do Oracle Instant Client
    ORACLE_USER          : usuário Bronze (ex.: DW_BRONZE)
    ORACLE_PASSWORD      : senha Bronze
    ORACLE_USER_PRATA    : usuário Prata (ex.: DW_PRATA)
    ORACLE_PASSWORD_PRATA: senha Prata
"""

# ----- IMPORTS -----

import os
from pathlib import Path

import oracledb
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

# ----- CONFIGURAÇÕES INICIAIS -----

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

# ----- SINGLETONS -----

_engine_bronze: Engine | None = None
_engine_prata:  Engine | None = None
_client_initialized = False


# ----- FUNÇÕES INTERNAS -----

def _init_client() -> None:
    """Inicializa o Oracle Instant Client (apenas uma vez)."""
    global _client_initialized
    if not _client_initialized:
        oracledb.init_oracle_client(lib_dir=os.environ["ORACLE_CLIENT_LIB_DIR"])
        _client_initialized = True


def _criar_engine(usuario: str, senha: str) -> Engine:
    """Cria um engine SQLAlchemy para o banco Oracle."""
    _init_client()
    host         = os.environ["ORACLE_HOST"]
    porta        = int(os.environ["ORACLE_PORT"])
    service_name = os.environ["ORACLE_SERVICE_NAME"]
    return create_engine(
        f"oracle+oracledb://{usuario}:{senha}@{host}:{porta}/?service_name={service_name}"
    )


# ----- FUNÇÕES PÚBLICAS -----

def get_engine_bronze() -> Engine:
    """Retorna o engine conectado como DW_BRONZE (singleton)."""
    global _engine_bronze
    if _engine_bronze is None:
        usuario = os.environ["ORACLE_USER"]
        senha   = os.environ["ORACLE_PASSWORD"]
        _engine_bronze = _criar_engine(usuario, senha)
    return _engine_bronze


def get_engine_prata() -> Engine:
    """Retorna o engine conectado como DW_PRATA (singleton)."""
    global _engine_prata
    if _engine_prata is None:
        usuario = os.environ["ORACLE_USER_PRATA"]
        senha   = os.environ["ORACLE_PASSWORD_PRATA"]
        _engine_prata = _criar_engine(usuario, senha)
    return _engine_prata


def get_engine() -> Engine:
    """
    Atalho para compatibilidade — retorna o engine Bronze.
    Scripts que chamavam get_engine() continuam funcionando sem alteração.
    """
    return get_engine_bronze()