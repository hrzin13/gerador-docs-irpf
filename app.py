import streamlit as st
from datetime import datetime
import urllib.parse

# --- Configuração da página ---
st.set_page_config(page_title="Solicitação Doc. IRPF", page_icon="📄")

st.title("📄 Gerador de Solicitação IRPF")
st.write("Selecione os perfis do cliente para gerar a lista de documentos.")

# --- Entradas de Dados ---
nome_cliente = st.text_input("Nome do Cliente", "Prezado(a) Cliente")

st.header("Perfil do Cliente")
col1, col2 = st.columns(2)

with col1:
    tem_salario = st.checkbox("Trabalho Assalariado (CLT)", value=True)
    tem_dependentes = st.checkbox("Possui Dependentes")
    paga_aluguel = st.checkbox("Mora de Aluguel")

with col2:
    gastos_saude = st.checkbox("Gastos com Saúde")
    gastos_educacao = st.checkbox("Gastos com Educação")
    investimentos = st.checkbox("Investimentos/Bancos")

# --- Lógica de Construção do Texto ---
def gerar_texto():
    ano_atual = datetime.now().year
    
    texto = f"Olá, *{nome_cliente}*! Tudo bem?\n\n"
    texto += f"Chegou a hora de prepararmos sua declaração do Imposto de Renda {ano_atual}.\n"
    texto += "Para garantir o melhor resultado possível e evitar a malha fina, por favor, me envie os seguintes documentos:\n\n"
    
    texto += "*1. BÁSICOS*\n"
    texto += "- [ ] Última declaração de IR (se tiver)\n"
    texto += "- [ ] Comprovante de endereço atualizado\n"
    texto += "- [ ] Título de eleitor\n\n"

    if tem_salario:
        texto += "*2. RENDA*\n"
        texto += "- [ ] Informe de Rendimentos da(s) empresa(s) onde trabalhou\n\n"

    if investimentos:
        texto += "*3. BANCOS E APLICAÇÕES*\n"
        texto += "- [ ] Informe de Rendimentos Financeiros (Bancos e Corretoras - baixar no app do banco)\n\n"

    # Se tiver despesas dedutíveis
    if gastos_saude or gastos_educacao or paga_aluguel or tem_dependentes:
        texto += "*4. DESPESAS E DEDUÇÕES*\n"
        
        if gastos_saude:
            texto += "- [ ] Recibos médicos/dentistas/psicólogos (com CPF do profissional)\n"
            texto += "- [ ] Extrato anual do Plano de Saúde para IR\n"
            
        if gastos_educacao:
            texto += "- [ ] Comprovantes de mensalidade escolar/faculdade (Nome e CNPJ da instituição)\n"
            
        if paga_aluguel:
            texto += "- [ ] Contrato de aluguel e comprovantes de pagamento (com CPF do proprietário)\n"
            
        if tem_dependentes:
            texto += "- [ ] CPF e data de nascimento de todos os dependentes\n"
            texto += "- [ ] Despesas médicas/escolares dos dependentes\n"

    texto += "\nQualquer dúvida sobre os documentos, é só me chamar. Fico no aguardo! 🚀"
    return texto

# --- Exibição do Resultado ---
st.divider()
st.subheader("Sua Mensagem:")

mensagem_final = gerar_texto()

# Mostra o texto na tela para você conferir se quiser
st.text_area("Pré-visualização do texto:", value=mensagem_final, height=250)

# Cria o link mágico do WhatsApp
texto_codificado = urllib.parse.quote(mensagem_final)
link_whatsapp = f"https://wa.me/?text={texto_codificado}"

# Botão de Ação
st.markdown("###") # Espaço vazio
st.link_button("📲 Enviar direto no WhatsApp", link_whatsapp, type="primary")
