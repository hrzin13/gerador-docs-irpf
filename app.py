import streamlit as st
import io
import unicodedata
from pypdf import PdfReader
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import google.generativeai as genai

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestor Inteligente & Criativo", layout="wide", page_icon="🏔️")

# --- 🎨 NOVO: FUNÇÃO DE DESIGN (MONTANHA) ---
def configurar_visual_montanha():
    # URL de uma imagem de montanha bonita e escura (Unsplash)
    imagem_url = "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?q=80&w=2670&auto=format&fit=crop"
    
    st.markdown(
        f"""
        <style>
        /* Isso atinge o corpo principal do App */
        .stApp {{
            background-image: linear-gradient(rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.6)), url("{imagem_url}");
            background-attachment: fixed;
            background-size: cover;
            background-position: center;
        }}
        
        /* Deixar os textos mais legíveis e cards semi-transparentes */
        .stTabs [data-baseweb="tab-list"] {{
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 10px;
        }}
        
        /* Cor dos títulos para garantir contraste */
        h1, h2, h3 {{
            color: #ffffff !important;
            text-shadow: 2px 2px 4px #000000;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# APLICA O VISUAL IMEDIATAMENTE
configurar_visual_montanha()

# --- 0. CONFIGURAÇÃO DA IA (GEMINI) ---
API_KEY = st.secrets.get("gemini_api_key", "COLE_SUA_CHAVE_AQUI_SE_NAO_USAR_SECRETS")
genai.configure(api_key=API_KEY)

# --- 1. O CÉREBRO DO ROBÔ ---
CEREBRO_DO_ROBO = {
    "1. Saúde e Bem-estar": ["unimed", "hospital", "clinica", "medico", "exame", "laboratorio", "academia", "nutricionista"],
    "2. Educação e Cursos": ["escola", "faculdade", "udemy", "alura", "curso", "livro", "material didatico"],
    "3. Financeiro e Rendimentos": ["comprovante", "holerite", "pagamento", "recibo", "nota fiscal", "banco", "pix"],
    "4. Documentos Pessoais": ["rg", "cpf", "cnh", "certidao", "passaporte"],
    "5. Contratos e Jurídico": ["contrato", "procuracao", "termo", "assinatura"],
    "6. Veículos e Transporte": ["ipva", "multa", "uber", "combustivel", "oficina"],
    "7. Geral": ["diverso", "outros"]
}

# --- 2. FERRAMENTAS ---
def extrair_texto_do_pdf(pdf_bytes):
    try:
        reader = PdfReader(pdf_bytes)
        texto_completo = ""
        for page in reader.pages:
            texto_completo += (page.extract_text() or "") + " "
        return texto_completo
    except:
        return ""

def normalizar_texto(texto):
    try:
        texto = texto.lower()
        nfkd = unicodedata.normalize('NFKD', texto)
        return "".join([c for c in nfkd if not unicodedata.combining(c)])
    except:
        return ""

# --- 3. INTEGRAÇÃO GEMINI ---
def gerar_conteudo_com_ia(texto_base, tipo_conteudo):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompts = {
        "Post Instagram": """
            Atue como um estrategista de Social Media.
            Crie um Post para Instagram (Carrossel) baseado no texto.
            Estrutura: Headline Chamativa, 3 Tópicos Resumidos, Frase Final.
            Use emojis e quebras de linha.
            """,
        "Resumo Simples": "Resuma o texto abaixo de forma didática e simples.",
        "Extrair Dados": "Extraia apenas datas, valores e nomes próprios em lista."
    }
    
    prompt = f"{prompts.get(tipo_conteudo)}\n\nTexto:\n{texto_base}"
    
    try:
        return model.generate_content(prompt).text
    except Exception as e:
        return f"Erro na IA: {e}"

# --- 4. GOOGLE DRIVE ---
def get_drive_service():
    try:
        if "gcp_service_account" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], scopes=['https://www.googleapis.com/auth/drive'])
            return build('drive', 'v3', credentials=creds)
    except:
        return None
    return None

def ocr_pelo_google(service, arquivo, folder_id):
    try:
        meta = {'name': "temp_ocr", 'mimeType': 'application/vnd.google-apps.document', 'parents': [folder_id]}
        media = MediaIoBaseUpload(arquivo, mimetype=arquivo.type, resumable=True)
        file_doc = service.files().create(body=meta, media_body=media, fields='id').execute()
        
        pdf_content = service.files().export(fileId=file_doc.get('id'), mimeType='application/pdf').execute()
        service.files().delete(fileId=file_doc.get('id')).execute()
        return io.BytesIO(pdf_content)
    except:
        return None

# --- 5. INTERFACE PRINCIPAL ---

# ID DA PASTA (Substitua pelo seu ID real)
FOLDER_ID_RAIZ = "1hxtNpuLtMiwfahaBRQcKrH6w_2cN_YFQ" 

service = get_drive_service()

st.title("🏔️ Gestor Inteligente")
st.markdown("### Sua central de comando digital")

if not service:
    st.warning("⚠️ Conecte o Google Drive nos 'secrets' para usar o OCR.")
    # Continua apenas para mostrar o visual, mas avisa do erro

tab_conteudo, tab_arquivo = st.tabs(["✨ Criar Conteúdo", "📂 Arquivos"])

with tab_conteudo:
    st.info("Suba uma foto de livro ou documento para gerar posts e resumos.")
    upload = st.file_uploader("Arquivo (Foto/PDF)", type=["png","jpg","pdf"])
    tipo = st.selectbox("Objetivo:", ["Post Instagram", "Resumo Simples"])
    
    if upload and st.button("Gerar Mágica ✨"):
        if service:
            with st.spinner("Lendo e Criando..."):
                pdf = ocr_pelo_google(service, upload, FOLDER_ID_RAIZ)
                if pdf:
                    texto = extrair_texto_do_pdf(pdf)
                    res = gerar_conteudo_com_ia(texto, tipo)
                    st.success("Pronto!")
                    st.markdown(res)
        else:
            st.error("Configurar Google Drive primeiro.")

with tab_arquivo:
    st.write("Seu sistema de arquivos original continua aqui...")
    # (Sua lógica de arquivos aqui)
