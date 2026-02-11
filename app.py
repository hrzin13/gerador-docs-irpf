import streamlit as st
import io
import unicodedata
from pypdf import PdfReader
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Robô Arquivista (Blindado)", layout="centered")

# --- 1. O CÉREBRO DO ROBÔ (PALAVRAS SEM ACENTO E MINÚSCULAS) ---
CEREBRO_DO_ROBO = {
    "1. Despesas Médicas": ["unimed", "hospital", "clinica", "medico", "dentista", "odontologia", "exame", "laboratorio", "saude", "psicologo", "fonoaudiologo"],
    "2. Educação": ["escola", "faculdade", "universidade", "colegio", "ensino", "educacao", "mensalidade", "curso", "pos-graduacao"],
    "3. Rendimentos": ["informe de rendimentos", "comprovante de rendimentos", "holerite", "salario", "pro-labore", "dirf"],
    "4. Bancos e Finanças": ["extrato", "banco", "itau", "bradesco", "nubank", "inter", "caixa", "santander", "financiamento", "consorcio", "comprovante de pagamento"],
    "5. Impostos Pagos": ["darf", "das", "simples nacional", "receita federal", "guia", "tributo"],
    "6. Veículos": ["ipva", "licenciamento", "detran", "veiculo", "carro", "moto"],
    "7. Imóveis": ["iptu", "aluguel", "condominio", "imovel", "escritura"]
}

# --- 2. FERRAMENTAS DE TEXTO (LIMPEZA E NORMALIZAÇÃO) ---

def limpar_apenas_numeros(texto):
    """A Peneira: Remove tudo que não é número."""
    resultado = ""
    for caractere in texto:
        if caractere.isdigit():
            resultado += caractere
    return resultado

def normalizar_texto(texto):
    """Remove acentos e deixa minúsculo para comparação."""
    try:
        texto = texto.lower()
        nfkd_form = unicodedata.normalize('NFKD', texto)
        texto_sem_acento = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
        return texto_sem_acento
    except:
        return ""

# --- 3. CONEXÃO GOOGLE ---
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

# --- 4. GOOGLE OCR (LÊ IMAGENS) ---
def ocr_pelo_google(service, arquivo_upload, folder_temp_id):
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

# --- 5. A INTELIGÊNCIA (LÊ TUDO E CLASSIFICA) ---
def decidir_pasta(pdf_bytes):
    try:
        reader = PdfReader(pdf_bytes)
        texto_completo = ""
        
        # Lê TODAS as páginas
        for page in reader.pages:
            texto_completo += (page.extract_text() or "") + " "
        
        texto_limpo = normalizar_texto(texto_completo)
        
        # Procura palavras-chave
        for pasta, palavras_chave in CEREBRO_DO_ROBO.items():
            for palavra in palavras_chave:
                palavra_limpa = normalizar_texto(palavra)
                if palavra_limpa in texto_limpo:
                    return pasta, palavra, texto_limpo
        
        return "Geral (Não Identificado)", None, texto_limpo
    except Exception as e:
        return "Geral (Erro Leitura)", None, ""

# --- 6. O ARQUIVISTA (SALVA NO DRIVE) ---
def salvar_na_pasta_certa(service, pdf_bytes, nome_arquivo, nome_pasta, id_cliente):
    try:
        # Verifica se a sub-pasta (ex: "Saude") já existe dentro da pasta do cliente
        q = f"name = '{nome_pasta}' and '{id_cliente}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(q=q, fields="files(id)").execute()
        pastas = results.get('files', [])
        
        if not pastas:
            meta_pasta = {'name': nome_pasta, 'parents': [id_cliente], 'mimeType': 'application/vnd.google-apps.folder'}
            pasta_criada = service.files().create(body=meta_pasta, fields='id').execute()
            id_destino = pasta_criada.get('id')
        else:
            id_destino = pastas[0]['id']
            
        meta_arquivo = {'name': nome_arquivo, 'parents': [id_destino]}
        media = MediaIoBaseUpload(pdf_bytes, mimetype='application/pdf', resumable=True)
        service.files().create(body=meta_arquivo, media_body=media, fields='id').execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

# --- 7. INTERFACE E FLUXO PRINCIPAL ---
st.title("🤖 Robô Arquivista (Blindado)")

# ⚠️⚠️⚠️ COLOQUE O ID DA SUA PASTA RAIZ AQUI ⚠️⚠️⚠️
FOLDER_ID_RAIZ = "1hxtNpuLtMiwfahaBRQcKrH6w_2cN_YFQ" 

service = get_drive_service()

if service:
    # Inicializa sessão
    if "cpf_atual" not in st.session_state: 
        st.session_state["cpf_atual"] = ""

    # TELA 1: LOGIN DO CLIENTE (COM VALIDAÇÃO)
    if not st.session_state["cpf_atual"]:
        st.subheader("Acesso ao Arquivo")
        entrada_usuario = st.text_input("Digite o CPF do Cliente (com ou sem pontos):")
        
        if st.button("Acessar Pasta"):
            # 1. Passa na Peneira (Limpa)
            cpf_limpo = limpar_apenas_numeros(entrada_usuario)
            
            # 2. O Portão (Valida tamanho)
            if len(cpf_limpo) == 11:
                st.session_state["cpf_atual"] = cpf_limpo
                st.rerun() # Recarrega a página já logado
            else:
                st.error(f"❌ CPF Inválido! Encontrei {len(cpf_limpo)} números. O CPF deve ter exatamente 11 dígitos.")

    # TELA 2: ÁREA DE TRABALHO (JÁ LOGADO)
    else:
        st.success(f"🗂️ Trabalhando na pasta do CPF: **{st.session_state['cpf_atual']}**")
        
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("Sair / Trocar CPF"): 
                st.session_state["cpf_atual"] = ""
                st.rerun()
        
        st.info("O Robô lê todas as páginas, ignora acentos e organiza automaticamente.")
        
        files = st.file_uploader("Solte os documentos aqui (PDF ou Imagens):", accept_multiple_files=True)
        
        if files and st.button("Processar Documentos"):
            
            if "COLOQUE" in FOLDER_ID_RAIZ:
                st.error("🛑 PARE! Você esqueceu de configurar o ID da pasta raiz no código (Linha 127).")
                st.stop()

            # Pega ou Cria a pasta do cliente (CPF Limpo) no Drive
            try:
                cpf_pasta = st.session_state['cpf_atual']
                q = f"name = '{cpf_pasta}' and '{FOLDER_ID_RAIZ}' in parents and trashed=false"
                res = service.files().list(q=q).execute().get('files', [])
                
                if res: 
                    id_pasta_cliente = res[0]['id']
                    st.toast("Pasta do cliente encontrada!")
                else: 
                    id_pasta_cliente = service.files().create(body={
                        'name': cpf_pasta, 
                        'parents': [FOLDER_ID_RAIZ], 
                        'mimeType': 'application/vnd.google-apps.folder'
                    }).execute()['id']
                    st.toast("Nova pasta criada para este CPF!")
                
                bar = st.progress(0)
                
                for i, f in enumerate(files):
                    st.write(f"--- Processando: **{f.name}** ---")
                    
                    # 1. OCR (Converte imagem/PDF em PDF pesquisável)
                    pdf_pronto = ocr_pelo_google(service, f, id_pasta_cliente)
                    
                    if pdf_pronto:
                        # 2. Decide Pasta (Lê texto)
                        nome_pasta, palavra, texto_lido = decidir_pasta(pdf_pronto)
                        
                        if palavra:
                            st.success(f"✅ Classificado como: **{nome_pasta}** (Palavra-chave: '{palavra}')")
                        else:
                            st.warning(f"⚠️ Não identificado. Indo para: **{nome_pasta}**")
                            
                        # RAIO X
                        with st.expander("🔍 Ver o que o robô leu"):
                            st.text(texto_lido[0:1000] + "...") 
                        
                        # 3. Salva
                        nome_final = f.name.rsplit('.', 1)[0] + ".pdf"
                        pdf_pronto.seek(0)
                        salvar_na_pasta_certa(service, pdf_pronto, nome_final, nome_pasta, id_pasta_cliente)
                    
                    bar.progress((i+1)/len(files))
                
                st.balloons()
                st.success("Tudo arquivado com sucesso!")
                
            except Exception as e:
                st.error(f"Erro Geral: {e}")
