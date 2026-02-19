import streamlit as st
import io
import unicodedata
from pypdf import PdfReader
from google.oauth2.credentials import Credentials 
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
        p, li, span, label {{ color: #e0e0e0 !important; font-weight: 500; }}
        </style>
        """,
        unsafe_allow_html=True
    )

configurar_visual_montanha()

# --- 1. CONFIGURAÇÃO DA IA (GEMINI) ---
try:
    API_KEY = st.secrets["gemini_api_key"]
    genai.configure(api_key=API_KEY)
except Exception as e:
    st.error("❌ Erro: Não encontrei a 'gemini_api_key' nos secrets.")

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
    
    # Se o usuário pediu imagem, ensinamos o robô de texto a criar o roteiro da imagem
    if pedir_imagem:
        prompt_final += "\n\nIMPORTANTE: No final da sua resposta, pule duas linhas e escreva EXATAMENTE 'PROMPT_VISUAL:' seguido de uma descrição rica, em inglês, detalhando como seria uma imagem perfeita, realista e criativa para ilustrar esse conteúdo."

    log_erros = []
    for modelo_nome in tentativas:
        try:
            model = genai.GenerativeModel(modelo_nome)
            response = model.generate_content(prompt_final)
            return response.text
        except Exception as e:
            log_erros.append(f"Erro {modelo_nome}: {str(e)}")
            continue 

    return f"❌ Falha Total na IA.\nLog de erros:\n" + "\n".join(log_erros)

def gerar_imagem_com_ia(prompt_visual):
    """Pega a descrição gerada e pede pro modelo de Imagem desenhar"""
    # Modelos de imagem que apareceram liberados na sua conta
    modelos_imagem = ['models/gemini-2.0-flash-exp-image-generation', 'models/gemini-3-pro-image-preview', 'imagen-3.0-generate-001']
    
    log_erros = []
    for modelo in modelos_imagem:
        try:
            # Invoca o pintor digital
            img_model = genai.ImageGenerationModel(modelo)
            resposta = img_model.generate_images(
                prompt=prompt_visual,
                number_of_images=1
            )
            # Retorna a foto gerada
            return resposta.images[0].image
        except Exception as e:
            log_erros.append(str(e))
            continue
            
    return f"Erro ao gerar imagem: {log_erros}"

# --- 5. O MOTOR DO GOOGLE DRIVE (OCR) ---
def ocr_pelo_google(service, arquivo, folder_id):
    try:
        meta = {'name': "temp_ocr_gemini", 'mimeType': 'application/vnd.google-apps.document', 'parents': [folder_id]}
        media = MediaIoBaseUpload(arquivo, mimetype=arquivo.type, resumable=True)
        file_doc = service.files().create(body=meta, media_body=media, fields='id').execute()
        file_id = file_doc.get('id')
        
        pdf_content = service.files().export(fileId=file_id, mimeType='application/pdf').execute()
        service.files().delete(fileId=file_id).execute()
        
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
        st.info(f"Usando motor de IA avançado (Série 2.5/3.0)")
        
        upload = st.file_uploader("Arquivo (Foto/PDF)", type=["png","jpg","jpeg","pdf"], key="up_ia")
        tipo = st.selectbox("O que você quer?", ["Post Instagram", "Resumo Simples", "Extrair Dados"])
        
        # O novo botão de escolher se quer imagem
        quer_imagem = st.checkbox("🎨 Gerar Imagem Ilustrativa Exclusiva (IA)", value=False)
        
        if upload and st.button("Gerar Mágica ✨"):
            with st.spinner("1/3 Enviando para Google Drive (OCR)..."):
                pdf = ocr_pelo_google(service, upload, FOLDER_ID_RAIZ)
            
            if pdf:
                with st.spinner("2/3 Lendo documento e escrevendo o texto..."):
                    texto = extrair_texto_do_pdf(pdf)
                    res_completa = gerar_conteudo_com_ia(texto, tipo, pedir_imagem=quer_imagem)
                    
                    # Vamos separar o que é o Post e o que é o Prompt da Imagem
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
                    # Se o usuário marcou a caixa e a IA gerou o roteiro visual
                    if quer_imagem and prompt_visual:
                        with st.spinner("3/3 Desenhando a imagem exclusiva..."):
                            imagem = gerar_imagem_com_ia(prompt_visual)
                            
                            st.markdown("### 🖼️ Sua Imagem:")
                            if isinstance(imagem, str) and "Erro" in imagem:
                                st.error(imagem)
                            else:
                                st.image(imagem, caption="Imagem criada sob medida para o seu texto.")
                                # Mostra o que a IA pensou pra desenhar
                                with st.expander("Ver roteiro da imagem"):
                                    st.caption(prompt_visual)
                    elif quer_imagem:
                         st.warning("A IA falhou em criar o roteiro visual desta vez.")
                
                st.write("---")
                with st.expander("🔍 Ver texto original lido (OCR)"):
                    st.text(texto)

    with tab_arquivo:
        st.write("Seus arquivos organizados.")
