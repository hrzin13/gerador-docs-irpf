import streamlit as st
import io
import unicodedata
import requests
import time
import socket # <-- Biblioteca adicionada para controlar o tempo da internet
from pypdf import PdfReader
from google.oauth2.credentials import Credentials 
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from google import genai
from PIL import Image

# --- BLINDAGEM CONTRA TIMEOUT ---
# Dá até 2 minutos para o Google Drive processar arquivos grandes sem cortar a conexão
socket.setdefaulttimeout(120) 

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
        p, li, span, label {{ color: #e0e0e0 !important; font-weight: 500; }}
        </style>
        """,
        unsafe_allow_html=True
    )

configurar_visual_montanha()

# --- 1. CONFIGURAÇÃO DAS APIs (GEMINI E HUGGING FACE) ---
try:
    API_KEY = st.secrets["gemini_api_key"]
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    st.error("❌ Erro: Não encontrei a 'gemini_api_key' nos secrets.")
    client = None

try:
    HF_TOKEN = st.secrets["hf_token"]
except Exception as e:
    HF_TOKEN = None
    st.warning("⚠️ Token da Hugging Face não encontrado nos secrets.")

# --- 2. CONFIGURAÇÃO DO GOOGLE DRIVE ---
def get_drive_service():
    try:
        if "google_auth" in st.secrets:
            info = st.secrets["google_auth"]
            creds = Credentials(
                None, 
                refresh_token=info["refresh_token"],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=info["client_id"],
                client_secret=info["client_secret"]
            )
            return build('drive', 'v3', credentials=creds)
        else:
            return None
    except Exception as e:
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

# --- 4. INTELIGÊNCIA ARTIFICIAL (TEXTO E IMAGEM) ---
def gerar_conteudo_com_ia(texto_base, tipo_conteudo, pedir_imagem=False):
    tentativas = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-2.5-pro']
    
    prompts = {
        "Post Instagram": """
            Atue como Social Media. Crie um Post de Instagram (Carrossel).
            Estrutura: Título Impactante + 3 Dicas Práticas + Chamada para Ação.
            Use emojis. Seja direto.
            """,
        "Resumo Simples": "Resuma o texto de forma didática para leigos.",
        "Extrair Dados": "Liste apenas: Datas, Valores (R$) e Nomes Próprios."
    }
    
    prompt_final = f"{prompts.get(tipo_conteudo)}\n\nTexto para analisar:\n{texto_base}"
    
    if pedir_imagem:
        prompt_final += "\n\nIMPORTANTE: No final da sua resposta, pule duas linhas e escreva EXATAMENTE 'PROMPT_VISUAL:' seguido de uma descrição curta (máximo 2 frases) em inglês, detalhando como seria uma imagem criativa e sem texto escrito para ilustrar esse post."

    log_erros = []
    if client:
        for modelo_nome in tentativas:
            try:
                response = client.models.generate_content(
                    model=modelo_nome,
                    contents=prompt_final
                )
                return response.text
            except Exception as e:
                log_erros.append(f"Erro {modelo_nome}: {str(e)}")
                continue 

    return f"❌ Falha Total na IA.\nLog de erros:\n" + "\n".join(log_erros)

def gerar_imagem_com_ia(prompt_visual):
    """Gera imagens usando o modelo oficial mais estável da Hugging Face"""
    
    # URL corrigida para o modelo super estável da RunwayML
    API_URL = "https://router.huggingface.co/hf-inference/models/runwayml/stable-diffusion-v1-5"
    
    if not HF_TOKEN:
        return "❌ Erro: O token da Hugging Face não foi configurado nos secrets."
        
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {"inputs": prompt_visual}
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        
        # O erro 503 significa que o modelo está sendo carregado no servidor deles
        if response.status_code == 503:
            with st.status("☕ A IA está acordando... aguarde um instante.", expanded=False):
                time.sleep(15) 
                response = requests.post(API_URL, headers=headers, json=payload)

        if response.status_code == 200:
            image_bytes = response.content
            imagem_pronta = Image.open(io.BytesIO(image_bytes))
            return imagem_pronta
        else:
            return f"❌ Erro na API Hugging Face ({response.status_code}): {response.text}"
            
    except Exception as e:
        return f"❌ Erro inesperado: {str(e)}"

# --- 5. O MOTOR DO GOOGLE DRIVE (OCR) ---
def ocr_pelo_google(service, arquivo, folder_id):
    try:
        meta = {'name': "temp_ocr_gemini", 'mimeType': 'application/vnd.google-apps.document', 'parents': [folder_id]}
        media = MediaIoBaseUpload(arquivo, mimetype=arquivo.type, resumable=True)
        
        # Adicionado num_retries=3 para o Google tentar de novo em caso de falha na rede
        file_doc = service.files().create(body=meta, media_body=media, fields='id').execute(num_retries=3)
        file_id = file_doc.get('id')
        
        pdf_content = service.files().export(fileId=file_id, mimeType='application/pdf').execute(num_retries=3)
        service.files().delete(fileId=file_id).execute(num_retries=3)
        
        return io.BytesIO(pdf_content)
    except Exception as e:
        st.error(f"Erro no OCR: {e}")
        return None

# --- 6. INTERFACE PRINCIPAL (TELA) ---
st.title("🏔️ Gestor Inteligente")

service = get_drive_service()

try:
    FOLDER_ID_RAIZ = st.secrets["google_auth"]["folder_id"]
except:
    FOLDER_ID_RAIZ = "root"

if not service:
    st.warning("⚠️ Conexão Google Drive falhou. Verifique os secrets.")
else:
    tab_conteudo, tab_arquivo = st.tabs(["✨ Criar Conteúdo (IA)", "📂 Arquivos"])

    with tab_conteudo:
        st.info("Usando motor de IA avançado para texto e Hugging Face para imagens")
        
        upload = st.file_uploader("Arquivo (Foto/PDF)", type=["png","jpg","jpeg","pdf"], key="up_ia")
        tipo = st.selectbox("O que você quer?", ["Post Instagram", "Resumo Simples", "Extrair Dados"])
        
        quer_imagem = st.checkbox("🎨 Gerar Imagem Ilustrativa Exclusiva (IA)", value=False)
        
        if upload and st.button("Gerar Mágica ✨"):
            with st.spinner("1/3 Enviando para Google Drive (OCR)..."):
                pdf = ocr_pelo_google(service, upload, FOLDER_ID_RAIZ)
            
            if pdf:
                with st.spinner("2/3 Lendo documento e escrevendo o texto..."):
                    texto = extrair_texto_do_pdf(pdf)
                    res_completa = gerar_conteudo_com_ia(texto, tipo, pedir_imagem=quer_imagem)
                    
                    texto_post = res_completa
                    prompt_visual = ""
                    
                    if "PROMPT_VISUAL:" in res_completa:
                        partes = res_completa.split("PROMPT_VISUAL:")
                        texto_post = partes[0].strip()
                        prompt_visual = partes[1].strip()
                
                st.success("Processo Finalizado!")
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.markdown("### 📝 Texto Gerado:")
                    st.write(texto_post)
                
                with col2:
                    if quer_imagem and prompt_visual:
                        with st.spinner("3/3 Desenhando a imagem exclusiva..."):
                            imagem = gerar_imagem_com_ia(prompt_visual)
                            
                            st.markdown("### 🖼️ Sua Imagem:")
                            if isinstance(imagem, str):
                                st.error(imagem)
                            else:
                                st.image(imagem, caption="Imagem criada sob medida para o seu texto.")
                                with st.expander("Ver roteiro da imagem (Prompt)"):
                                    st.caption(prompt_visual)
                    elif quer_imagem:
                         st.warning("A IA falhou em criar o roteiro visual desta vez.")
                
                st.write("---")
                with st.expander("🔍 Ver texto original lido (OCR)"):
                    st.text(texto)

    with tab_arquivo:
        st.write("Seus arquivos organizados.")
