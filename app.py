import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import datetime

# --- Configurações ---
# ID da pasta no Google Drive (é aquele código no final do link quando você abre a pasta)
# Exemplo: drive.google.com/drive/folders/1aBcDeFgHiJkLmNoPqRsTuVwXyZ
PASTA_ID = st.secrets["pasta_id"] 

# Configuração da página
st.set_page_config(page_title="Envio de Documentos", page_icon="📂")

# --- Função de Conexão com o Drive ---
def upload_para_drive(arquivo, nome_cliente):
    # Autenticação usando os "Segredos" do Streamlit
    creds_dict = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=['https://www.googleapis.com/auth/drive']
    )
    service = build('drive', 'v3', credentials=creds)

    # Criação do nome do arquivo: "João Silva - cpf.pdf"
    nome_final = f"{nome_cliente} - {arquivo.name}"

    file_metadata = {
        'name': nome_final,
        'parents': [PASTA_ID]
    }
    
    media = MediaIoBaseUpload(arquivo, mimetype=arquivo.type)
    
    arquivo_drive = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    
    return arquivo_drive.get('id')

# --- Interface ---
st.title("📂 Envio de Documentos IRPF")
st.write("Envie seus comprovantes diretamente para nossa nuvem segura.")
st.divider()

nome_cliente = st.text_input("Seu Nome Completo")
arquivos = st.file_uploader("Anexar Documentos", accept_multiple_files=True)

if st.button("📤 Enviar Documentos"):
    if not nome_cliente or not arquivos:
        st.error("Preencha seu nome e anexe os arquivos.")
    else:
        barra = st.progress(0)
        status = st.empty()
        
        total = len(arquivos)
        for i, arquivo in enumerate(arquivos):
            status.write(f"Enviando {arquivo.name}...")
            try:
                upload_para_drive(arquivo, nome_cliente)
                barra.progress((i + 1) / total)
            except Exception as e:
                st.error(f"Erro ao enviar {arquivo.name}: {e}")
                
        status.success("✅ Tudo pronto! Seus documentos foram salvos com sucesso.")
        st.balloons()
