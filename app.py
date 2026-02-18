import streamlit as st
import io
import unicodedata
from pypdf import PdfReader
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import google.generativeai as genai  # <--- NOVA IMPORTAÇÃO

st.set_page_config(page_title="Gestor Inteligente & Criativo", layout="wide")

# --- 0. CONFIGURAÇÃO DA IA (GEMINI) ---
# Você precisa colocar sua chave aqui ou no st.secrets["gemini_api_key"]

# --- 1. O CÉREBRO DO ROBÔ (MANTIDO DO ORIGINAL) ---
# Mantivemos a lógica de classificação caso você queira organizar arquivos pessoais
CEREBRO_DO_ROBO = {
    "1. Saúde e Bem-estar": ["unimed", "hospital", "clinica", "medico", "exame", "laboratorio", "academia", "nutricionista"],
    "2. Educação e Cursos": ["escola", "faculdade", "udemy", "alura", "curso", "livro", "material didatico"],
    "3. Financeiro e Rendimentos": ["comprovante", "holerite", "pagamento", "recibo", "nota fiscal", "banco", "pix"],
    "4. Documentos Pessoais": ["rg", "cpf", "cnh", "certidao", "passaporte"],
    "5. Contratos e Jurídico": ["contrato", "procuracao", "termo", "assinatura"],
    "6. Veículos e Transporte": ["ipva", "multa", "uber", "combustivel", "oficina"],
    "7. Casa e Moradia": ["aluguel", "condominio", "luz", "agua", "internet", "iptu"]
}

# --- 2. FERRAMENTAS (FUNÇÕES UTILITÁRIAS) ---

def limpar_apenas_numeros(texto):
    return "".join([c for c in texto if c.isdigit()])

def normalizar_texto(texto):
    try:
        texto = texto.lower()
        nfkd_form = unicodedata.normalize('NFKD', texto)
        return "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    except:
        return ""

def extrair_texto_do_pdf(pdf_bytes):
    """Extrai texto puro de um arquivo PDF na memória."""
    try:
        reader = PdfReader(pdf_bytes)
        texto_completo = ""
        for page in reader.pages:
            texto_completo += (page.extract_text() or "") + " "
        return texto_completo
    except Exception as e:
        return ""

# --- 3. INTEGRAÇÃO COM GEMINI (NOVA FUNÇÃO) ---
def gerar_conteudo_com_ia(texto_base, tipo_conteudo):
    """
    Usa o texto extraído pelo OCR e pede para o Gemini criar algo novo.
    """
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompts = {
        "Post Instagram": """
            Atue como um estrategista de Social Media.
            Baseado no texto abaixo (que veio de um OCR), crie um Post para Instagram (Carrossel).
            Estrutura:
            1. Headline (Título Chamativo)
            2. 3 Tópicos principais resumidos
            3. Uma frase de impacto final.
            Use emojis.
            Texto base:
            """,
        "Resumo Simples": """
            Atue como um professor didático.
            Resuma o texto abaixo em tópicos simples e fáceis de entender para uma criança de 10 anos.
            Texto base:
            """,
        "Extrair Dados": """
            Analise o texto abaixo e extraia apenas datas, valores monetários e nomes de empresas/pessoas em formato de lista.
            Texto base:
            """
    }
    
    prompt_final = prompts.get(tipo_conteudo, prompts["Resumo Simples"]) + f"\n\n---\n{texto_base}\n---"
    
    try:
        response = model.generate_content(prompt_final)
        return response.text
    except Exception as e:
        return f"Erro na IA: {e}. Verifique sua API Key."

# --- 4. CONEXÃO GOOGLE DRIVE (MANTIDA) ---
def get_drive_service():
    try:
        if "gcp_service_account" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], scopes=['https://www.googleapis.com/auth/drive'])
        elif "google_auth" in st.secrets:
            info = st.secrets["google_auth"]
            creds = Credentials(None, refresh_token=info["refresh_token"], 
                              token_uri="https://oauth2.googleapis.com/token",
                              client_id=info["client_id"], client_secret=info["client_secret"])
        else:
            return None
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Erro Conexão Google: {e}")
        return None

def ocr_pelo_google(service, arquivo_upload, folder_temp_id):
    """Sobe imagem, converte pra Docs (OCR) e baixa como PDF."""
    try:
        meta = {'name': "temp_ocr", 'mimeType': 'application/vnd.google-apps.document', 'parents': [folder_temp_id]}
        media = MediaIoBaseUpload(arquivo_upload, mimetype=arquivo_upload.type, resumable=True)
        file_doc = service.files().create(body=meta, media_body=media, fields='id').execute()
        doc_id = file_doc.get('id')
        
        pdf_content = service.files().export(fileId=doc_id, mimeType='application/pdf').execute()
        service.files().delete(fileId=doc_id).execute()
        
        return io.BytesIO(pdf_content)
    except Exception as e:
        st.error(f"Erro no OCR: {e}")
        return None

def salvar_na_pasta_certa(service, pdf_bytes, nome_arquivo, nome_pasta, id_raiz):
    # Lógica simplificada para salvar direto na raiz ou pasta específica
    # Se quiser criar pastas por CPF, mantenha a lógica antiga. Aqui simplifiquei para salvar direto.
    try:
        meta_arquivo = {'name': nome_arquivo, 'parents': [id_raiz]}
        media = MediaIoBaseUpload(pdf_bytes, mimetype='application/pdf', resumable=True)
        service.files().create(body=meta_arquivo, media_body=media, fields='id').execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

# --- 5. INTERFACE PRINCIPAL ---

st.title("🧠 Central de Inteligência & Arquivo")
st.markdown("Uma ferramenta para organizar documentos e **gerar conteúdo** a partir deles.")

# ID da pasta onde o OCR temporário acontece (e onde arquivos são salvos)
# Mude isso para o ID da sua pasta real
FOLDER_ID_RAIZ = "1hxtNpuLtMiwfahaBRQcKrH6w_2cN_YFQ" 

service = get_drive_service()

if not service:
    st.error("Erro de conexão com Google Drive. Verifique seus secrets.")
    st.stop()

# --- ABAS PARA SEPARAR AS FUNÇÕES ---
tab_conteudo, tab_arquivo = st.tabs(["✨ Fábrica de Conteúdo (Novo)", "📂 Arquivo Digital (Antigo)"])

# --- ABA 1: FÁBRICA DE CONTEÚDO (O QUE DÁ LUCRO/LINKS) ---
with tab_conteudo:
    st.header("Transforme Papel em Post/Resumo")
    st.info("Tire foto de um livro, apostila ou documento e deixe a IA criar para você.")
    
    upload_criativo = st.file_uploader("Suba a imagem/PDF aqui", type=["png", "jpg", "jpeg", "pdf"], key="upload_criativo")
    
    tipo_transformacao = st.selectbox(
        "O que você quer criar?",
        ["Post Instagram", "Resumo Simples", "Extrair Dados"]
    )
    
    if upload_criativo and st.button("🚀 Processar e Criar"):
        with st.spinner("1/2: Lendo a imagem com Google OCR..."):
            # Usa o OCR do Drive (usa a pasta raiz como temp)
            pdf_resultado = ocr_pelo_google(service, upload_criativo, FOLDER_ID_RAIZ)
        
        if pdf_resultado:
            with st.spinner("2/2: A Inteligência Artificial está escrevendo..."):
                # Extrai texto do PDF gerado
                texto_bruto = extrair_texto_do_pdf(pdf_resultado)
                
                # Manda para o Gemini
                resultado_ia = gerar_conteudo_com_ia(texto_bruto, tipo_transformacao)
                
                st.success("Conteúdo Gerado com Sucesso!")
                
                col_res1, col_res2 = st.columns(2)
                with col_res1:
                    st.subheader("📝 Resultado:")
                    st.write(resultado_ia)
                    st.code(resultado_ia) # Fácil de copiar
                
                with col_res2:
                    st.subheader("🔍 Texto Original Lido:")
                    with st.expander("Ver texto bruto"):
                        st.text(texto_bruto)
        else:
            st.error("Falha ao ler o arquivo.")

# --- ABA 2: ARQUIVO DIGITAL (SUA LÓGICA ANTIGA) ---
with tab_arquivo:
    st.header("Organizador de Documentos")
    
    if "cpf_atual" not in st.session_state: st.session_state["cpf_atual"] = ""

    if not st.session_state["cpf_atual"]:
        cpf_input = st.text_input("Digite o Identificador (CPF ou Nome) da Pasta:", key="cpf_input")
        if st.button("Acessar Pasta", key="btn_cpf"):
            st.session_state["cpf_atual"] = cpf_input
            st.rerun()
    else:
        st.success(f"Logado na pasta: {st.session_state['cpf_atual']}")
        if st.button("Sair"):
            st.session_state["cpf_atual"] = ""
            st.rerun()
            
        arquivos_para_guardar = st.file_uploader("Arquivos para arquivar", accept_multiple_files=True, key="upload_arquivo")
        
        if arquivos_para_guardar and st.button("🗂️ Arquivar Agora"):
            # Lógica simplificada de salvar e organizar
            # Cria/Busca pasta do cliente dentro da Raiz
            # (Aqui você pode reutilizar sua lógica completa de subpastas se quiser)
            
            progress_bar = st.progress(0)
            
            for i, f in enumerate(arquivos_para_guardar):
                pdf_ocr = ocr_pelo_google(service, f, FOLDER_ID_RAIZ)
                if pdf_ocr:
                    texto = extrair_texto_do_pdf(pdf_ocr)
                    texto_norm = normalizar_texto(texto)
                    
                    # Classificação simples baseada no dicionário antigo
                    pasta_destino = "Geral"
                    for cat, chaves in CEREBRO_DO_ROBO.items():
                        for chave in chaves:
                            if normalizar_texto(chave) in texto_norm:
                                pasta_destino = cat
                                break
                    
                    # Salva
                    nome_final = f"{pasta_destino} - {f.name.split('.')[0]}.pdf"
                    pdf_ocr.seek(0)
                    salvar_na_pasta_certa(service, pdf_ocr, nome_final, pasta_destino, FOLDER_ID_RAIZ)
                    st.toast(f"Salvo em: {pasta_destino}")
                
                progress_bar.progress((i + 1) / len(arquivos_para_guardar))
            
            st.success("Processo finalizado!")
