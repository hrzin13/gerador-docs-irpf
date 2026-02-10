import streamlit as st
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Configuração da página para parecer app de celular
st.set_page_config(page_title="Upload IRPF", layout="centered")

# --- 1. AUTENTICAÇÃO (Mantenha a que deu certo para você) ---
def get_drive_service():
    # Tenta pegar Service Account (Robô)
    if "gcp_service_account" in st.secrets:
        creds_dict = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=['https://www.googleapis.com/auth/drive']
        )
    # Ou tenta pegar Refresh Token (OAuth)
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

# --- 2. GERENCIADOR DE PASTAS (A Mágica do CPF) ---
def buscar_ou_criar_pasta_cpf(service, folder_pai_id, cpf):
    # 1. Procura se já existe uma pasta com esse CPF
    query = f"name = '{cpf}' and '{folder_pai_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = response.get('files', [])

    if files:
        # Achou a pasta! Retorna o ID dela.
        return files[0]['id']
    else:
        # Não achou. Vamos criar.
        file_metadata = {
            'name': cpf,
            'parents': [folder_pai_id],
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')

# --- 3. FUNÇÃO DE UPLOAD ---
def fazer_upload(arquivo, folder_id_cpf):
    try:
        service = get_drive_service()
        
        file_metadata = {
            'name': arquivo.name,
            'parents': [folder_id_cpf] # Salva dentro da pasta do CPF
        }
        
        media = MediaIoBaseUpload(arquivo, mimetype=arquivo.type, resumable=True)
        
        service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        return True
    except Exception as e:
        st.error(f"Erro no envio: {e}")
        return False

# --- 4. INTERFACE DO USUÁRIO ---
st.title("📂 Sistema IRPF")

# ID DA PASTA RAIZ (A pasta "IRPF / Pablo Henrique")
# Certifique-se que este ID está correto no seu código!
FOLDER_ID_RAIZ = "1hxtNpuLtMiwfahaBRQcKrH6w_2cN_YFQ" 
# Se você já salvou nos secrets, pode usar: st.secrets["google_auth"]["folder_id"]

# --- Fluxo de CPF ---
if "cpf_atual" not in st.session_state:
    st.session_state["cpf_atual"] = ""

# Se não tem CPF definido, mostra a tela de login
if not st.session_state["cpf_atual"]:
    st.info("Identifique o cliente para começar.")
    cpf_input = st.text_input("Digite o CPF do Cliente:", max_chars=14, placeholder="000.000.000-00")
    
    if st.button("Acessar Pasta do Cliente", use_container_width=True):
        if len(cpf_input) > 5: # Validação simples
            st.session_state["cpf_atual"] = cpf_input
            st.rerun() # Recarrega a página
        else:
            st.warning("Digite um CPF válido.")

# Se já tem CPF, mostra a tela de upload
else:
    st.markdown(f"### Cliente: **{st.session_state['cpf_atual']}**")
    
    # Botão para trocar de cliente
    if st.button("Trocar Cliente", type="secondary"):
        st.session_state["cpf_atual"] = ""
        st.rerun()

    st.write("---")
    uploaded_file = st.file_uploader("Selecione o documento", type=['jpg', 'png', 'pdf', 'jpeg'])

    if uploaded_file:
        if st.button("Enviar Documento 🚀", use_container_width=True):
            with st.spinner(f"Criando/Buscando pasta para {st.session_state['cpf_atual']}..."):
                
                service = get_drive_service()
                
                # AQUI É O PULO DO GATO:
                # Ele descobre qual é a pasta do CPF antes de enviar
                folder_id_cpf = buscar_ou_criar_pasta_cpf(service, FOLDER_ID_RAIZ, st.session_state['cpf_atual'])
                
                # Faz o upload na pasta certa
                if fazer_upload(uploaded_file, folder_id_cpf):
                    st.success(f"Sucesso! Arquivo salvo na pasta do CPF {st.session_state['cpf_atual']}")
                    st.balloons()
