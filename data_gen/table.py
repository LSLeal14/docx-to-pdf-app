import numpy as np
import pandas as pd

def cria_tablela(linhas, l_tipo, colunas, c_tipo):
    return pd.DataFrame({col: pd.Series(c_tipo = dtype_map(typ)) for col, typ in zip(colunas, c_tipo)},
                        {col: pd.Series(c_tipo = dtype_map(typ)) for col, typ in zip(linhas, l_tipo)})

def dtype_map(dtype_str):
    return {
        'str': 'object',
        'int': 'int64',
        'float': 'float64'
    }.get(dtype_str, 'object')