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

# ==== Funções auxiliares ====
def get_downloads_folder():
    home = Path.home()
    return home / "Downloads"

def extrair_campos(doc):
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
    for p in doc.paragraphs:
        for k, v in dados.items():
            p.text = p.text.replace(f"{{{{{k}}}}}", str(v))
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    for k, v in dados.items():
                        p.text = p.text.replace(f"{{{{{k}}}}}", str(v))

def converter_para_pdf(caminho_docx):
    downloads_dir = get_downloads_folder()
    os.makedirs(downloads_dir, exist_ok=True)
    comando = [
        "soffice",
        "--headless",
        "--convert-to", "pdf",
        "--outdir", str(downloads_dir),
        caminho_docx
    ]
    result = subprocess.run(comando, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Erro na conversão para PDF:\n{result.stderr}")

    arquivos = os.listdir(downloads_dir)
    pdfs = [f for f in arquivos if f.lower().endswith(".pdf")]
    if not pdfs:
        raise FileNotFoundError(f"Nenhum arquivo PDF encontrado na pasta {downloads_dir}")
    pdfs = sorted(pdfs, key=lambda f: os.path.getmtime(os.path.join(downloads_dir, f)), reverse=True)
    return os.path.join(downloads_dir, pdfs[0])

# ==== App principal ====
def main():
    st.set_page_config(layout="wide")
    st.title("Consulta de Projetos e Geração de PDF")

    FIREBASE_KEY_PATH = os.getenv("FIREBASE_KEY_PATH", "app/firebase_key.json")
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_KEY_PATH)
        firebase_admin.initialize_app(cred)

    db = firestore.client()

    campos = {
        "N° do Contrato": "n_contrato",
        "Período de Vigência": "periodo_vigencia",
        "N° da OS/OFB/NE": "n_os",
        "Objeto": "objeto",
        "Valor dos Bens/Serviços Recebidos": "valor_bens_receb",
        "Contratante": "contratante",
        "Contratada": "contratada"
    }

    campo_escolhido = st.selectbox("Selecione o campo para buscar:", list(campos.keys()))
    termo_busca = st.text_input("Digite o termo para busca:")

    projetos_ref = db.collection("projetos")
    docs = projetos_ref.stream()

    st.subheader("Projetos encontrados:")
    campo_firebase = campos[campo_escolhido]
    resultados = []

    for doc in docs:
        data = doc.to_dict()
        if termo_busca.lower() in str(data.get(campo_firebase, "")).lower():
            resultados.append((doc.id, data))

    if resultados:
        for doc_id, data in resultados:
            df_info = pd.DataFrame({
                "Item": list(campos.keys()),
                "Info": [data.get(campos[campo], "") for campo in campos]
            })
            st.dataframe(df_info, use_container_width=True)

            if st.button(f"Gerar PDF"):
                try:
                    # Copiar template fixo para temporário
                    caminho_fixo = "template/Template_ata_ebserh.docx"
                    if not os.path.exists(caminho_fixo):
                        st.error(f"Template não encontrado: {caminho_fixo}")
                        return
                    temp_docx = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
                    shutil.copyfile(caminho_fixo, temp_docx.name)

                    # Preencher
                    docx_obj = Document(temp_docx.name)
                    preencher_campos(docx_obj, data)

                    preenchido_path = tempfile.NamedTemporaryFile(delete=False, suffix=".docx").name
                    docx_obj.save(preenchido_path)

                    # Converter e salvar em Downloads
                    pdf_path = converter_para_pdf(preenchido_path)

                    with open(pdf_path, "rb") as pdf_file:
                        st.download_button(
                            label="📥 Baixar PDF",
                            data=pdf_file,
                            file_name=f"projeto_{doc_id}.pdf",
                            mime="application/pdf"
                        )

                    st.success(f"PDF gerado e salvo em: {pdf_path}")
                except Exception as e:
                    st.error(f"Erro ao gerar PDF: {e}")
    else:
        st.info("Nenhum projeto encontrado.")

if __name__ == "__main__":
    main()
