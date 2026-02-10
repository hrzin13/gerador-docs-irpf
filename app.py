import streamlit as st
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Configuração da página
st.set_page_config(page_title="Upload IRPF", layout="centered")

# --- 1. AUTENTICAÇÃO ---
def get_drive_service():
    # Tenta pegar Service Account (Robô)
    if "gcp_service_account" in st.secrets:
        creds_dict = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=['https://www.googleapis.com/auth/drive']
        )
    # Ou tenta pegar Refresh Token (OAuth - O que deu certo pra você)
    elif "google_auth" in st.secrets:
        info = st.secrets["google_auth"]
        creds = Credentials(
            None,
            refresh_token=info["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=info["client_id"],
            client_secret=info["client_secret"]
        )
    else:
        st.error("Nenhuma credencial encontrada nos Secrets!")
        return None
        
    return build('drive', 'v3', credentials=creds)

# --- 2. GERENCIADOR DE PASTAS (CPF) ---
def buscar_ou_criar_pasta_cpf(service, folder_pai_id, cpf):
    query = f"name = '{cpf}' and '{folder_pai_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = response.get('files', [])

    if files:
        return files[0]['id']
    else:
        file_metadata = {
            'name': cpf,
            'parents': [folder_pai_id],
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')

# --- 3. FUNÇÃO DE UPLOAD ---
def fazer_upload(service, arquivo, folder_id_cpf):
    try:
        file_metadata = {
            'name': arquivo.name,
            'parents': [folder_id_cpf]
        }
        media = MediaIoBaseUpload(arquivo, mimetype=arquivo.type, resumable=True)
        service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        return True
    except Exception as e:
        st.error(f"Erro no arquivo {arquivo.name}: {e}")
        return False

# --- 4. INTERFACE DO USUÁRIO ---
st.title("📂 Envio de Documentos IRPF")

# SEU ID DA PASTA PRINCIPAL AQUI
FOLDER_ID_RAIZ = "1hxtNpuLtMiwfahaBRQcKrH6w_2cN_YFQ"
# Ou se estiver nos secrets: st.secrets["google_auth"]["folder_id"]

if "cpf_atual" not in st.session_state:
    st.session_state["cpf_atual"] = ""

# --- TELA 1: IDENTIFICAÇÃO ---
if not st.session_state["cpf_atual"]:
    st.info("Digite seu CPF para começar o envio.")
    cpf_input = st.text_input("CPF (somente números):", max_chars=14)
    
    if st.button("Continuar", use_container_width=True):
        if len(cpf_input) > 5:
            st.session_state["cpf_atual"] = cpf_input
            st.rerun()
        else:
            st.warning("Por favor, digite um CPF válido.")

# --- TELA 2: UPLOAD MÚLTIPLO ---
else:
    st.markdown(f"### Cliente: **{st.session_state['cpf_atual']}**")
    
    if st.button("Sair / Trocar CPF", type="secondary"):
        st.session_state["cpf_atual"] = ""
        st.rerun()

    st.write("---")
    
    # A MÁGICA ESTÁ AQUI: accept_multiple_files=True
    uploaded_files = st.file_uploader(
        "Selecione todos os documentos e fotos:", 
        type=['jpg', 'png', 'pdf', 'jpeg'],
        accept_multiple_files=True 
    )

    if uploaded_files:
        st.write(f"📁 **{len(uploaded_files)} arquivos selecionados.**")
        
        if st.button(f"Enviar {len(uploaded_files)} Arquivos 🚀", use_container_width=True):
            
            # Barra de progresso
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            service = get_drive_service()
            
            # Busca/Cria a pasta uma única vez antes do loop
            status_text.text("Verificando pasta do cliente...")
            folder_id_cpf = buscar_ou_criar_pasta_cpf(service, FOLDER_ID_RAIZ, st.session_state['cpf_atual'])
            
            sucessos = 0
            
            # Loop para enviar um por um
            for i, arquivo in enumerate(uploaded_files):
                status_text.text(f"Enviando: {arquivo.name}...")
                
                if fazer_upload(service, arquivo, folder_id_cpf):
                    sucessos += 1
                
                # Atualiza barra de progresso
                percentual = (i + 1) / len(uploaded_files)
                progress_bar.progress(percentual)
            
            status_text.text("Finalizado!")
            st.success(f"✅ Sucesso! {sucessos} de {len(uploaded_files)} arquivos foram enviados.")
            
            # Limpa a lista para não enviar duplicado se clicar de novo
            if st.button("Enviar mais arquivos"):
                st.rerun()
