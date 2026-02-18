import streamlit as st
import io
import unicodedata
from pypdf import PdfReader
from google.oauth2.credentials import Credentials # Importante para seu tipo de login
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import google.generativeai as genai

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestor Inteligente & Criativo", layout="wide", page_icon="🏔️")

# --- 🎨 VISUAL MONTANHA (CSS) ---
def configurar_visual_montanha():
    imagem_url = "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?q=80&w=2670&auto=format&fit=crop"
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.7)), url("{imagem_url}");
            background-attachment: fixed;
            background-size: cover;
            background-position: center;
        }}
        .stTabs [data-baseweb="tab-list"] {{
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 10px;
        }}
        h1, h2, h3 {{ color: #ffffff !important; text-shadow: 2px 2px 4px #000000; }}
        p, li, span {{ color: #e0e0e0 !important; font-weight: 500; }}
        </style>
        """,
        unsafe_allow_html=True
    )

configurar_visual_montanha()

# --- 1. CONFIGURAÇÃO DA IA (GEMINI) ---
# Pega a chave direto dos seus secrets: gemini_api_key = "AIzaSy..."
try:
    API_KEY = st.secrets["gemini_api_key"]
    genai.configure(api_key=API_KEY)
except Exception as e:
    st.error("❌ Erro: Não encontrei a 'gemini_api_key' nos secrets.")

# --- 2. CONFIGURAÇÃO DO GOOGLE DRIVE (Ajustado para seu google_auth) ---
def get_drive_service():
    """Conecta no Drive usando o refresh_token dos seus secrets"""
    try:
        # Verifica se existe a seção [google_auth] nos secrets
        if "google_auth" in st.secrets:
            info = st.secrets["google_auth"]
            
            # Monta a credencial usando seus dados
            creds = Credentials(
                None, # Access token (será gerado automaticamente)
                refresh_token=info["refresh_token"],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=info["client_id"],
                client_secret=info["client_secret"]
            )
            return build('drive', 'v3', credentials=creds)
        else:
            st.error("❌ Seção [google_auth] não encontrada no secrets.toml")
            return None
    except Exception as e:
        st.error(f"❌ Erro na conexão com Google: {e}")
        return None

# --- 3. FERRAMENTAS UTILITÁRIAS ---
def extrair_texto_do_pdf(pdf_bytes):
    try:
        reader = PdfReader(pdf_bytes)
        texto_completo = ""
        for page in reader.pages:
            texto_completo += (page.extract_text() or "") + " "
        return texto_completo
    except:
        return ""

def gerar_conteudo_com_ia(texto_base, tipo_conteudo):
    # Tenta usar o modelo Pro, se falhar tenta o Flash
    modelo_nome = 'gemini-1.5-flash' 
    try:
        model = genai.GenerativeModel(modelo_nome)
        prompts = {
            "Post Instagram": """
                Atue como Social Media. Crie um Post de Instagram (Carrossel).
                Estrutura: Título Impactante + 3 Dicas Práticas + Chamada para Ação.
                Use emojis. Seja direto.
                """,
            "Resumo Simples": "Resuma o texto de forma didática para leigos.",
            "Extrair Dados": "Liste apenas: Datas, Valores (R$) e Nomes Próprios."
        }
        prompt = f"{prompts.get(tipo_conteudo)}\n\nTexto:\n{texto_base}"
        return model.generate_content(prompt).text
    except Exception as e:
        return f"Erro na IA ({modelo_nome}): {e}"

def ocr_pelo_google(service, arquivo, folder_id):
    """Sobe imagem pro Drive, converte e baixa PDF"""
    try:
        # Cria arquivo temporário Google Docs
        meta = {'name': "temp_ocr_gemini", 'mimeType': 'application/vnd.google-apps.document', 'parents': [folder_id]}
        media = MediaIoBaseUpload(arquivo, mimetype=arquivo.type, resumable=True)
        file_doc = service.files().create(body=meta, media_body=media, fields='id').execute()
        file_id = file_doc.get('id')
        
        # Baixa como PDF (que agora tem texto selecionável)
        pdf_content = service.files().export(fileId=file_id, mimeType='application/pdf').execute()
        
        # Limpa a sujeira (deleta o arquivo temporário do Drive)
        service.files().delete(fileId=file_id).execute()
        
        return io.BytesIO(pdf_content)
    except Exception as e:
        st.error(f"Erro no OCR: {e}")
        return None

# --- 4. INTERFACE PRINCIPAL ---

st.title("🏔️ Gestor Inteligente")

# Tenta conectar
service = get_drive_service()

# Pega o ID da pasta direto dos secrets também!
try:
    FOLDER_ID_RAIZ = st.secrets["google_auth"]["folder_id"]
except:
    st.warning("⚠️ 'folder_id' não encontrado em [google_auth]. Usando raiz.")
    FOLDER_ID_RAIZ = "root"

if not service:
    st.warning("⚠️ Conexão Google Drive falhou. Verifique os secrets.")
else:
    # --- ABAS ---
    tab_conteudo, tab_arquivo = st.tabs(["✨ Criar Conteúdo (IA)", "📂 Arquivos"])

    # ABA 1: FÁBRICA DE CONTEÚDO
    with tab_conteudo:
        st.info("Suba uma foto e deixe a IA trabalhar.")
        upload = st.file_uploader("Arquivo (Foto/PDF)", type=["png","jpg","jpeg","pdf"], key="up_ia")
        tipo = st.selectbox("O que você quer?", ["Post Instagram", "Resumo Simples", "Extrair Dados"])
        
        if upload and st.button("Gerar Mágica ✨"):
            with st.spinner("1/2 Enviando para Google Drive (OCR)..."):
                pdf = ocr_pelo_google(service, upload, FOLDER_ID_RAIZ)
            
            if pdf:
                with st.spinner("2/2 A Inteligência Artificial está pensando..."):
                    texto = extrair_texto_do_pdf(pdf)
                    res = gerar_conteudo_com_ia(texto, tipo)
                    
                    st.success("Pronto!")
                    # Mostra resultado em destaque
                    st.markdown("### 📝 Resultado Gerado:")
                    st.markdown(res)
                    
                    # Mostra texto original em um expansor
                    with st.expander("Ver texto original lido"):
                        st.text(texto)

    # ABA 2: ARQUIVO (Sua lógica antiga simplificada)
    with tab_arquivo:
        st.write("Seus arquivos organizados.")
        # Se quiser implementar a lógica de salvar pastas depois, pode adicionar aqui.
