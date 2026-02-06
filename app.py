import streamlit as st
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Portal IRPF - Clientes", page_icon="👤")

def get_drive_service():
    token_info = st.secrets["oauth"]
    creds_dict = {
        "token": "fake_token", 
        "refresh_token": token_info["refresh_token"],
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": token_info["client_id"],
        "client_secret": token_info["client_secret"],
        "scopes": ["https://www.googleapis.com/auth/drive.file"],
        "universe_domain": "googleapis.com",
        "account": "",
        "expiry": "2024-01-01T00:00:00Z"
    }
    creds = Credentials.from_authorized_user_info(creds_dict)
    return build('drive', 'v3', credentials=creds)

# --- Funções Inteligentes do Drive ---

def buscar_ou_criar_pasta(service, nome_cliente, pasta_pai_id):
    # 1. Procura se a pasta já existe
    query = f"name = '{nome_cliente}' and '{pasta_pai_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    response = service.files().list(q=query, fields="files(id)").execute()
    files = response.get('files', [])

    if files:
        return files[0]['id'] # Retorna o ID da pasta existente
    else:
        # 2. Se não existir, cria uma nova
        meta = {
            'name': nome_cliente,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [pasta_pai_id]
        }
        folder = service.files().create(body=meta, fields='id').execute()
        return folder.get('id')

# --- Interface ---
st.title("📂 Área de Envio do Cliente")
st.subheader("Organização Automática por Pastas")

PASTA_MESTRA_ID = st.secrets["pasta_id"]

# Simulação de Login simples
nome_cliente = st.text_input("Digite seu Nome Completo (Será o nome da sua pasta)", placeholder="Ex: João da Silva")

if nome_cliente:
    st.info(f"Arquivos serão organizados na pasta: **IRPF / {nome_cliente}**")
    arquivos = st.file_uploader("Selecione os documentos", accept_multiple_files=True)

    if st.button("🚀 Iniciar Upload Seguro", type="primary"):
        if not arquivos:
            st.warning("Selecione os arquivos antes de enviar.")
        else:
            status = st.empty()
            bar = st.progress(0)
            
            try:
                service = get_drive_service()
                
                # Garante que a pasta do cliente existe
                id_pasta_cliente = buscar_ou_criar_pasta(service, nome_cliente.strip(), PASTA_MESTRA_ID)
                
                for i, arquivo in enumerate(arquivos):
                    status.text(f"Enviando {i+1} de {len(arquivos)}: {arquivo.name}")
                    
                    metadata = {
                        'name': arquivo.name,
                        'parents': [id_pasta_cliente]
                    }
                    media = MediaIoBaseUpload(arquivo, mimetype=arquivo.type)
                    service.files().create(body=metadata, media_body=media).execute()
                    
                    bar.progress((i + 1) / len(arquivos))
                
                status.success(f"✅ Concluído! Tudo salvo na pasta de {nome_cliente}.")
                st.balloons()
            except Exception as e:
                st.error(f"Erro: {e}")
