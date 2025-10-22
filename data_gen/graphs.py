import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import tempfile
import os

# Define um estilo básico para os gráficos
plt.style.use('seaborn-v0_8-darkgrid')

def formatar_reais(x, pos):
    'Formata o eixo Y como R$'
    return f'R$ {x:,.0f}'.replace(',', '.')

def gerar_curva_s(df_tabela_3: pd.DataFrame):
    """
    Gera um gráfico de Curva S (Previsto Acumulado vs. Realizado Acumulado)
    a partir dos dados da Tabela 3 (gerar_tabela_previsto_realizado_mes).
    """
    try:
        if df_tabela_3.empty:
            return None

        # Garante que os dados são numéricos
        df_tabela_3['Total Previsto'] = pd.to_numeric(df_tabela_3['Total Previsto'], errors='coerce').fillna(0)
        df_tabela_3['Total Realizado'] = pd.to_numeric(df_tabela_3['Total Realizado'], errors='coerce').fillna(0)
        
        # Calcula o cumulativo
        df_plot = pd.DataFrame()
        df_plot['Mês'] = df_tabela_3['Mês']
        df_plot['Previsto Acumulado'] = df_tabela_3['Total Previsto'].cumsum()
        df_plot['Realizado Acumulado'] = df_tabela_3['Total Realizado'].cumsum()
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.plot(df_plot['Mês'], df_plot['Previsto Acumulado'], label='Previsto Acumulado', marker='o', color='blue')
        ax.plot(df_plot['Mês'], df_plot['Realizado Acumulado'], label='Realizado Acumulado', marker='s', color='green')
        
        ax.set_title('Desempenho Financeiro (Curva S)', fontsize=14, fontweight='bold')
        ax.set_xlabel('Mês', fontsize=12)
        ax.set_ylabel('Valor Acumulado (R$)', fontsize=12)
        ax.legend()
        
        # Formata o eixo Y
        formatter = plt.FuncFormatter(formatar_reais)
        ax.yaxis.set_major_formatter(formatter)
        ax.grid(True)
        
        # Salva em arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png", prefix="curva_s_") as tmpfile:
            plt.savefig(tmpfile.name, format='png', bbox_inches='tight')
            plt.close(fig)
            return tmpfile.name
            
    except Exception as e:
        print(f"Erro ao gerar Curva S: {e}")
        plt.close(fig)
        return None

def gerar_grafico_aderencia(df_tabela_5: pd.DataFrame):
    """
    Gera um gráfico de barras comparando Previsto Acumulado vs. Realizado Acumulado
    por item, a partir dos dados da Tabela 5 (gerar_tabela_previsto_realizado_acumulado).
    """
    try:
        if df_tabela_5.empty:
            return None

        # Filtra a linha 'TOTAL' se ela existir
        df_plot = df_tabela_5[df_tabela_5['Item'].str.upper() != 'TOTAL'].copy()
        
        if df_plot.empty:
            return None
            
        # Garante que os dados são numéricos
        df_plot['Valor Previsto Acumulado'] = pd.to_numeric(df_plot['Valor Previsto Acumulado'], errors='coerce').fillna(0)
        df_plot['Valor Realizado Acumulado'] = pd.to_numeric(df_plot['Valor Realizado Acumulado'], errors='coerce').fillna(0)

        n_itens = len(df_plot)
        index = np.arange(n_itens)
        bar_width = 0.35
        
        fig, ax = plt.subplots(figsize=(12, max(8, n_itens * 0.8))) # Altura dinâmica
        
        bars1 = ax.barh(index - bar_width/2, df_plot['Valor Previsto Acumulado'], bar_width, label='Previsto Acumulado', color='tab:blue')
        bars2 = ax.barh(index + bar_width/2, df_tabela_5['Valor Realizado Acumulado'], bar_width, label='Realizado Acumulado', color='tab:green')
        
        ax.set_title('Aderência às Etapas (Acumulado)', fontsize=14, fontweight='bold')
        ax.set_xlabel('Valor (R$)', fontsize=12)
        ax.set_ylabel('Itens', fontsize=12)
        ax.set_yticks(index)
        ax.set_yticklabels(df_plot['Item'], ha='right')
        ax.legend()
        
        # Formata o eixo X
        formatter = plt.FuncFormatter(formatar_reais)
        ax.xaxis.set_major_formatter(formatter)
        
        ax.grid(axis='x', linestyle='--', alpha=0.7)
        plt.gca().invert_yaxis() # Item de cima primeiro
        
        # Salva em arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png", prefix="aderencia_") as tmpfile:
            plt.savefig(tmpfile.name, format='png', bbox_inches='tight')
            plt.close(fig)
            return tmpfile.name

    except Exception as e:
        print(f"Erro ao gerar gráfico de aderência: {e}")
        plt.close(fig)
        return None

# Você pode adicionar mais funções de gráfico aqui (ex: para Tabela 2, Tabela 6, etc.)
# def gerar_grafico_idp(df_tabela_6: pd.DataFrame):
#     ...