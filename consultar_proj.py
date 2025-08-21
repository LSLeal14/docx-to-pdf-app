import streamlit as st
import os
import tempfile
import shutil
import re
import subprocess
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from docx import Document
from docx.shared import Inches
import matplotlib.pyplot as plt

# ==== Funções auxiliares ====

def get_downloads_folder():
    """Retorna o caminho para a pasta de Downloads do usuário."""
    home = Path.home()
    return home / "Downloads"

def gerar_grafico_exemplo(dados_grafico, caminho_saida):
    """Gera um gráfico de pizza e salva como imagem."""
    if not dados_grafico:
        st.warning("Dados para o gráfico não encontrados.")
        return
    labels = dados_grafico.keys()
    sizes = dados_grafico.values()
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 8})
    ax.axis('equal')
    plt.title("Distribuição de Custos", fontsize=10)
    plt.tight_layout()
    plt.savefig(caminho_saida, dpi=150)
    plt.close(fig)

# <<< NOVO: Função refatorada e corrigida para inserir a tabela >>>
def insert_table_after_paragraph(p, doc, records, dados_completos):
    """
    Insere uma tabela formatada após um parágrafo, com ordem de colunas e bordas corretas.
    """
    if not records:
        return

    # Limpa o parágrafo do placeholder
    for r in p.runs:
        r.text = ""

    # --- CORREÇÃO 2.2: GARANTINDO A ORDEM DAS COLUNAS ---
    prazo = dados_completos.get('prazo_meses')
    if not prazo:
        # Fallback caso 'prazo_meses' não esteja salvo no documento do Firebase
        cols_ordenadas = list(records[0].keys())
        st.warning("Campo 'prazo_meses' não encontrado no Firebase. A ordem das colunas da tabela pode não estar correta.")
    else:
        # Constrói a lista de colunas na ordem correta e garantida
        cols_ordenadas = ['Item'] + [f"Mês {i+1}" for i in range(int(prazo))]
        # Garante que qualquer outra coluna extra nos dados também apareça no final
        for col in records[0].keys():
            if col not in cols_ordenadas:
                cols_ordenadas.append(col)

    table = doc.add_table(rows=1, cols=len(cols_ordenadas))
    
    # --- CORREÇÃO 2.1: APLICANDO O ESTILO DE TABELA COM BORDAS ---
    table.style = 'Table Grid'
    
    # Preenche o cabeçalho
    hdr_cells = table.rows[0].cells
    for i, col_name in enumerate(cols_ordenadas):
        hdr_cells[i].text = str(col_name)

    # Preenche as linhas de dados
    for row_data in records:
        row_cells = table.add_row().cells
        # Itera na ordem correta e busca o valor correspondente no dicionário
        for i, col_name in enumerate(cols_ordenadas):
            cell_value = row_data.get(col_name)
            row_cells[i].text = "" if cell_value is None else str(cell_value)
    
    p._element.addnext(table._element)

def preencher_campos(doc, dados):
    """
    Substitui placeholders {{chave}} no documento por texto, imagens ou tabelas.
    """
    def is_image(v):
        return isinstance(v, (str, Path)) and str(v).lower().endswith((".png", ".jpg", ".jpeg"))

    def is_table(v):
        return isinstance(v, (list, pd.DataFrame)) and not is_image(v)

    def normalize_table(v):
        if isinstance(v, pd.DataFrame):
            return v.to_dict(orient="records")
        return v
    
    def replace_text_in_paragraph(p, mapping_text):
        full_text = p.text
        for k, v in mapping_text.items():
            if not isinstance(v, (list, dict)): # Não tenta substituir texto por tabelas/listas
                full_text = full_text.replace(f"{{{{{k}}}}}", str(v))
        if full_text != p.text:
            for r in p.runs: r.text = ""
            if p.runs: p.runs[0].text = full_text
            else: p.add_run(full_text)

    def paragraph_only_placeholder(p, placeholder):
        return p.text.strip() == placeholder

    def insert_image_at_paragraph(p, img_path):
        for r in p.runs: r.text = ""
        try:
            p.add_run().add_picture(str(img_path), width=Inches(5.0))
        except Exception as e:
            st.error(f"Não foi possível inserir a imagem {img_path}: {e}")

    # Separa os tipos de dados
    dados_texto, dados_imagem, dados_tabela = {}, {}, {}
    for k, v in dados.items():
        if is_image(v): dados_imagem[k] = v
        elif is_table(v): dados_tabela[k] = normalize_table(v)
        else: dados_texto[k] = v

    # Combina todos os parágrafos do documento (corpo e tabelas existentes)
    all_paragraphs = list(doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                all_paragraphs.extend(cell.paragraphs)

    for p in all_paragraphs:
        # Processa placeholders que ocupam um parágrafo inteiro (imagens e tabelas)
        for k, value in {**dados_imagem, **dados_tabela}.items():
            ph = f"{{{{{k}}}}}"
            if paragraph_only_placeholder(p, ph):
                if k in dados_imagem:
                    insert_image_at_paragraph(p, dados_imagem[k])
                elif k in dados_tabela:
                    # <<< MUDANÇA: Chamando a nova função corrigida >>>
                    insert_table_after_paragraph(p, doc, dados_tabela[k], dados) # Passa 'dados' completos
    
    # Processa texto em todos os parágrafos no final
    for p in all_paragraphs:
        replace_text_in_paragraph(p, dados_texto)

def converter_para_pdf(caminho_docx):
    """Converte um arquivo DOCX para PDF usando LibreOffice."""
    downloads_dir = get_downloads_folder()
    os.makedirs(downloads_dir, exist_ok=True)
    comando = ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(downloads_dir), str(caminho_docx)]
    result = subprocess.run(comando, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Erro na conversão para PDF com soffice:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
    nome_base = Path(caminho_docx).stem
    caminho_pdf_esperado = downloads_dir / f"{nome_base}.pdf"
    if not caminho_pdf_esperado.exists():
        raise FileNotFoundError(f"Arquivo PDF não encontrado em {caminho_pdf_esperado} após a conversão.")
    return str(caminho_pdf_esperado)


# ==== App principal ====
def main():
    st.set_page_config(layout="wide")
    st.title("Gerador de Relatórios a partir de Templates")

    try:
        if not firebase_admin._apps:
            FIREBASE_KEY_PATH = os.getenv("FIREBASE_KEY_PATH", "app/firebase_key.json")
            cred = credentials.Certificate(FIREBASE_KEY_PATH)
            firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erro ao inicializar o Firebase: {e}")
        return

    db = firestore.client()
    
    # Interface de busca
    campo_escolhido = st.selectbox("Buscar projeto por:", ["N° do Contrato", "Objeto"])
    mapa_campos = {"N° do Contrato": "n_contrato", "Objeto": "objeto"}
    termo_busca = st.text_input(f"Digite o {campo_escolhido} para buscar:")

    if st.button("Buscar Projetos"):
        projetos_ref = db.collection("projetos")
        docs = projetos_ref.where(mapa_campos[campo_escolhido], '>=', termo_busca).where(mapa_campos[campo_escolhido], '<=', termo_busca + '\uf8ff').stream()

        st.subheader("Projetos encontrados:")
        resultados = [(doc.id, doc.to_dict()) for doc in docs]

        if resultados:
            for doc_id, data in resultados:
                st.markdown(f"---")
                st.write(f"**Projeto ID:** `{doc_id}`")
                st.write(f"**Objeto:** {data.get('objeto', 'N/A')}")
                
                if st.button(f"Gerar Relatório", key=f"gerar_pdf_{doc_id}"):
                    with st.spinner("Gerando relatório..."):
                        try:
                            dados_preenchimento = data.copy()
                            
                            # Lógica para gerar gráfico (se houver dados para isso)
                            dados_grafico_exemplo = data.get('dados_grafico', {})
                            if dados_grafico_exemplo:
                                temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                                gerar_grafico_exemplo(dados_grafico_exemplo, temp_img.name)
                                dados_preenchimento['grafico_performance'] = temp_img.name
                            
                            caminho_template = "template/Template_ata_ebserh.docx"
                            if not os.path.exists(caminho_template):
                                st.error(f"Template não encontrado: {caminho_template}")
                                return
                            
                            doc_obj = Document(caminho_template)
                            preencher_campos(doc_obj, dados_preenchimento)

                            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_docx:
                                doc_obj.save(temp_docx.name)
                                pdf_path = converter_para_pdf(temp_docx.name)

                            with open(pdf_path, "rb") as pdf_file:
                                pdf_bytes = pdf_file.read()
                                st.download_button(
                                    label="📥 Baixar Relatório em PDF",
                                    data=pdf_bytes,
                                    file_name=f"relatorio_{doc_id}.pdf",
                                    mime="application/pdf"
                                )
                            st.success(f"Relatório gerado com sucesso!")

                        except Exception as e:
                            st.error(f"Ocorreu um erro: {e}")
                        finally:
                            if 'temp_img' in locals() and os.path.exists(temp_img.name):
                                os.remove(temp_img.name)
        else:
            st.info("Nenhum projeto encontrado com os critérios fornecidos.")

if __name__ == "__main__":
    main()