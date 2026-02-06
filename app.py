import streamlit as st
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Envio Docs", page_icon="📂")

# --- Função de Conexão (Versão OAuth) ---
def get_drive_service():
    # Pega as credenciais da seção [oauth] dos segredos
    try:
        token_info = st.secrets["oauth"]
    except KeyError:
        st.error("Erro: A configuração 'oauth' não foi encontrada nos Segredos.")
        st.stop()
    
    # Monta a credencial
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

# --- Interface ---
st.title("📂 Envio de Documentos")
st.write("Sistema de envio seguro para o Google Drive.")

# Pega o ID da pasta
try:
    PASTA_ID = st.secrets["pasta_id"]
except:
    st.error("Configure o 'pasta_id' nos Segredos!")
    st.stop()

nome = st.text_input("Nome Completo")
arquivos = st.file_uploader("Anexar Arquivos", accept_multiple_files=True)

if st.button("Enviar Arquivos", type="primary"):
    if not nome or not arquivos:
        st.warning("Preencha o nome e anexe arquivos.")
    else:
        status = st.empty()
        bar = st.progress(0)
        
        try:
            service = get_drive_service()
            
            for i, arquivo in enumerate(arquivos):
                status.text(f"Enviando: {arquivo.name}...")
                
                metadata = {
                    'name': f"{nome} - {arquivo.name}",
                    'parents': [PASTA_ID]
                }
                
                media = MediaIoBaseUpload(arquivo, mimetype=arquivo.type)
                
                service.files().create(
                    body=metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                
                bar.progress((i + 1) / len(arquivos))
                
            status.success("✅ Sucesso! Arquivos enviados.")
            st.balloons()
            
        except Exception as e:
            st.error(f"Erro técnico: {e}")
