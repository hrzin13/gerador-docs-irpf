import streamlit as st
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Upload IRPF", layout="centered")

# --- CONEXÃO SEGURA COM O GOOGLE DRIVE ---
def get_drive_service():
    # Pega as chaves que você salvou nos Secrets
    info = st.secrets["google_auth"]
    
    # Recria a credencial usando o Refresh Token (Isso renova o acesso sozinho)
    creds = Credentials(
        None, 
        refresh_token=info["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=info["client_id"],
        client_secret=info["client_secret"]
    )
    return build('drive', 'v3', credentials=creds)

# --- FUNÇÃO DE UPLOAD ---
def upload_file(file_obj):
    try:
        service = get_drive_service()
        folder_id = st.secrets["google_auth"]["folder_id"]
        
        file_metadata = {
            'name': file_obj.name,
            'parents': [folder_id]
        }
        
        # Faz o upload
        media = MediaIoBaseUpload(file_obj, mimetype=file_obj.type, resumable=True)
        service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        return True
    except Exception as e:
        st.error(f"Erro no envio: {e}")
        return False

# --- TELA DO CELULAR ---
st.title("📂 Envio Rápido IRPF")
st.info("Sistema conectado via Refresh Token")

arquivo = st.file_uploader("Tirar foto ou escolher arquivo", type=['jpg', 'png', 'pdf'])

if arquivo:
    if st.button("Enviar Agora", use_container_width=True):
        with st.spinner("Enviando..."):
            if upload_file(arquivo):
                st.success("✅ Arquivo salvo no Drive com sucesso!")
                st.balloons()
