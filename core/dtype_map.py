"""
Mapeamento automático de tipos pandas → tipos SQLAlchemy compatíveis com Oracle.
 
Utilizado antes de qualquer operação de escrita no banco (upsert ou full_reload)
para garantir que as colunas do DataFrame sejam criadas com os tipos corretos
na tabela Oracle de destino.
"""

# ----- IMPORTS -----

import pandas as pd
from sqlalchemy.types import CLOB, DateTime, Integer, Numeric, String

# ----- FUNÇÕES -----

def build_dtype_map(df: pd.DataFrame) -> dict:
    """
    Inspeciona cada coluna do DataFrame e retorna um dicionário
    com o tipo SQLAlchemy adequado para uso no Oracle.
 
    Regras de mapeamento:
        - int   → Integer()
        - float → Numeric(38, 10)
        - data  → DateTime()
        - texto ≤ 4000 chars → String(max_len + 20)   [margem de segurança]
        - texto > 4000 chars → CLOB()
 
    Args:
        df (pd.DataFrame): DataFrame com os dados a serem carregados.
 
    Returns:
        dict: {nome_coluna: tipo_SQLAlchemy}
    """
    dtype_map = {}

    for col in df.columns:
        serie = df[col]

        if pd.api.types.is_integer_dtype(serie):
            dtype_map[col] = Integer()

        elif pd.api.types.is_float_dtype(serie):
            dtype_map[col] = Numeric(38, 10)

        elif pd.api.types.is_datetime64_any_dtype(serie):
            dtype_map[col] = DateTime()

        else:
            # ----- CÁLCULO DO TAMANHO MÁXIMO PARA COLUNAS TEXTO -----
            try:
                max_len = int(serie.astype(str).str.len().max())
            except Exception:
                max_len = 100

            # Garante valor mínimo caso a coluna esteja vazia ou com NaN
            if pd.isna(max_len) or max_len <= 0:
                max_len = 100

            if max_len > 4000:
                dtype_map[col] = CLOB()
            else:
                dtype_map[col] = String(min(max_len + 20, 4000))

    return dtype_map
