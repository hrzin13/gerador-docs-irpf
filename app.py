import streamlit as st
import io
import os
import tempfile
import ocrmypdf
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Configuração da página
st.set_page_config(page_title="Upload IRPF", layout="centered")

# --- 1. AUTENTICAÇÃO ---
def get_drive_service():
    if "gcp_service_account" in st.secrets:
        creds_dict = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=['https://www.googleapis.com/auth/drive']
        )
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

# --- 2. FUNÇÃO MÁGICA: FOTO -> PDF PESQUISÁVEL (CORRIGIDA) ---
def converter_imagem_para_pdf_ocr(image_file):
    try:
        # Cria um arquivo temporário para a imagem
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_img:
            tmp_img.write(image_file.getvalue())
            tmp_img_path = tmp_img.name
        
        output_pdf_path = tmp_img_path.replace(".jpg", ".pdf")
        
        # Roda o OCR (Transforma em PDF pesquisável)
        # CORREÇÃO AQUI: Adicionei 'image_dpi=300' para aceitar prints de tela
        ocrmypdf.ocr(
            tmp_img_path, 
            output_pdf_path, 
            language='por', 
            deskew=True, 
            force_ocr=True, 
            image_dpi=300 
        )
        
        # Lê o PDF gerado de volta para a memória
        with open(output_pdf_path, "rb") as f:
            pdf_bytes = f.read()
            
        # Limpa a sujeira
        os.remove(tmp_img_path)
        os.remove(output_pdf_path)
        
        return io.BytesIO(pdf_bytes)
        
    except Exception as e:
        # Se der erro, mostra no log mas não para o app
        print(f"Erro OCR: {e}") 
        return None

# --- 3. GERENCIADOR DE PASTAS (CPF) ---
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

# --- 4. FUNÇÃO DE UPLOAD ---
def fazer_upload(service, arquivo_bytes, nome_arquivo, folder_id_cpf, mime_type):
    try:
        file_metadata = {
            'name': nome_arquivo,
            'parents': [folder_id_cpf]
        }
        media = MediaIoBaseUpload(arquivo_bytes, mimetype=mime_type, resumable=True)
        service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        return True
    except Exception as e:
        st.error(f"Erro no envio: {e}")
        return False

# --- 5. TELA DO APLICATIVO ---
st.title("📂 Envio Inteligente IRPF")

# SEU ID DA PASTA PRINCIPAL AQUI (IMPORTANTE!)
FOLDER_ID_RAIZ = "1hxtNpuLtMiwfahaBRQcKrH6w_2cN_YFQ" 

if "cpf_atual" not in st.session_state:
    st.session_state["cpf_atual"] = ""

if not st.session_state["cpf_atual"]:
    st.info("Identificação do Cliente")
    cpf_input = st.text_input("CPF (somente números):", max_chars=14)
    if st.button("Iniciar Atendimento", use_container_width=True):
        if len(cpf_input) > 5:
            st.session_state["cpf_atual"] = cpf_input
            st.rerun()
        else:
            st.warning("CPF inválido.")
else:
    st.markdown(f"### Cliente: **{st.session_state['cpf_atual']}**")
    if st.button("Trocar Cliente", type="secondary"):
        st.session_state["cpf_atual"] = ""
        st.rerun()
    st.divider()
    
    uploaded_files = st.file_uploader("Fotos ou Documentos:", type=['jpg', 'png', 'jpeg', 'pdf'], accept_multiple_files=True)

    if uploaded_files:
        if st.button(f"Processar e Enviar ({len(uploaded_files)})", use_container_width=True):
            service = get_drive_service()
            folder_id_cpf = buscar_ou_criar_pasta_cpf(service, FOLDER_ID_RAIZ, st.session_state['cpf_atual'])
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, arquivo in enumerate(uploaded_files):
                status_text.text(f"Processando: {arquivo.name}...")
                
                # SE FOR IMAGEM -> CONVERTE PRA PDF
                if arquivo.type in ['image/jpeg', 'image/png', 'image/jpg']:
                    status_text.text(f"Convertendo {arquivo.name} para PDF pesquisável...")
                    pdf_convertido = converter_imagem_para_pdf_ocr(arquivo)
                    
                    if pdf_convertido:
                        # Upload do PDF novo
                        nome_novo = arquivo.name.rsplit('.', 1)[0] + ".pdf"
                        fazer_upload(service, pdf_convertido, nome_novo, folder_id_cpf, 'application/pdf')
                    else:
                        # Se falhar a conversão, sobe a imagem original mesmo
                        fazer_upload(service, arquivo, arquivo.name, folder_id_cpf, arquivo.type)
                
                # SE JÁ FOR PDF -> SOBE DIRETO
                else:
                    fazer_upload(service, arquivo, arquivo.name, folder_id_cpf, arquivo.type)
                
                progress_bar.progress((i + 1) / len(uploaded_files))
            
            status_text.text("Concluído!")
            st.success("✅ Todos os arquivos foram processados e salvos!")
            st.balloons()
