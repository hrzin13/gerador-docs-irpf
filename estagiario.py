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

# --- CONFIGURAÇÕES ---
# ⚠️ GARANTA QUE O ID ABAIXO ESTÁ CERTO (É A PASTA RAIZ DO DRIVE)
FOLDER_ID_RAIZ = "1hxtNpuLtMiwfahaBRQcKrH6w_2cN_YFQ" 

CEREBRO_DO_ROBO = {
    "1. Despesas Médicas": ["unimed", "hospital", "clinica", "medico", "dentista"],
    "2. Educação": ["escola", "faculdade", "universidade", "colegio", "ensino"],
    "3. Rendimentos": ["informe de rendimentos", "holerite", "salario"],
    "4. Bancos e Finanças": ["extrato", "banco", "itau", "nubank", "caixa"],
    "5. Impostos Pagos": ["darf", "das", "receita federal"],
    "6. Veículos": ["ipva", "licenciamento", "detran"],
    "7. Imóveis": ["iptu", "aluguel", "condominio"]
}

# --- FUNÇÕES ---

def get_drive_service():
    try:
        # Tenta pegar as credenciais do arquivo json (que vc subiu no Render como Secret File)
        creds = service_account.Credentials.from_service_account_file(
            'service_account.json', 
            scopes=['https://www.googleapis.com/auth/drive']
        )
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"Erro Auth Google: {e}")
        return None

def ocr_google_drive(service, arquivo_bytes, nome_arquivo):
    """
    Mágica: Sobe a FOTO pro Drive convertendo pra Google Docs (OCR),
    depois baixa como PDF com texto selecionável.
    """
    try:
        # 1. Sobe como Google Doc (faz o OCR)
        meta = {
            'name': nome_arquivo, 
            'mimeType': 'application/vnd.google-apps.document', # Isso força o OCR
            'parents': [FOLDER_ID_RAIZ] # Usa a pasta raiz temporariamente
        }
        media = MediaIoBaseUpload(arquivo_bytes, mimetype='image/jpeg', resumable=True)
        arquivo_criado = service.files().create(body=meta, media_body=media, fields='id').execute()
        file_id = arquivo_criado.get('id')

        # 2. Baixa de volta como PDF
        pdf_content = service.files().export(fileId=file_id, mimeType='application/pdf').execute()
        
        # 3. Limpa a bagunça (apaga o arquivo temporário do Drive)
        service.files().delete(fileId=file_id).execute()

        return io.BytesIO(pdf_content)
    except Exception as e:
        print(f"Erro no OCR: {e}")
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
        
        # Debug: Imprime o que leu no log do Render (ajuda a achar erros)
        print(f"Texto lido: {texto_limpo[:100]}") 

        for pasta, palavras in CEREBRO_DO_ROBO.items():
            for p in palavras:
                if normalizar_texto(p) in texto_limpo: return pasta
        return "Geral (Não Identificado)"
    except Exception as e:
        print(f"Erro Leitura PDF: {e}")
        return "Erro Leitura"

def salvar_drive(service, pdf_bytes, nome_arq, nome_pasta):
    try:
        # Acha pasta destino ou cria
        q = f"name = '{nome_pasta}' and '{FOLDER_ID_RAIZ}' in parents and trashed=false"
        res = service.files().list(q=q).execute().get('files', [])
        if not res:
            meta = {'name': nome_pasta, 'parents': [FOLDER_ID_RAIZ], 'mimeType': 'application/vnd.google-apps.folder'}
            id_destino = service.files().create(body=meta).execute()['id']
        else: id_destino = res[0]['id']
        
        # Salva o arquivo final
        meta_arq = {'name': nome_arq, 'parents': [id_destino]}
        media = MediaIoBaseUpload(pdf_bytes, mimetype='application/pdf')
        service.files().create(body=meta_arq, media_body=media).execute()
        return True
    except Exception as e:
        print(f"Erro Salvar: {e}")
        return False

# --- ROTAS ---
@app.route("/bot", methods=['POST'])
def bot():
    tem_arquivo = int(request.values.get('NumMedia', 0))
    resp = MessagingResponse()
    
    if tem_arquivo > 0:
        url = request.values.get('MediaUrl0')
        tipo = request.values.get('MediaContentType0') # image/jpeg, application/pdf, etc
        
        # Baixa o arquivo do WhatsApp
        r = requests.get(url)
        arquivo_original = io.BytesIO(r.content)
        
        service = get_drive_service()
        if service:
            
            # SE FOR IMAGEM -> FAZ OCR
            if "image" in tipo:
                pdf_para_ler = ocr_google_drive(service, arquivo_original, "temp_ocr")
            # SE JÁ FOR PDF -> LÊ DIRETO
            elif "pdf" in tipo:
                pdf_para_ler = arquivo_original
            else:
                resp.message("❌ Formato não suportado. Mande Foto ou PDF.")
                return str(resp)

            if pdf_para_ler:
                # 1. Classifica
                pasta_destino = decidir_pasta(pdf_para_ler)
                
                # 2. Salva
                pdf_para_ler.seek(0) # Volta pro início do arquivo
                salvar_drive(service, pdf_para_ler, f"ZAP_DOC.pdf", pasta_destino)
                
                resp.message(f"✅ Recebi! Classifiquei como *{pasta_destino}* e salvei no Drive.")
            else:
                resp.message("❌ Erro ao processar a imagem.")
        else:
            resp.message("❌ Erro de conexão com o Google (Chave Secreta).")
    else:
        resp.message("Mande uma foto ou PDF.")

    return str(resp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
