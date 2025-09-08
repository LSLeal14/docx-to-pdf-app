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

# --- IMPORTAÇÃO DA NOVA FUNÇÃO ---
# Certifique-se de que o arquivo com a função abaixo se chama 'processamento.py'
# e está na mesma pasta que este script.
from processamento import gerar_tabela_percentual, gerar_tabela_previsto_realizado

# ==== Funções auxiliares ====
def get_downloads_folder():
    """Retorna o caminho para a pasta de Downloads do usuário."""
    home = Path.home()
    return home / "Downloads"

def extrair_campos(doc):
    """Extrai todos os placeholders {{campo}} de um documento Word."""
    campos = set()
    for p in doc.paragraphs:
        campos.update(re.findall(r"\{\{(.*?)\}\}", p.text))
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    campos.update(re.findall(r"\{\{(.*?)\}\}", p.text))
    return list(campos)

def preencher_campos(doc, dados):
    """
    Substitui placeholders {{chave}} no documento por:
      - Texto (str/int/float)
      - Imagem (caminho .png/.jpg/.jpeg)
      - Tabela (list[dict] ou pandas.DataFrame) com grid.
    """
    def is_image(v):
        return isinstance(v, (str, Path)) and str(v).lower().endswith((".png", ".jpg", ".jpeg"))

    def is_table(v):
        if isinstance(v, pd.DataFrame):
            return True
        if isinstance(v, list) and v and all(isinstance(r, dict) for r in v):
            return True
        return False

    def normalize_table(v):
        if isinstance(v, pd.DataFrame):
            return v.to_dict(orient="records")
        return v

    def replace_text_in_paragraph(p, mapping_text):
        original_text = p.text
        for k, v in mapping_text.items():
            placeholder = f"{{{{{k}}}}}"
            if placeholder in p.text:
                # Substitui o placeholder pelo valor, mantendo o resto do texto
                p.text = p.text.replace(placeholder, str(v))

    def paragraph_only_placeholder(p, placeholder):
        return p.text.strip() == placeholder

    def insert_image_at_paragraph(p, img_path):
        for r in p.runs:
            r.text = ""
        p.add_run().add_picture(str(img_path), width=Inches(2))

    def insert_table_after_paragraph(doc, p, records):
        """Cria uma tabela com grid e cabeçalho em negrito."""
        if not records:
            return
        cols = list(records[0].keys())
        
        table = doc.add_table(rows=1 + len(records), cols=len(cols), style='Table Grid')
        table.autofit = True

        hdr_cells = table.rows[0].cells
        for j, c in enumerate(cols):
            run = hdr_cells[j].paragraphs[0].add_run(str(c))
            run.bold = True

        for i, row_data in enumerate(records, start=1):
            row_cells = table.rows[i].cells
            for j, c in enumerate(cols):
                cell_value = row_data.get(c)
                row_cells[j].text = "" if cell_value is None else str(cell_value)
                
        p._element.addnext(table._element)

    dados_texto, dados_imagem, dados_tabela = {}, {}, {}
    for k, v in dados.items():
        if is_image(v):
            dados_imagem[k] = v
        elif is_table(v):
            dados_tabela[k] = normalize_table(v)
        else:
            dados_texto[k] = v

    all_paragraphs = list(doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                all_paragraphs.extend(cell.paragraphs)

    for p in all_paragraphs:
        for k, rows in dados_tabela.items():
            ph = f"{{{{{k}}}}}"
            if ph in p.text:
                # Limpa o parágrafo antes de inserir a tabela
                p.text = p.text.replace(ph, "")
                insert_table_after_paragraph(doc, p, rows)
        
        for k, img in dados_imagem.items():
            ph = f"{{{{{k}}}}}"
            if ph in p.text:
                if paragraph_only_placeholder(p, ph):
                    insert_image_at_paragraph(p, img)
                else:
                    # Se houver mais texto, a imagem é inserida inline
                    p.text = p.text.replace(ph, "")
                    p.add_run().add_picture(str(img), width=Inches(2))

        replace_text_in_paragraph(p, dados_texto)

def converter_para_pdf(caminho_docx):
    """Converte um arquivo .docx para .pdf usando LibreOffice."""
    downloads_dir = get_downloads_folder()
    os.makedirs(downloads_dir, exist_ok=True)
    comando = [
        "soffice", "--headless", "--convert-to", "pdf",
        "--outdir", str(downloads_dir), caminho_docx
    ]
    result = subprocess.run(comando, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Erro na conversão para PDF:\n{result.stderr}")

    base_name = Path(caminho_docx).stem
    pdf_path = downloads_dir / f"{base_name}.pdf"
    
    if not pdf_path.exists():
         raise FileNotFoundError(f"Arquivo PDF esperado não foi encontrado em: {pdf_path}")
    
    return str(pdf_path)

# ==== App principal ====
def main():
    st.set_page_config(layout="wide")
    st.title("Consulta de Projetos e Geração de PDF")

    # Inicialização do Firebase (evita reinicializar)
    if not firebase_admin._apps:
        try:
            FIREBASE_KEY_PATH = os.getenv("FIREBASE_KEY_PATH", "app/firebase_key.json")
            cred = credentials.Certificate(FIREBASE_KEY_PATH)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Erro ao inicializar Firebase: {e}")
            st.stop()

    db = firestore.client()

    campos = {
        "N° do Contrato": "n_contrato", "Período de Vigência": "periodo_vigencia",
        "N° da OS/OFB/NE": "n_os", "Objeto": "objeto",
        "Valor dos Bens/Serviços Recebidos": "valor_bens_receb",
        "Contratante": "contratante", "Contratada": "contratada"
    }

    campo_escolhido = st.selectbox("Selecione o campo para buscar:", list(campos.keys()))
    termo_busca = st.text_input("Digite o termo para busca:")

    projetos_ref = db.collection("projetos")
    
    st.subheader("Projetos encontrados:")
    campo_firebase = campos[campo_escolhido]
    
    # Otimiza a busca para não carregar todos os documentos de uma vez
    query = projetos_ref.stream()
    resultados = []
    for doc in query:
        data = doc.to_dict()
        if termo_busca.lower() in str(data.get(campo_firebase, "")).lower():
            resultados.append((doc.id, data))

    if resultados:
        for doc_id, data in resultados:
            st.markdown(f"---")
            #st.write(f"**ID do Projeto:** `{doc_id}`")
            df_info = pd.DataFrame({
                "Item": list(campos.keys()),
                "Info": [str(data.get(campos[campo], "")) for campo in campos]
            })
            st.table(df_info)

            if st.button(f"Gerar PDF para o Projeto", key=f"gerar_pdf_{doc_id}"):
                with st.spinner("Gerando documento..."):
                    try:
                        # --- ALTERAÇÃO PRINCIPAL ---
                        # 1. Gera a Tabela 1 usando a função importada
                        tabela_1_df = gerar_tabela_percentual(db, doc_id)
                        
                        if tabela_1_df is None:
                            st.error("Falha ao gerar a tabela de análise percentual.")
                            continue

                        tabela_2_df = gerar_tabela_previsto_realizado(db, doc_id)
                        
                        if tabela_2_df is None:
                            st.error("Falha ao gerar a tabela de de comparativo.")
                            continue

                        # 2. Adiciona a tabela ao dicionário de dados
                        dados_para_template = data.copy()
                        # A chave 'Tabela 1' deve corresponder ao placeholder {{Tabela 1}} no Word
                        dados_para_template['table'] = tabela_1_df
                        dados_para_template['table_2'] = tabela_2_df
                        
                        # Copia o template para um local temporário
                        caminho_template = "template/Template_ata_ebserh.docx"
                        if not os.path.exists(caminho_template):
                            st.error(f"Template não encontrado: {caminho_template}")
                            continue
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_docx:
                            shutil.copyfile(caminho_template, temp_docx.name)
                            
                            # Preenche o documento com todos os dados (incluindo a nova tabela)
                            doc_obj = Document(temp_docx.name)
                            preencher_campos(doc_obj, dados_para_template)
                            doc_obj.save(temp_docx.name)
                            
                            # Converte para PDF
                            pdf_path = converter_para_pdf(temp_docx.name)

                        with open(pdf_path, "rb") as pdf_file:
                            st.download_button(
                                label="✔️ Baixar PDF Pronto",
                                data=pdf_file,
                                file_name=f"projeto_{doc_id}.pdf",
                                mime="application/pdf",
                                key=f"download_{doc_id}"
                            )
                        st.success(f"PDF gerado com sucesso! Salvo em sua pasta de Downloads.")
                    
                    except Exception as e:
                        st.error(f"Erro ao gerar PDF: {e}")
    else:
        st.info("Nenhum projeto encontrado com os critérios de busca.")

if __name__ == "__main__":
    main()
