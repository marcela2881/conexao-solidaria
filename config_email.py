# config_email.py
"""
Configurações de Email para o Sistema Vôlei Beneficente

INSTRUÇÕES PARA CONFIGURAR O EMAIL:

1. Gmail (Recomendado):
   - Vá em "Gerenciar sua Conta do Google"
   - Segurança -> Verificação em duas etapas (ative se não estiver)
   - Senhas de app -> Selecione "Mail" -> Gerar
   - Use a senha gerada (16 caracteres) no campo 'password'

2. Outlook/Hotmail:
   - smtp_server: 'smtp-mail.outlook.com'
   - port: 587

3. Outros provedores:
   - Consulte a documentação do seu provedor de email
"""

EMAIL_CONFIG = {
    # CONFIGURAÇÕES BÁSICAS
    'smtp_server': 'smtp.gmail.com',  # Gmail
    'port': 587,                      # Porta padrão para TLS
    'email': 'seu_email@gmail.com',   # SEU EMAIL AQUI
    'password': 'sua_senha_app_aqui', # SENHA DE APP AQUI (não a senha normal!)
    
    # CONFIGURAÇÕES AVANÇADAS
    'timeout': 60,
    'use_tls': True,
    
    # TEMPLATE DO EMAIL
    'remetente_nome': 'Conexão Solidária',
    'assunto_padrao': '🎫 Seu Ingresso - I Torneio Beneficente'
}

# Para usar em app.py, importe assim:
# from config_email import EMAIL_CONFIG