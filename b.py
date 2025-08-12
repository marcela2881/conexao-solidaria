from flask import Flask, render_template_string, request, redirect, url_for, Response
import sqlite3
import os
import qrcode
import uuid
from datetime import datetime
import io
import base64
import csv

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = 'conexao_solidaria_2025'

def init_db():
    conn = sqlite3.connect('conexao_solidaria.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ingressos (
        id TEXT PRIMARY KEY,
        nome TEXT NOT NULL,
        email TEXT NOT NULL,
        telefone TEXT,
        idade INTEGER,
        categoria TEXT NOT NULL,
        preco REAL NOT NULL,
        status TEXT DEFAULT 'pendente',
        data_compra TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        usado BOOLEAN DEFAULT 0,
        data_uso TIMESTAMP,
        qr_code TEXT
    )''')
    conn.commit()
    conn.close()

def gerar_qr_code_pix(valor, chave_pix="conexaosolidariamao@gmail.com", nome_beneficiario="VANESSA CARVALHO RAMOS", cidade="MANAUS"):
    payload = f"00020126580014br.gov.bcb.pix0136{chave_pix}520400005303986540{valor:.2f}5802BR5925{nome_beneficiario}6009{cidade}6304ABCD"
    return payload

@app.route('/')
def index():
    return render_template_string(INDEX_TEMPLATE_COM_FOTOS)

@app.route('/processar_carrinho_simples', methods=['POST'])
def processar_carrinho_simples():
    print("🔥 PROCESSANDO CARRINHO!")
    
    total_pessoas = int(request.form['total_pessoas'])
    print(f"👥 Total de pessoas: {total_pessoas}")
    
    carrinho = []
    preco_total = 0
    
    for i in range(1, total_pessoas + 1):
        nome_key = f'nome_{i}'
        if nome_key in request.form and request.form[nome_key]:
            nome = request.form[f'nome_{i}']
            email = request.form[f'email_{i}']
            telefone = request.form.get(f'telefone_{i}', '')
            idade = int(request.form[f'idade_{i}'])
            categoria = request.form[f'categoria_{i}']
            
            # Calcular preço individual
            if idade <= 5:
                preco = 0
                categoria_nome = "👶 Criança (0-5 anos) - GRATUITO"
            elif idade <= 12:
                preco = 25
                if categoria == 'crianca_almoco':
                    categoria_nome = "🧒 Almoço Criança (6-12 anos) + Day Use"
                else:
                    categoria_nome = "🧒 Criança (6-12 anos) + Day Use"
            else:
                if categoria == 'volei_iniciante':
                    preco = 50
                    categoria_nome = "🏐 Vôlei Iniciante + Almoço + Day Use"
                elif categoria == 'volei_intermediario':
                    preco = 50
                    categoria_nome = "🏆 Vôlei Intermediário + Almoço + Day Use"
                elif categoria == 'almoco_day_use':
                    preco = 40
                    categoria_nome = "🍽️ Almoço Adulto + Day Use"
                elif categoria == 'crianca_almoco':
                    preco = 25
                    categoria_nome = "🧒 Almoço Criança + Day Use"
                else:
                    preco = 40
                    categoria_nome = "🍽️ Almoço + Day Use"
            
            carrinho.append({
                'nome': nome,
                'email': email,
                'telefone': telefone,
                'idade': idade,
                'categoria': categoria_nome,
                'preco': preco
            })
            
            preco_total += preco
            print(f"👤 Pessoa {i}: {nome} - R$ {preco}")
    
    print(f"💰 Preço total: R$ {preco_total}")
    
    # Gerar ID do pedido
    pedido_id = str(uuid.uuid4())[:8].upper()
    
    # Salvar no banco
    try:
        conn = sqlite3.connect('conexao_solidaria.db')
        c = conn.cursor()
        
        # Salvar cada pessoa individualmente
        for pessoa in carrinho:
            ingresso_id = str(uuid.uuid4())[:8].upper()
            c.execute('''
                INSERT INTO ingressos (id, nome, email, telefone, idade, categoria, preco, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ingresso_id, pessoa['nome'], pessoa['email'], pessoa['telefone'], 
                  pessoa['idade'], pessoa['categoria'], pessoa['preco'], 'pendente'))
        
        # Criar registro do pedido consolidado
        categoria_resumo = f"Pedido com {len(carrinho)} ingressos"
        c.execute('''
            INSERT INTO ingressos (id, nome, email, telefone, idade, categoria, preco, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (pedido_id, 'PEDIDO CONSOLIDADO', carrinho[0]['email'], '', 0, 
              categoria_resumo, preco_total, 'pedido_consolidado'))
        
        conn.commit()
        conn.close()
        print("✅ Salvo no banco!")
        
    except Exception as e:
        print(f"❌ Erro no banco: {e}")
        return f"Erro no banco: {e}"
    
    print(f"🔄 Redirecionando para /pagamento_simples/{pedido_id}")
    return redirect(url_for('pagamento_simples', ingresso_id=pedido_id))

@app.route('/pagamento_simples/<ingresso_id>')
def pagamento_simples(ingresso_id):
    print(f"💳 CHEGOU NA PÁGINA DE PAGAMENTO! ID: {ingresso_id}")
    
    # Buscar no banco
    conn = sqlite3.connect('conexao_solidaria.db')
    c = conn.cursor()
    c.execute('SELECT * FROM ingressos WHERE id = ?', (ingresso_id,))
    ingresso = c.fetchone()
    conn.close()
    
    if not ingresso:
        print("❌ Ingresso não encontrado!")
        return "Ingresso não encontrado!"
    
    print(f"📋 Ingresso encontrado: {ingresso}")
    
    # ✅ USAR SUA IMAGEM QR CODE (.jpg)
    qr_code_url = "/static/qrcoud.jpg"
    
    return render_template_string(PAGAMENTO_TEMPLATE, ingresso=ingresso, qr_code_url=qr_code_url)

@app.route('/gerar_ingresso/<ingresso_id>')
def gerar_ingresso(ingresso_id):
    conn = sqlite3.connect('conexao_solidaria.db')
    c = conn.cursor()
    c.execute('SELECT * FROM ingressos WHERE id = ?', (ingresso_id,))
    ingresso = c.fetchone()
    conn.close()
    
    if not ingresso:
        return "Ingresso não encontrado!"
    
    qr_data = f"{ingresso[0]}|{ingresso[1]}|{ingresso[2]}"
    qr = qrcode.QRCode(version=1, box_size=8, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#9333ea", back_color="white")
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    qr_code_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    return render_template_string(TEMPLATE_INGRESSO, ingresso=ingresso, qr_code=qr_code_base64)

# ==================== ROTAS ADMINISTRATIVAS ====================
ADMIN_PASSWORD = "conexao2025"

ADMIN_LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Admin - Conexão Solidária</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: Arial, sans-serif; 
            background: linear-gradient(135deg, #9333ea, #e879f9);
            min-height: 100vh; 
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 25px 50px rgba(147, 51, 234, 0.4);
            text-align: center;
            max-width: 400px;
            width: 100%;
        }
        .login-container h1 {
            color: #9333ea;
            margin-bottom: 30px;
            font-size: 2em;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group input {
            width: 100%;
            padding: 15px;
            border: 2px solid #e2e8f0;
            border-radius: 10px;
            font-size: 16px;
        }
        .btn {
            background: linear-gradient(135deg, #9333ea, #7c3aed);
            color: white;
            padding: 15px 30px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            cursor: pointer;
            width: 100%;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>🔐 Painel Admin</h1>
        <form method="POST" action="/admin/dashboard">
            <div class="form-group">
                <input type="password" name="senha" placeholder="Digite a senha de admin" required>
            </div>
            <button type="submit" class="btn">🚀 Entrar</button>
        </form>
    </div>
</body>
</html>
'''

@app.route('/admin')
def admin_login():
    return render_template_string(ADMIN_LOGIN_TEMPLATE)

@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    # Verificar senha
    if request.method == 'POST':
        senha = request.form.get('senha')
        if senha != ADMIN_PASSWORD:
            return "❌ Senha incorreta!"
    elif request.method == 'GET':
        senha = request.args.get('senha')
        if senha != ADMIN_PASSWORD:
            return redirect('/admin')
    
    # Buscar dados do banco
    conn = sqlite3.connect('conexao_solidaria.db')
    c = conn.cursor()
    
    c.execute('''SELECT * FROM ingressos 
                 WHERE status != "pedido_consolidado"
                 ORDER BY data_compra DESC''')
    inscricoes = c.fetchall()
    
    c.execute('SELECT COUNT(*) FROM ingressos WHERE status != "pedido_consolidado"')
    total_inscricoes = c.fetchone()[0]
    
    c.execute('SELECT SUM(preco) FROM ingressos WHERE status != "pedido_consolidado"')
    receita_total = c.fetchone()[0] or 0
    
    c.execute('SELECT COUNT(*) FROM ingressos WHERE status = "confirmado"')
    pagamentos_confirmados = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM ingressos WHERE usado = 1')
    ingressos_utilizados = c.fetchone()[0]
    
    conn.close()
    
    return render_template_string(ADMIN_DASHBOARD_TEMPLATE, 
                                 inscricoes=inscricoes,
                                 total_inscricoes=total_inscricoes,
                                 receita_total=receita_total,
                                 pagamentos_confirmados=pagamentos_confirmados,
                                 ingressos_utilizados=ingressos_utilizados)

@app.route('/admin/confirmar_pagamento/<ingresso_id>')
def confirmar_pagamento(ingresso_id):
    conn = sqlite3.connect('conexao_solidaria.db')
    c = conn.cursor()
    c.execute('UPDATE ingressos SET status = "confirmado" WHERE id = ?', (ingresso_id,))
    conn.commit()
    conn.close()
    return redirect(f'/admin/dashboard?senha={ADMIN_PASSWORD}')

@app.route('/admin/marcar_usado/<ingresso_id>')
def marcar_usado(ingresso_id):
    conn = sqlite3.connect('conexao_solidaria.db')
    c = conn.cursor()
    c.execute('UPDATE ingressos SET usado = 1, data_uso = CURRENT_TIMESTAMP WHERE id = ?', (ingresso_id,))
    conn.commit()
    conn.close()
    return redirect(f'/admin/dashboard?senha={ADMIN_PASSWORD}')

@app.route('/admin/exportar_excel')
def exportar_excel():
    conn = sqlite3.connect('conexao_solidaria.db')
    c = conn.cursor()
    c.execute('SELECT * FROM ingressos WHERE status != "pedido_consolidado" ORDER BY data_compra DESC')
    dados = c.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Nome', 'Email', 'Telefone', 'Idade', 'Categoria', 'Preço', 'Status', 'Data Compra', 'Usado', 'Data Uso', 'QR Code'])
    
    for linha in dados:
        writer.writerow(linha)
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=inscricoes_conexao_solidaria.csv"}
    )

ADMIN_DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Dashboard Admin - Conexão Solidária</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: Arial, sans-serif; 
            background: #f1f5f9;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            background: linear-gradient(135deg, #9333ea, #7c3aed);
            color: white;
            padding: 30px;
            border-radius: 20px;
            text-align: center;
            margin-bottom: 30px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border: 3px solid #e2e8f0;
        }
        .stat-number {
            font-size: 2.5em;
            font-weight: bold;
            color: #9333ea;
            margin-bottom: 10px;
        }
        .actions-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .action-btn {
            padding: 20px;
            border: none;
            border-radius: 15px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            text-decoration: none;
            display: block;
            text-align: center;
            transition: transform 0.2s;
        }
        .action-btn:hover {
            transform: translateY(-2px);
        }
        .btn-export { background: linear-gradient(135deg, #0ea5e9, #0284c7); color: white; }
        .btn-home { background: linear-gradient(135deg, #6b7280, #4b5563); color: white; }
        
        .table-container {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            min-width: 900px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
            vertical-align: middle;
        }
        th {
            background: #f8fafc;
            font-weight: bold;
            color: #374151;
            font-size: 14px;
        }
        td {
            font-size: 13px;
        }
        .status-pendente { 
            background: #fef3c7; 
            color: #92400e; 
            padding: 4px 8px; 
            border-radius: 15px; 
            font-size: 11px;
            font-weight: bold;
        }
        .status-confirmado { 
            background: #dcfce7; 
            color: #166534; 
            padding: 4px 8px; 
            border-radius: 15px; 
            font-size: 11px;
            font-weight: bold;
        }
        .btn {
            padding: 6px 12px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            margin: 1px;
            font-size: 11px;
            font-weight: bold;
            text-align: center;
            min-width: 70px;
        }
        .btn-confirmar { background: #22c55e; color: white; }
        .btn-usar { background: #f59e0b; color: white; }
        .btn-ingresso { 
            background: linear-gradient(135deg, #9333ea, #7c3aed); 
            color: white; 
            font-size: 12px;
            padding: 8px 12px;
        }
        .btn-ingresso:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(147, 51, 234, 0.3);
        }
        .usado { background: #f3f4f6; opacity: 0.7; }
        
        .acoes-col {
            min-width: 180px;
        }
        
        .nome-col {
            max-width: 150px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .categoria-col {
            max-width: 200px;
            font-size: 11px;
        }
        
        .email-col {
            max-width: 180px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 11px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Dashboard Administrativo</h1>
            <p>I Torneio Beneficente - Conexão Solidária 2025</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{{ total_inscricoes }}</div>
                <div>👥 Total Inscrições</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">R$ {{ "%.2f"|format(receita_total) }}</div>
                <div>💰 Receita Total</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ pagamentos_confirmados }}</div>
                <div>✅ Pagamentos Confirmados</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ ingressos_utilizados }}</div>
                <div>🎫 Ingressos Utilizados</div>
            </div>
        </div>
        
        <div class="actions-grid">
            <a href="/admin/exportar_excel?senha=conexao2025" class="action-btn btn-export">
                📥 Exportar Excel/CSV
            </a>
            <a href="/" class="action-btn btn-home">
                🏠 Voltar ao Site
            </a>
        </div>
        
        <div class="table-container">
            <h2 style="margin-bottom: 20px; color: #374151;">📋 Lista de Inscrições</h2>
            
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Nome</th>
                        <th>Email</th>
                        <th>Telefone</th>
                        <th>Categoria</th>
                        <th>Preço</th>
                        <th>Status</th>
                        <th>Data</th>
                        <th class="acoes-col">Ações</th>
                    </tr>
                </thead>
                <tbody>
                    {% for inscricao in inscricoes %}
                    <tr {% if inscricao[9] %}class="usado"{% endif %}>
                        <td><strong>{{ inscricao[0] }}</strong></td>
                        <td class="nome-col" title="{{ inscricao[1] }}">{{ inscricao[1] }}</td>
                        <td class="email-col" title="{{ inscricao[2] }}">{{ inscricao[2] }}</td>
                        <td>{{ inscricao[3] or '-' }}</td>
                        <td class="categoria-col">{{ inscricao[5] }}</td>
                        <td>
                            {% if inscricao[6] == 0 %}
                                <span style="color: #22c55e; font-weight: bold;">GRATUITO</span>
                            {% else %}
                                <strong>R$ {{ "%.2f"|format(inscricao[6]) }}</strong>
                            {% endif %}
                        </td>
                        <td>
                            {% if inscricao[7] == 'confirmado' %}
                                <span class="status-confirmado">✅ Confirmado</span>
                            {% else %}
                                <span class="status-pendente">⏳ Pendente</span>
                            {% endif %}
                            {% if inscricao[9] %}
                                <br><span style="color: #dc2626; font-weight: bold; font-size: 10px;">🎫 USADO</span>
                            {% endif %}
                        </td>
                        <td style="font-size: 11px;">{{ inscricao[8][:10] if inscricao[8] else '-' }}</td>
                        <td class="acoes-col">
                            <a href="/gerar_ingresso/{{ inscricao[0] }}" 
                               class="btn btn-ingresso" 
                               target="_blank" 
                               title="Gerar ingresso visual para {{ inscricao[1] }}">
                                🎫 Gerar Ingresso
                            </a>
                            <br>
                            
                            {% if inscricao[7] != 'confirmado' and inscricao[6] > 0 %}
                                <a href="/admin/confirmar_pagamento/{{ inscricao[0] }}" 
                                   class="btn btn-confirmar"
                                   title="Confirmar pagamento">✅ Confirmar</a>
                            {% endif %}
                            
                            {% if not inscricao[9] and inscricao[7] == 'confirmado' %}
                                <a href="/admin/marcar_usado/{{ inscricao[0] }}" 
                                   class="btn btn-usar"
                                   title="Marcar como usado">🎫 Usar</a>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            
            {% if not inscricoes %}
            <div style="text-align: center; padding: 40px; color: #6b7280;">
                <h3>😔 Nenhuma inscrição encontrada</h3>
                <p>As inscrições aparecerão aqui quando as pessoas se cadastrarem.</p>
            </div>
            {% endif %}
        </div>
    </div>
</body>
</html>
'''

# TEMPLATES
INDEX_TEMPLATE_COM_FOTOS = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>I Torneio Beneficente - Conexão Solidária</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #9333ea, #e879f9, #f3e8ff);
            min-height: 100vh; 
            padding: 20px;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 30px;
            padding: 0;
            box-shadow: 0 25px 50px rgba(147, 51, 234, 0.4);
            border: 3px solid #9333ea;
            backdrop-filter: blur(10px);
            overflow: hidden;
        }
        
        .header {
            text-align: center;
            padding: 40px;
            background: linear-gradient(135deg, #9333ea, #7c3aed, #a855f7);
            color: white;
            position: relative;
        }
        
        .header h1 { 
            font-size: 2.2em; 
            margin-bottom: 15px; 
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            font-weight: bold;
        }
        
        .header h2 { 
            font-size: 1.3em; 
            margin-bottom: 20px; 
            opacity: 0.95;
        }
        
        .form-section {
            padding: 40px;
            background: white;
        }
        
        .section-title {
            color: #9333ea;
            text-align: center;
            margin-bottom: 40px;
            font-size: 2.5em;
            font-weight: bold;
        }
        
        .pessoa-card {
            background: linear-gradient(135deg, #f8fafc, #f1f5f9);
            padding: 30px;
            margin: 25px 0;
            border-radius: 20px;
            border: 3px solid #e2e8f0;
            position: relative;
        }
        
        .pessoa-title {
            color: #9333ea;
            font-size: 1.8em;
            margin-bottom: 20px;
            font-weight: bold;
        }
        
        .form-group { 
            margin-bottom: 25px; 
        }
        
        .form-group label {
            display: block;
            margin-bottom: 10px;
            font-weight: bold;
            color: #374151;
            font-size: 1.1em;
        }
        
        .form-group input, .form-group select {
            width: 100%;
            padding: 15px;
            border: 3px solid #e2e8f0;
            border-radius: 12px;
            font-size: 16px;
            background: #f8fafc;
        }
        
        .preco-individual {
            background: linear-gradient(135deg, #ddd6fe, #c4b5fd);
            padding: 15px;
            border-radius: 12px;
            margin-top: 15px;
            text-align: center;
            font-weight: bold;
            color: #581c87;
            font-size: 1.1em;
            border: 2px solid #9333ea;
        }
        
        .preco-individual.gratuito {
            background: linear-gradient(135deg, #dcfce7, #bbf7d0);
            color: #14532d;
            border-color: #22c55e;
        }
        
        .add-btn {
            background: linear-gradient(135deg, #22c55e, #16a34a);
            color: white;
            padding: 18px 35px;
            border: none;
            border-radius: 20px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            margin: 15px;
        }
        
        .remove-btn {
            background: #dc2626;
            color: white;
            padding: 8px 15px;
            border: none;
            border-radius: 20px;
            font-size: 12px;
            cursor: pointer;
            position: absolute;
            top: 15px;
            right: 15px;
            font-weight: bold;
        }
        
        .total-box {
            background: linear-gradient(135deg, #9333ea, #7c3aed);
            color: white;
            padding: 30px;
            border-radius: 20px;
            text-align: center;
            margin: 30px 0;
            font-size: 1.8em;
            font-weight: bold;
        }
        
        .submit-btn {
            background: linear-gradient(135deg, #9333ea, #7c3aed);
            color: white;
            padding: 20px 40px;
            border: none;
            border-radius: 20px;
            font-size: 20px;
            font-weight: bold;
            cursor: pointer;
            width: 100%;
        }
        
        .projeto-section {
            background: linear-gradient(135deg, #f8fafc, #f1f5f9);
            padding: 30px;
            text-align: center;
            border-top: 3px solid #e2e8f0;
        }
        
        .projeto-title {
            color: #9333ea;
            font-size: 1.8em;
            margin-bottom: 20px;
            font-weight: bold;
        }
        
        .fotos-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin: 25px 0;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
        }
        
        .foto-real {
            position: relative;
            border-radius: 12px;
            overflow: hidden;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(147, 51, 234, 0.2);
            border: 3px solid #9333ea;
        }
        
        .foto-real:hover {
            transform: scale(1.05);
            box-shadow: 0 8px 25px rgba(147, 51, 234, 0.4);
        }
        
        .foto-real img {
            width: 100%;
            height: 120px;
            object-fit: cover;
            display: block;
        }
        
        .foto-legenda {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            background: linear-gradient(transparent, rgba(147, 51, 234, 0.95));
            color: white;
            padding: 12px 8px 8px 8px;
            font-size: 0.9em;
            text-align: center;
            font-weight: bold;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
        }
        
        .projeto-texto {
            background: white;
            padding: 20px;
            border-radius: 15px;
            margin: 20px 0;
            border: 2px solid #9333ea;
            font-size: 1em;
            line-height: 1.6;
            color: #374151;
            text-align: left;
        }
        
        @media (max-width: 768px) {
            .fotos-grid { grid-template-columns: repeat(2, 1fr); }
            .foto-real img { height: 100px; }
            .foto-legenda { font-size: 0.8em; }
            .header h1 { font-size: 1.8em; }
            .header h2 { font-size: 1.1em; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏐 I TORNEIO BENEFICENTE</h1>
            <h2>🏆 CONEXÃO SOLIDÁRIA 2025 🏆</h2>
            <div class="subtitle">Esporte, Solidariedade e Diversão em um só lugar!</div>
        </div>

        <div class="form-section">
            <h3 class="section-title">🏐 Faça sua Inscrição</h3>
            
            <form method="POST" action="/processar_carrinho_simples">
                <div id="pessoas-container">
                    <div class="pessoa-card" id="pessoa-1">
                        <h3 class="pessoa-title">👤 Primeira Pessoa</h3>
                        
                        <div class="form-group">
                            <label>👤 Nome Completo:</label>
                            <input type="text" name="nome_1" required>
                        </div>
                        
                        <div class="form-group">
                            <label>📧 E-mail:</label>
                            <input type="email" name="email_1" required>
                        </div>
                        
                        <div class="form-group">
                            <label>📱 Telefone (opcional):</label>
                            <input type="tel" name="telefone_1" placeholder="(11) 99999-9999">
                        </div>
                        
                        <div class="form-group">
                            <label>🎂 Idade:</label>
                            <input type="number" name="idade_1" min="1" max="100" required onchange="calcularPreco(1)">
                        </div>
                        
                        <div class="form-group">
                            <label>🏷️ Categoria:</label>
                            <select name="categoria_1" required onchange="calcularPreco(1)">
                                <option value="">Selecione sua categoria...</option>
                                <option value="volei_iniciante">🏐 Vôlei Iniciante + Almoço + Day Use (R$ 50,00)</option>
                                <option value="volei_intermediario">🏆 Vôlei Intermediário + Almoço + Day Use (R$ 50,00)</option>
                                <option value="almoco_day_use">🍽️ Almoço Adulto + Day Use (R$ 40,00)</option>
                                <option value="crianca_almoco">🧒 Almoço Criança (6-12 anos) + Day Use (R$ 25,00)</option>
                            </select>
                        </div>
                        
                        <div class="preco-individual" id="preco-1">
                            💰 Selecione idade e categoria para ver o preço
                        </div>
                    </div>
                </div>
                
                <div style="text-align: center;">
                    <button type="button" class="add-btn" onclick="adicionarPessoa()">
                        ➕ Adicionar Outra Pessoa
                    </button>
                </div>
                
                <div class="total-box" id="total-geral">
                    🧮 Total Geral: R$ 0,00
                </div>
                
                <input type="hidden" name="total_pessoas" id="total_pessoas" value="1">
                <button type="submit" class="submit-btn">🎫 Continuar</button>
            </form>
        </div>

        <div class="projeto-section">
            <h3 class="projeto-title">📸 Galeria do Projeto</h3>
            
            <div class="fotos-grid">
                <div class="foto-real">
                    <img src="/static/1.png.jpg" alt="Confraternização dos voluntários">
                    <div class="foto-legenda">🤝 Confraternização Voluntários</div>
                </div>
                <div class="foto-real">
                    <img src="/static/2.png.jpg" alt="Visita ao Abrigo Infantil Monte Salem">
                    <div class="foto-legenda">🏠 Abrigo Infantil Monte Salem</div>
                </div>
                <div class="foto-real">
                    <img src="/static/3.png.jpg" alt="Cinema Kids para as crianças">
                    <div class="foto-legenda">🎬 Cinema Kids</div>
                </div>
                <div class="foto-real">
                    <img src="/static/4.png.jpg" alt="Distribuição de comida para moradores de rua">
                    <div class="foto-legenda">🍽️ Distribuição Comidas Moradores de Rua</div>
                </div>
                <div class="foto-real">
                    <img src="/static/5.png.jpg" alt="Ação especial de Natal">
                    <div class="foto-legenda">🎄 Ação de Natal</div>
                </div>
                <div class="foto-real">
                    <img src="/static/6.png.jpg" alt="Ação solidária no hospital">
                    <div class="foto-legenda">🏥 Ação Hospital</div>
                </div>
            </div>
            
            <div class="projeto-texto">
                <strong>🤝 O Conexão Solidária</strong><br><br>
                O Conexão Solidária é um projeto voluntário que nasceu do desejo de transformar realidades com pequenos gestos de amor.
                <br><br>
                <strong>🏐 O Torneio</strong><br><br>
                Para continuar espalhando essa corrente do bem, criamos o Torneio Conexão Solidária, um evento beneficente que une esporte e solidariedade.
            </div>
        </div>
    </div>

    <script>
        let contadorPessoas = 1;
        
        function calcularPrecoIndividual(idade, categoria) {
            if (idade <= 5) return 0;
            if (idade <= 12) return 25;
            
            if (categoria === 'volei_iniciante' || categoria === 'volei_intermediario') {
                return 50;
            } else if (categoria === 'almoco_day_use') {
                return 40;
            } else if (categoria === 'crianca_almoco') {
                return 25;
            }
            return 0;
        }
        
        function calcularPreco(numeroPessoa) {
            const idade = document.querySelector("input[name='idade_" + numeroPessoa + "']").value;
            const categoria = document.querySelector("select[name='categoria_" + numeroPessoa + "']").value;
            const precoDiv = document.getElementById("preco-" + numeroPessoa);
            
            if (idade && categoria) {
                const preco = calcularPrecoIndividual(parseInt(idade), categoria);
                
                if (preco === 0) {
                    precoDiv.innerHTML = '🎁 GRATUITO (0-5 anos)';
                    precoDiv.className = 'preco-individual gratuito';
                } else {
                    precoDiv.innerHTML = '💰 R$ ' + preco.toFixed(2);
                    precoDiv.className = 'preco-individual';
                }
            } else {
                precoDiv.innerHTML = '💰 Selecione idade e categoria para ver o preço';
                precoDiv.className = 'preco-individual';
            }
            
            calcularTotal();
        }
        
        function calcularTotal() {
            let total = 0;
            for (let i = 1; i <= contadorPessoas; i++) {
                const pessoaDiv = document.getElementById("pessoa-" + i);
                if (pessoaDiv) {
                    const idade = document.querySelector("input[name='idade_" + i + "']");
                    const categoria = document.querySelector("select[name='categoria_" + i + "']");
                    
                    if (idade && categoria && idade.value && categoria.value) {
                        total += calcularPrecoIndividual(parseInt(idade.value), categoria.value);
                    }
                }
            }
            
            document.getElementById('total-geral').innerHTML = '🧮 Total Geral: R$ ' + total.toFixed(2);
        }
        
        function adicionarPessoa() {
            contadorPessoas++;
            document.getElementById('total_pessoas').value = contadorPessoas;
            
            const novaPessoa = '<div class="pessoa-card" id="pessoa-' + contadorPessoas + '">' +
                '<button type="button" class="remove-btn" onclick="removerPessoa(' + contadorPessoas + ')">✕ Remover</button>' +
                '<h3 class="pessoa-title">👤 Pessoa ' + contadorPessoas + '</h3>' +
                '<div class="form-group">' +
                '<label>👤 Nome Completo:</label>' +
                '<input type="text" name="nome_' + contadorPessoas + '" required>' +
                '</div>' +
                '<div class="form-group">' +
                '<label>📧 E-mail:</label>' +
                '<input type="email" name="email_' + contadorPessoas + '" required>' +
                '</div>' +
                '<div class="form-group">' +
                '<label>📱 Telefone (opcional):</label>' +
                '<input type="tel" name="telefone_' + contadorPessoas + '" placeholder="(11) 99999-9999">' +
                '</div>' +
                '<div class="form-group">' +
                '<label>🎂 Idade:</label>' +
                '<input type="number" name="idade_' + contadorPessoas + '" min="1" max="100" required onchange="calcularPreco(' + contadorPessoas + ')">' +
                '</div>' +
                '<div class="form-group">' +
                '<label>🏷️ Categoria:</label>' +
                '<select name="categoria_' + contadorPessoas + '" required onchange="calcularPreco(' + contadorPessoas + ')">' +
                '<option value="">Selecione sua categoria...</option>' +
                '<option value="volei_iniciante">🏐 Vôlei Iniciante + Almoço + Day Use (R$ 50,00)</option>' +
                '<option value="volei_intermediario">🏆 Vôlei Intermediário + Almoço + Day Use (R$ 50,00)</option>' +
                '<option value="almoco_day_use">🍽️ Almoço Adulto + Day Use (R$ 40,00)</option>' +
                '<option value="crianca_almoco">🧒 Almoço Criança (6-12 anos) + Day Use (R$ 25,00)</option>' +
                '</select>' +
                '</div>' +
                '<div class="preco-individual" id="preco-' + contadorPessoas + '">' +
                '💰 Selecione idade e categoria para ver o preço' +
                '</div>' +
                '</div>';
            
            document.getElementById('pessoas-container').innerHTML += novaPessoa;
        }
        
        function removerPessoa(numero) {
            const pessoaDiv = document.getElementById("pessoa-" + numero);
            if (pessoaDiv) {
                pessoaDiv.remove();
                calcularTotal();
            }
        }
    </script>
</body>
</html>
'''

PAGAMENTO_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Pagamento PIX - Conexão Solidária</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: Arial, sans-serif; 
            background: linear-gradient(135deg, #9333ea, #e879f9);
            min-height: 100vh; 
            padding: 20px;
        }
        .container {
            max-width: 700px;
            margin: 0 auto;
            background: white;
            border-radius: 25px;
            padding: 30px;
            box-shadow: 0 25px 50px rgba(147, 51, 234, 0.4);
            border: 3px solid #9333ea;
        }
        .header {
            background: linear-gradient(135deg, #9333ea, #7c3aed);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 15px;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 2em;
            margin-bottom: 10px;
            font-weight: bold;
        }
        .info-box {
            background: #f8fafc;
            padding: 25px;
            border-radius: 15px;
            border: 2px solid #e2e8f0;
            margin-bottom: 20px;
        }
        .info-box h3 {
            color: #9333ea;
            margin-bottom: 20px;
            font-size: 1.5em;
        }
        .pix-section {
            text-align: center;
            margin: 30px 0;
        }
        .valor-destaque {
            background: linear-gradient(135deg, #9333ea, #7c3aed);
            color: white;
            padding: 20px;
            border-radius: 15px;
            font-size: 2em;
            font-weight: bold;
            margin: 20px 0;
        }
        .qr-container {
            background: white;
            padding: 25px;
            border-radius: 20px;
            display: inline-block;
            margin: 25px 0;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            border: 3px solid #9333ea;
        }
        .qr-container img {
            max-width: 300px;
            width: 100%;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(147, 51, 234, 0.2);
        }
        .whatsapp-section {
            background: linear-gradient(135deg, #dcfce7, #bbf7d0);
            border: 3px solid #22c55e;
            border-radius: 20px;
            padding: 30px;
            margin: 30px 0;
            text-align: center;
        }
        .back-btn {
            background: #6b7280;
            color: white;
            padding: 15px 30px;
            border: none;
            border-radius: 15px;
            text-decoration: none;
            display: inline-block;
            margin: 30px auto;
            font-weight: bold;
        }
        .pix-info {
            background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
            border: 3px solid #0ea5e9;
            padding: 20px;
            border-radius: 15px;
            margin: 25px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏐 Pagamento PIX</h1>
            <p>I Torneio Beneficente - Conexão Solidária 2025</p>
        </div>
        
        <div class="info-box">
            <h3>📋 Resumo do Pedido</h3>
            <p><strong>🎫 ID:</strong> {{ ingresso[0] }}</p>
            <p><strong>📧 E-mail:</strong> {{ ingresso[2] }}</p>
            <p><strong>🏷️ Detalhes:</strong> {{ ingresso[5] }}</p>
            <p><strong>💰 Valor:</strong> {% if ingresso[6] == 0 %}GRATUITO{% else %}R$ {{ "%.2f"|format(ingresso[6]) }}{% endif %}</p>
        </div>
        
        {% if ingresso[6] > 0 %}
        <div class="pix-section">
            <h2 style="color: #0369a1; font-size: 2em; margin-bottom: 20px;">🔸 Pagamento via PIX</h2>
            
            <div class="valor-destaque">
                💰 R$ {{ "%.2f"|format(ingresso[6]) }}
            </div>
            
            <div class="pix-info">
                <p style="color: #0369a1; font-weight: bold; font-size: 1.2em; margin-bottom: 10px;">📧 Chave PIX: conexaosolidariamao@gmail.com</p>
                <p style="color: #0369a1; font-weight: bold; font-size: 1.1em;">👤 Beneficiário: Vanessa Carvalho Ramos</p>
            </div>
            
            <!-- SEU QR CODE PERSONALIZADO (.jpg) -->
            <div class="qr-container">
                <h4 style="color: #9333ea; margin-bottom: 20px; font-size: 1.3em;">📱 QR Code PIX</h4>
                <img src="{{ qr_code_url }}" alt="QR Code PIX - Conexão Solidária">
                <p style="color: #6b7280; margin-top: 15px; font-weight: bold;">Escaneie com o app do seu banco</p>
            </div>
            
            <div class="whatsapp-section">
                <h4 style="color: #166534; font-size: 1.5em; margin-bottom: 20px;">📲 Após o pagamento:</h4>
                
                <p style="color: #166534; margin-bottom: 25px; font-size: 1.2em;">
                    <strong>1. Envie o comprovante via WhatsApp:</strong>
                </p>
                
                <div style="background: white; padding: 25px; border-radius: 15px; border: 3px solid #25d366; margin-bottom: 20px;">
                    <p style="color: #128c7e; font-size: 1.4em; font-weight: bold; margin-bottom: 15px;">
                        📱 (92) 99286-8443
                    </p>
                    <a href="https://wa.me/5592992868443" target="_blank" 
                       style="color: #25d366; font-size: 1.1em; text-decoration: none; font-weight: bold;">
                        👆 Clique aqui para abrir o WhatsApp
                    </a>
                </div>
                
                <p style="color: #166534; margin-bottom: 15px; font-size: 1.2em;">
                    <strong>2. Entre no grupo do seu nível:</strong>
                </p>
                
                <div style="display: flex; gap: 15px; justify-content: center; flex-wrap: wrap;">
                    <a href="https://chat.whatsapp.com/C0PvsakJsvPIKD7XKVhKMf" target="_blank" 
                       style="background: #25d366; color: white; padding: 15px 25px; border-radius: 15px; text-decoration: none; font-weight: bold; display: inline-block; min-width: 200px; text-align: center;">
                        🏐 Grupo Iniciante (Manhã)
                    </a>
                    <a href="https://chat.whatsapp.com/LSOR6KMha1uLvtmNrvzutt" target="_blank" 
                       style="background: #f59e0b; color: white; padding: 15px 25px; border-radius: 15px; text-decoration: none; font-weight: bold; display: inline-block; min-width: 200px; text-align: center;">
                        🏆 Grupo Intermediário (Tarde)
                    </a>
                </div>
            </div>
        </div>
        {% else %}
        <div style="background: linear-gradient(135deg, #f3e8ff, #e879f9); padding: 40px; text-align: center; margin: 30px;">
            <h2 style="color: #9333ea; font-size: 2.5em; margin-bottom: 20px;">🎁 Inscrição Gratuita!</h2>
            <p style="font-size: 1.3em; color: #7c3aed; margin-bottom: 25px;">
                Parabéns! Sua inscrição não tem custo.<br>
                Crianças de 0 a 5 anos têm entrada gratuita!
            </p>
            
            <div style="background: linear-gradient(135deg, #dcfce7, #bbf7d0); border: 3px solid #22c55e; border-radius: 20px; padding: 30px; margin: 30px 0; text-align: center;">
                <h4 style="color: #166534; font-size: 1.5em; margin-bottom: 20px;">📲 Entre no grupo:</h4>
                
                <div style="display: flex; gap: 15px; justify-content: center; flex-wrap: wrap;">
                    <a href="https://chat.whatsapp.com/C0PvsakJsvPIKD7XKVhKMf" target="_blank" 
                       style="background: #25d366; color: white; padding: 15px 25px; border-radius: 15px; text-decoration: none; font-weight: bold; display: inline-block; min-width: 200px; text-align: center;">
                        🏐 Grupo Iniciante (Manhã)
                    </a>
                    <a href="https://chat.whatsapp.com/LSOR6KMha1uLvtmNrvzutt" target="_blank" 
                       style="background: #f59e0b; color: white; padding: 15px 25px; border-radius: 15px; text-decoration: none; font-weight: bold; display: inline-block; min-width: 200px; text-align: center;">
                        🏆 Grupo Intermediário (Tarde)
                    </a>
                </div>
            </div>
        </div>
        {% endif %}
        
        <div style="text-align: center; padding: 30px;">
            <a href="/" class="back-btn">🔙 Voltar à Página Inicial</a>
        </div>
    </div>
</body>
</html>
'''

TEMPLATE_INGRESSO = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Ingresso - {{ ingresso[1] }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif; 
            background: #f1f5f9;
            padding: 8px;
            line-height: 1.4;
            font-size: 14px;
        }
        
        .ingresso-container {
            max-width: 420px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 8px 25px rgba(0,0,0,0.12);
            border: 2px solid #9333ea;
        }
        
        .ingresso-header {
            background: linear-gradient(135deg, #9333ea, #7c3aed);
            color: white;
            padding: 16px 12px;
            text-align: center;
        }
        
        .evento-title {
            font-size: 1.4rem;
            font-weight: 700;
            margin-bottom: 6px;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
            line-height: 1.2;
        }
        
        .evento-subtitle {
            font-size: 0.95rem;
            opacity: 0.95;
            margin-bottom: 8px;
            line-height: 1.2;
        }
        
        .evento-data {
            background: rgba(255,255,255,0.2);
            padding: 6px 12px;
            border-radius: 16px;
            display: inline-block;
            font-size: 0.8rem;
            font-weight: 600;
        }
        
        .ingresso-body {
            padding: 16px 12px;
        }
        
        .dados-participante {
            background: linear-gradient(135deg, #f8fafc, #f1f5f9);
            padding: 16px;
            border-radius: 12px;
            border: 2px solid #e2e8f0;
            margin-bottom: 16px;
        }
        
        .dados-participante h3 {
            color: #9333ea;
            font-size: 1.1rem;
            margin-bottom: 12px;
            border-bottom: 2px solid #9333ea;
            padding-bottom: 6px;
            font-weight: 700;
        }
        
        .dado-item {
            margin-bottom: 10px;
            display: flex;
            flex-direction: column;
            gap: 2px;
        }
        
        .dado-label {
            font-weight: 600;
            color: #374151;
            font-size: 0.85rem;
        }
        
        .dado-valor {
            color: #6b7280;
            font-size: 0.9rem;
            word-break: break-word;
            padding-left: 8px;
        }
        
        .preco-box {
            background: linear-gradient(135deg, #9333ea, #7c3aed);
            color: white;
            padding: 16px;
            border-radius: 12px;
            text-align: center;
            margin: 16px 0;
        }
        
        .preco-valor {
            font-size: 1.6rem;
            font-weight: 700;
            margin-bottom: 4px;
        }
        
        .preco-label {
            font-size: 0.85rem;
            opacity: 0.9;
        }
        
        .qr-section {
            text-align: center;
            background: white;
            padding: 16px;
            border-radius: 12px;
            border: 2px solid #9333ea;
            box-shadow: 0 4px 12px rgba(147, 51, 234, 0.15);
            margin-bottom: 16px;
        }
        
        .qr-section h4 {
            color: #9333ea;
            margin-bottom: 12px;
            font-size: 1rem;
            font-weight: 600;
        }
        
        .qr-code img {
            max-width: 160px;
            width: 100%;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 8px;
            background: white;
        }
        
        .ingresso-id {
            font-family: 'Courier New', monospace;
            font-size: 0.75rem;
            color: #6b7280;
            margin-top: 8px;
        }
        
        .evento-details {
            background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
            border: 2px solid #0ea5e9;
            border-radius: 12px;
            padding: 16px;
            margin: 16px 0;
        }
        
        .evento-details h4 {
            color: #0c4a6e;
            font-size: 1rem;
            margin-bottom: 12px;
            text-align: center;
            font-weight: 600;
        }
        
        .evento-details p {
            color: #0c4a6e;
            font-size: 0.85rem;
            margin-bottom: 12px;
            text-align: center;
            line-height: 1.4;
        }
        
        .detalhes-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
            margin-top: 12px;
        }
        
        .detalhe-item {
            background: white;
            padding: 10px 6px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid #0ea5e9;
        }
        
        .detalhe-emoji {
            font-size: 1.2rem;
            margin-bottom: 4px;
        }
        
        .detalhe-texto {
            color: #0c4a6e;
            font-weight: 600;
            font-size: 0.75rem;
            line-height: 1.2;
        }
        
        .grupos-whatsapp {
            background: #dcfce7; 
            border: 2px solid #22c55e; 
            border-radius: 12px; 
            padding: 14px; 
            text-align: center;
            margin: 16px 0;
        }
        
        .grupos-whatsapp h4 {
            color: #166534; 
            margin-bottom: 12px;
            font-size: 0.95rem;
            font-weight: 600;
        }
        
        .grupos-links {
            display: flex; 
            flex-direction: column;
            gap: 8px;
        }
        
        .grupo-link {
            padding: 10px 12px; 
            border-radius: 8px; 
            text-decoration: none; 
            font-weight: 600;
            font-size: 0.8rem;
            text-align: center;
            display: block;
        }
        
        .grupo-iniciante {
            background: #25d366;
            color: white;
        }
        
        .grupo-intermediario {
            background: #f59e0b;
            color: white;
        }
        
        .acoes {
            text-align: center;
            margin-top: 20px;
            padding-top: 16px;
            border-top: 2px dashed #e2e8f0;
        }
        
        .btn {
            padding: 12px 20px;
            border: none;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            margin: 6px;
            transition: transform 0.2s;
        }
        
        .btn:active {
            transform: scale(0.98);
        }
        
        .btn-print {
            background: linear-gradient(135deg, #059669, #047857);
            color: white;
        }
        
        .btn-back {
            background: #6b7280;
            color: white;
        }
        
        @media (max-width: 380px) {
            body { padding: 4px; font-size: 13px; }
            .ingresso-container { border-radius: 12px; }
            .ingresso-header { padding: 12px 8px; }
            .evento-title { font-size: 1.2rem; }
            .evento-subtitle { font-size: 0.85rem; }
            .ingresso-body { padding: 12px 8px; }
            .dados-participante { padding: 12px; }
            .qr-code img { max-width: 140px; }
            .detalhes-grid { grid-template-columns: 1fr; gap: 6px; }
            .btn { padding: 10px 16px; font-size: 0.85rem; margin: 4px; }
        }
        
        @media print {
            body { background: white; padding: 0; }
            .acoes { display: none; }
            .ingresso-container { 
                box-shadow: none; 
                border: 2px solid #9333ea;
                max-width: none;
                margin: 0;
            }
        }
    </style>
</head>
<body>
    <div class="ingresso-container">
        <div class="ingresso-header">
            <div class="evento-title">🏐 I TORNEIO BENEFICENTE</div>
            <div class="evento-subtitle">🏆 CONEXÃO SOLIDÁRIA 2025 🏆</div>
            <div class="evento-data">📅 Data do Evento</div>
        </div>
        
        <div class="ingresso-body">
            <div class="dados-participante">
                <h3>👤 Dados do Participante</h3>
                
                <div class="dado-item">
                    <span class="dado-label">🆔 ID:</span>
                    <span class="dado-valor">{{ ingresso[0] }}</span>
                </div>
                
                <div class="dado-item">
                    <span class="dado-label">👤 Nome:</span>
                    <span class="dado-valor">{{ ingresso[1] }}</span>
                </div>
                
                <div class="dado-item">
                    <span class="dado-label">📧 Email:</span>
                    <span class="dado-valor">{{ ingresso[2] }}</span>
                </div>
                
                <div class="dado-item">
                    <span class="dado-label">📱 Telefone:</span>
                    <span class="dado-valor">{{ ingresso[3] or 'Não informado' }}</span>
                </div>
                
                <div class="dado-item">
                    <span class="dado-label">🎂 Idade:</span>
                    <span class="dado-valor">{{ ingresso[4] }} anos</span>
                </div>
                
                <div class="dado-item">
                    <span class="dado-label">🏷️ Categoria:</span>
                    <span class="dado-valor">{{ ingresso[5] }}</span>
                </div>
            </div>
            
            <div class="qr-section">
                <h4>📱 QR Code</h4>
                <div class="qr-code">
                    <img src="data:image/png;base64,{{ qr_code }}" alt="QR Code">
                </div>
                <div class="ingresso-id">ID: {{ ingresso[0] }}</div>
            </div>
            
            <div class="preco-box">
                <div class="preco-valor">
                    {% if ingresso[6] == 0 %}
                        🎁 GRATUITO
                    {% else %}
                        💰 R$ {{ "%.2f"|format(ingresso[6]) }}
                    {% endif %}
                </div>
                <div class="preco-label">Valor da Inscrição</div>
            </div>
            
            <div class="evento-details">
                <h4>📍 Informações do Evento</h4>
                <p><strong>📍 Local:</strong> Rua Jaboti, 231 - Novo Aleixo<br>
                   <strong>🗺️ Ref.:</strong> Próximo à USF 58 - Águas Claras 2</p>
                
                <div class="detalhes-grid">
                    <div class="detalhe-item">
                        <div class="detalhe-emoji">🏊‍♂️</div>
                        <div class="detalhe-texto">Piscina</div>
                    </div>
                    <div class="detalhe-item">
                        <div class="detalhe-emoji">🥩</div>
                        <div class="detalhe-texto">Churrasco</div>
                    </div>
                    <div class="detalhe-item">
                        <div class="detalhe-emoji">🎱</div>
                        <div class="detalhe-texto">Sinuca</div>
                    </div>
                    <div class="detalhe-item">
                        <div class="detalhe-emoji">🎤</div>
                        <div class="detalhe-texto">Karaokê</div>
                    </div>
                </div>
            </div>
            
            <div class="grupos-whatsapp">
                <h4>📲 Entre nos Grupos do WhatsApp</h4>
                <div class="grupos-links">
                    <a href="https://chat.whatsapp.com/C0PvsakJsvPIKD7XKVhKMf" 
                       class="grupo-link grupo-iniciante">
                        🏐 Grupo Iniciante (Manhã)
                    </a>
                    <a href="https://chat.whatsapp.com/LSOR6KMha1uLvtmNrvzutt" 
                       class="grupo-link grupo-intermediario">
                        🏆 Grupo Intermediário (Tarde)
                    </a>
                </div>
            </div>
        </div>
        
        <div class="acoes">
            <button onclick="window.print()" class="btn btn-print">🖨️ Imprimir</button>
            <a href="/" class="btn btn-back">🔙 Voltar</a>
        </div>
    </div>
</body>
</html>
'''

if __name__ == '__main__':
    init_db()
    print("🚀 Servidor iniciando...")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
