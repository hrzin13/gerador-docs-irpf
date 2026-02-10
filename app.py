import streamlit as st
import io
import os
import tempfile
import ocrmypdf
from PIL import Image
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Configuração da página
st.set_page_config(page_title="Upload IRPF", layout="centered")

# --- 1. AUTENTICAÇÃO (Mantendo a que funciona pra você) ---
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
        st.error("Erro: Credenciais não encontradas.")
        return None
    return build('drive', 'v3', credentials=creds)

# --- 2. FUNÇÃO: FOTO -> PDF A4 PESQUISÁVEL ---
def converter_imagem_para_pdf_padrao(image_file):
    try:
        # Abre a imagem enviada
        img = Image.open(image_file)
        
        # Converte para RGB se necessário (pra evitar erro com PNG transparente)
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        # Cria uma folha A4 Branca (2480 x 3508 pixels = A4 em 300 DPI)
        a4_width, a4_height = 2480, 3508
        a4_canvas = Image.new('RGB', (a4_width, a4_height), (255, 255, 255))
        
        # Redimensiona a imagem para caber no A4 com margem
        img.thumbnail((a4_width - 150, a4_height - 150), Image.Resampling.LANCZOS)
        
        # Centraliza
        w, h = img.size
        x = (a4_width - w) // 2
        y = (a4_height - h) // 2
        a4_canvas.paste(img, (x, y))
        
        # Salva o temp
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_img:
            a4_canvas.save(tmp_img.name, quality=95, dpi=(300, 300))
            tmp_img_path = tmp_img.name
        
        output_pdf_path = tmp_img_path.replace(".jpg", ".pdf")
        
        # RODA O OCR (O segredo do texto selecionável)
        ocrmypdf.ocr(
            tmp_img_path, 
            output_pdf_path, 
            language='por', 
            deskew=True,       # Desentorta
            force_ocr=True,    # Obriga a ler
            image_dpi=300,     # Força qualidade alta
            optimize=1
        )
        
        with open(output_pdf_path, "rb") as f:
            pdf_bytes = f.read()
            
        # Limpa tudo
        if os.path.exists(tmp_img_path): os.remove(tmp_img_path)
        if os.path.exists(output_pdf_path): os.remove(output_pdf_path)
        
        return io.BytesIO(pdf_bytes)

    except Exception as e:
        print(f"Erro na conversão: {e}")
        return None

# --- 3. UPLOAD ---
def fazer_upload(service, arquivo_bytes, nome, folder_id, mime_type):
    try:
        file_metadata = {'name': nome, 'parents': [folder_id]}
        media = MediaIoBaseUpload(arquivo_bytes, mimetype=mime_type, resumable=True)
        service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar no Drive: {e}")
        return False

# --- 4. TELA ---
st.title("📂 Digitalizador Pro IRPF")

# ID DA SUA PASTA AQUI
FOLDER_ID_RAIZ = "1hxtNpuLtMiwfahaBRQcKrH6w_2cN_YFQ" 

if "cpf_atual" not in st.session_state:
    st.session_state["cpf_atual"] = ""

if not st.session_state["cpf_atual"]:
    cpf = st.text_input("CPF do Cliente:", max_chars=14)
    if st.button("Entrar"):
        if len(cpf) > 5:
            st.session_state["cpf_atual"] = cpf
            st.rerun()
else:
    st.markdown(f"### Cliente: **{st.session_state['cpf_atual']}**")
    if st.button("Sair"):
        st.session_state["cpf_atual"] = ""
        st.rerun()
        
    uploaded_files = st.file_uploader("Fotos/Documentos", type=['jpg','png','jpeg','pdf'], accept_multiple_files=True)
    
    if uploaded_files and st.button("Processar e Enviar"):
        service = get_drive_service()
        
        # Lógica simples de pasta: Tenta achar, se não achar cria
        query = f"name = '{st.session_state['cpf_atual']}' and '{FOLDER_ID_RAIZ}' in parents and trashed = false"
        res = service.files().list(q=query).execute()
        files = res.get('files', [])
        
        if files:
            folder_id = files[0]['id']
        else:
            meta = {'name': st.session_state['cpf_atual'], 'parents': [FOLDER_ID_RAIZ], 'mimeType': 'application/vnd.google-apps.folder'}
            folder_id = service.files().create(body=meta).execute()['id']
            
        bar = st.progress(0)
        
        for i, file in enumerate(uploaded_files):
            # Se for imagem, converte pra PDF A4
            if file.type in ['image/jpeg', 'image/png', 'image/jpg']:
                st.toast(f"Convertendo {file.name}...")
                pdf_bytes = converter_imagem_para_pdf_padrao(file)
                if pdf_bytes:
                    novo_nome = file.name.rsplit('.', 1)[0] + ".pdf"
                    fazer_upload(service, pdf_bytes, novo_nome, folder_id, 'application/pdf')
                else:
                    fazer_upload(service, file, file.name, folder_id, file.type)
            # Se já for PDF, só sobe
            else:
                fazer_upload(service, file, file.name, folder_id, file.type)
            
            bar.progress((i + 1) / len(uploaded_files))
            
        st.success("Concluído!")
        st.balloons()
