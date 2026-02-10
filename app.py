import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Configuração da página
st.set_page_config(page_title="Upload IRPF", layout="centered")

# --- AUTENTICAÇÃO ROBUSTA (SERVICE ACCOUNT) ---
def autenticar_drive():
    # Pega as credenciais direto dos Segredos do Streamlit
    gcp_service_account = st.secrets["gcp_service_account"]
    
    # Cria as credenciais a partir do dicionário
    creds = service_account.Credentials.from_service_account_info(
        gcp_service_account,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    return creds

# --- FUNÇÃO DE UPLOAD ---
def fazer_upload(arquivo, folder_id):
    try:
        creds = autenticar_drive()
        service = build('drive', 'v3', credentials=creds)

        file_metadata = {
            'name': arquivo.name,
            'parents': [folder_id] # ID da pasta que você compartilhou com o robô
        }
        
        media = MediaIoBaseUpload(arquivo, mimetype=arquivo.type, resumable=True)
        
        arquivo_drive = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        return True
    except Exception as e:
        st.error(f"Erro no upload: {e}")
        return False

# --- INTERFACE ---
st.title("Envio de Documentos - IRPF")
st.info("Arquivos serão organizados na pasta: **IRPF / Pablo Henrique**")

# ID DA PASTA NO DRIVE (Você pega isso na URL quando abre a pasta no navegador)
# Exemplo: drive.google.com/drive/folders/1abcDEFgHiJkLmNoPqRsTuVwXyZ
FOLDER_ID_DESTINO = "COLOQUE_O_ID_DA_SUA_PASTA_AQUI" 

uploaded_file = st.file_uploader("Selecione o documento (Foto ou PDF)", type=['png', 'jpg', 'jpeg', 'pdf'])

if uploaded_file is not None:
    if st.button("🚀 Iniciar Upload Seguro"):
        with st.spinner("Enviando para a nuvem..."):
            sucesso = fazer_upload(uploaded_file, FOLDER_ID_DESTINO)
            if sucesso:
                st.success("Arquivo enviado com sucesso!")
                st.balloons()
