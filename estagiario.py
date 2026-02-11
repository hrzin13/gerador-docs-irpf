from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import requests
import io
import unicodedata
from pypdf import PdfReader
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

app = Flask(__name__)

# --- CONFIGURAÇÕES IGUAIS AO DO SEU SITE ---
# (O Estagiário precisa saber onde guardar as coisas)
FOLDER_ID_RAIZ = "1hxtNpuLtMiwfahaBRQcKrH6w_2cN_YFQ"  # <--- O MESMO ID DO OUTRO CÓDIGO
CEREBRO_DO_ROBO = {
    "1. Despesas Médicas": ["unimed", "hospital", "clinica", "medico", "dentista"],
    "2. Educação": ["escola", "faculdade", "universidade", "colegio", "ensino"],
    "3. Rendimentos": ["informe de rendimentos", "holerite", "salario"],
    "4. Bancos e Finanças": ["extrato", "banco", "itau", "nubank", "caixa"],
    "5. Impostos Pagos": ["darf", "das", "receita federal"],
    "6. Veículos": ["ipva", "licenciamento", "detran"],
    "7. Imóveis": ["iptu", "aluguel", "condominio"]
}

# --- FUNÇÕES VITAIS (CÓPIA SEGURA PARA MOBILE) ---
# O estagiário usa as mesmas ferramentas, mas sem a parte visual do Streamlit

def get_drive_service():
    # Procura o arquivo json na mesma pasta
    try:
        # Tenta achar o arquivo de credenciais padrão
        creds = service_account.Credentials.from_service_account_file(
            'service_account.json', # <--- TENHA CERTEZA QUE ESSE ARQUIVO ESTÁ NA PASTA
            scopes=['https://www.googleapis.com/auth/drive']
        )
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"Erro no Google: {e}")
        return None

def normalizar_texto(texto):
    try:
        texto = texto.lower()
        return "".join([c for c in unicodedata.normalize('NFKD', texto) if not unicodedata.combining(c)])
    except: return ""

def decidir_pasta(pdf_bytes):
    try:
        reader = PdfReader(pdf_bytes)
        texto = ""
        for page in reader.pages: texto += (page.extract_text() or "") + " "
        texto_limpo = normalizar_texto(texto)
        
        for pasta, palavras in CEREBRO_DO_ROBO.items():
            for p in palavras:
                if normalizar_texto(p) in texto_limpo: return pasta
        return "Geral (Não Identificado)"
    except: return "Erro Leitura"

def salvar_drive(service, pdf_bytes, nome_arq, nome_pasta, id_cliente):
    try:
        # Acha pasta destino
        q = f"name = '{nome_pasta}' and '{id_cliente}' in parents and trashed=false"
        res = service.files().list(q=q).execute().get('files', [])
        if not res:
            meta = {'name': nome_pasta, 'parents': [id_cliente], 'mimeType': 'application/vnd.google-apps.folder'}
            id_destino = service.files().create(body=meta).execute()['id']
        else: id_destino = res[0]['id']
        
        # Salva arquivo
        meta_arq = {'name': nome_arq, 'parents': [id_destino]}
        media = MediaIoBaseUpload(pdf_bytes, mimetype='application/pdf')
        service.files().create(body=meta_arq, media_body=media).execute()
        return True
    except: return False

# --- O OUVIDO DO ESTAGIÁRIO (WHATSAPP) ---
@app.route("/bot", methods=['POST'])
def bot():
    msg = request.values.get('Body', '').strip()
    tem_arquivo = int(request.values.get('NumMedia', 0))
    resp = MessagingResponse()
    
    # Lógica Simplificada para Celular:
    # 1. O usuário manda CPF na legenda ou texto anterior (vamos supor que é fixo ou vc manda antes)
    # Para facilitar no celular, vamos fazer ele salvar numa pasta "TRIAGEM_ZAP" se não tiver CPF
    
    if tem_arquivo > 0:
        url = request.values.get('MediaUrl0')
        pdf_bytes = io.BytesIO(requests.get(url).content)
        
        service = get_drive_service()
        if service:
            # 1. Classifica
            pasta_destino = decidir_pasta(pdf_bytes)
            
            # 2. Salva na Raiz (ou pasta específica de Triagem)
            # Como não temos o CPF aqui fácil sem login, salvamos na pasta Raiz com o nome da categoria
            # Você depois move pelo site visualmente
            
            pdf_bytes.seek(0)
            salvar_drive(service, pdf_bytes, f"ZAP_{pasta_destino}.pdf", FOLDER_ID_RAIZ, FOLDER_ID_RAIZ)
            
            resp.message(f"✅ Recebi! Classifiquei como *{pasta_destino}* e salvei no Drive.")
        else:
            resp.message("❌ Erro de conexão com o Google.")
    else:
        resp.message("Mande uma foto ou PDF que eu guardo no Drive pra você.")

    return str(resp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
