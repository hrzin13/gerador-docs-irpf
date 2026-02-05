import streamlit as st
from datetime import datetime
import time

# --- Configuração da Página (Visual Clean) ---
st.set_page_config(page_title="Envio de Documentos", page_icon="📂")

st.markdown("""
    <style>
        .stButton>button {
            width: 100%;
            background-color: #0099ff;
            color: white;
            font-size: 20px;
            padding: 10px;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📂 Envio de Documentos IRPF")
st.write("Olá! Use este canal seguro para enviar seus documentos para a declaração.")
st.divider()

# --- 1. Identificação ---
st.header("1. Seus Dados")
nome_cliente = st.text_input("Seu Nome Completo", placeholder="Ex: João da Silva")
cpf_cliente = st.text_input("Seu CPF", placeholder="000.000.000-00")

# --- 2. Upload de Arquivos ---
st.header("2. Anexar Documentos")
st.info("Você pode selecionar vários arquivos de uma vez ou tirar fotos.")

arquivos = st.file_uploader(
    "Clique aqui para buscar arquivos ou tirar foto", 
    type=['pdf', 'png', 'jpg', 'jpeg'], 
    accept_multiple_files=True
)

# --- 3. Processamento (Simulação) ---
st.divider()

if st.button("📤 Enviar Documentos Agora"):
    if not nome_cliente or not arquivos:
        st.error("⚠️ Por favor, preencha seu nome e anexe pelo menos um documento.")
    else:
        # Barra de progresso para dar feedback visual ao cliente
        barra = st.progress(0)
        status = st.empty()
        
        status.write("Iniciando upload seguro...")
        time.sleep(1)
        
        # Simulação do processamento de cada arquivo
        for i, arquivo in enumerate(arquivos):
            # AQUI ENTRARIA O CÓDIGO DO GOOGLE DRIVE
            # O sistema criaria a pasta: "IRPF 2026 / Nome do Cliente"
            # E salvaria: arquivo.name
            
            progresso = int((i + 1) / len(arquivos) * 100)
            barra.progress(progresso)
            status.write(f"Enviando: {arquivo.name}...")
            time.sleep(0.5) # Simula tempo de envio
            
        barra.progress(100)
        status.success(f"✅ Sucesso! {len(arquivos)} documentos enviados para a contabilidade.")
        st.balloons()
        
        st.write(f"Obrigado, **{nome_cliente}**. Recebemos seus arquivos e já vamos iniciar a análise.")
