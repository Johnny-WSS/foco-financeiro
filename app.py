# app.py COMPLETO e ATUALIZADO (com API)

# Importei jsonify para criar respostas da API
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
from sqlalchemy import func

# --- 1. Configuração e Modelos (Sem Mudanças) ---
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///foco_financeiro.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'uma-chave-secreta-muito-dificil-de-adivinhar' 

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)
    transacoes = db.relationship('Transacao', backref='autor', lazy=True)
    categorias = db.relationship('Categoria', backref='criador', lazy=True)

class Categoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    transacoes = db.relationship('Transacao', backref='categoria_assoc', lazy=True)

class Transacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    tipo = db.Column(db.String(7), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=True)

# --- 2. Rotas de Autenticação e Gestão (Sem Mudanças) ---
# Rotas: index, cadastro, login, logout, perfil, excluir_conta
# Rotas: gerenciar_categorias, adicionar_categoria, editar_categoria, excluir_categoria

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')
        novo_usuario = Usuario(nome=nome, email=email, senha=senha_hash)
        try:
            db.session.add(novo_usuario)
            db.session.commit()
            flash('Conta criada com sucesso! Por favor, faça o login.', 'success')
            return redirect(url_for('login')) 
        except:
            flash('Erro ao cadastrar usuário. E-mail já existente.', 'danger')
            return redirect(url_for('cadastro'))
    return render_template('cadastro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha_candidata = request.form['senha']
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and bcrypt.check_password_hash(usuario.senha, senha_candidata):
            session['user_id'] = usuario.id
            session['user_name'] = usuario.nome
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login inválido. Verifique seu e-mail e senha.', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('login'))

@app.route('/perfil', methods=['GET', 'POST'])
def perfil():
    if 'user_id' not in session:
        flash('Você precisa estar logado.', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    usuario = Usuario.query.get_or_404(user_id)

    if request.method == 'POST':
        usuario.nome = request.form['nome']
        db.session.commit()
        session['user_name'] = usuario.nome
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('perfil'))

    return render_template('perfil.html', usuario=usuario)

@app.route('/perfil/excluir', methods=['POST'])
def excluir_conta():
    if 'user_id' not in session:
        flash('Você precisa estar logado.', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    usuario = Usuario.query.get(user_id)
    senha_digitada = request.form['senha']

    if usuario and bcrypt.check_password_hash(usuario.senha, senha_digitada):
        Transacao.query.filter_by(usuario_id=user_id).delete()
        Categoria.query.filter_by(usuario_id=user_id).delete()
        
        db.session.delete(usuario)
        db.session.commit()
        
        session.clear()
        flash('Sua conta foi excluída com sucesso.', 'info')
        return redirect(url_for('login'))
    else:
        flash('Senha incorreta. A exclusão falhou.', 'danger')
        return redirect(url_for('perfil'))

@app.route('/categorias')
def gerenciar_categorias():
    if 'user_id' not in session:
        flash('Você precisa estar logado.', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    categorias = Categoria.query.filter_by(usuario_id=user_id).order_by(Categoria.nome).all()
    
    return render_template('categorias.html', categorias=categorias)

@app.route('/categorias/add', methods=['POST'])
def adicionar_categoria():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nome_categoria = request.form['nome']
        user_id = session['user_id']
        
        existente = Categoria.query.filter_by(usuario_id=user_id, nome=nome_categoria).first()
        if not existente:
            nova_categoria = Categoria(nome=nome_categoria, usuario_id=user_id)
            db.session.add(nova_categoria)
            db.session.commit()
            flash('Categoria adicionada com sucesso!', 'success')
        else:
            flash('Essa categoria já existe.', 'danger')
            
    return redirect(url_for('gerenciar_categorias'))

@app.route('/categorias/edit/<int:id>', methods=['GET', 'POST'])
def editar_categoria(id):
    if 'user_id' not in session:
        flash('Você precisa estar logado.', 'warning')
        return redirect(url_for('login'))

    categoria = Categoria.query.get_or_404(id)
    user_id = session['user_id']

    if categoria.criador.id != user_id:
        flash('Operação não permitida.', 'danger')
        return redirect(url_for('gerenciar_categorias'))

    if request.method == 'POST':
        novo_nome = request.form['nome']
        existente = Categoria.query.filter_by(usuario_id=user_id, nome=novo_nome).first()
        if existente and existente.id != id:
            flash('Você já tem uma categoria com esse nome.', 'danger')
            return redirect(url_for('editar_categoria', id=id))

        categoria.nome = novo_nome
        db.session.commit()
        flash('Categoria atualizada com sucesso!', 'success')
        return redirect(url_for('gerenciar_categorias'))

    return render_template('editar_categoria.html', categoria=categoria)

@app.route('/categorias/delete/<int:id>')
def excluir_categoria(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    categoria = Categoria.query.get_or_404(id)
    
    if categoria.criador.id != session['user_id']:
        flash('Operação não permitida.', 'danger')
        return redirect(url_for('gerenciar_categorias'))

    transacao_usando = Transacao.query.filter_by(categoria_id=id).first()
    if transacao_usando:
        flash('Não é possível excluir: esta categoria está sendo usada por uma transação.', 'danger')
        return redirect(url_for('gerenciar_categorias'))

    db.session.delete(categoria)
    db.session.commit()
    flash('Categoria excluída com sucesso.', 'success')
    return redirect(url_for('gerenciar_categorias'))

@app.route('/transacao/edit/<int:id>', methods=['GET', 'POST'])
def editar_transacao(id):
    if 'user_id' not in session:
        flash('Você precisa estar logado.', 'warning')
        return redirect(url_for('login'))

    transacao = Transacao.query.get_or_404(id)
    user_id = session['user_id']

    if transacao.autor.id != user_id:
        flash('Operação não permitida.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        transacao.descricao = request.form['descricao']
        transacao.valor = float(request.form['valor'])
        transacao.tipo = request.form['tipo']
        data_str = request.form['data']
        transacao.data = datetime.strptime(data_str, '%Y-%m-%d').date()
        categoria_id = request.form.get('categoria')

        if transacao.tipo == 'despesa' and categoria_id:
            transacao.categoria_id = int(categoria_id)
        else:
            transacao.categoria_id = None
        
        db.session.commit()
        flash('Transação atualizada com sucesso!', 'success')
        return redirect(url_for('dashboard'))

    categorias = Categoria.query.filter_by(usuario_id=user_id).all()
    return render_template('editar_transacao.html', transacao=transacao, categorias=categorias)

@app.route('/transacao/delete/<int:id>')
def excluir_transacao(id):
    if 'user_id' not in session:
        flash('Você precisa estar logado.', 'warning')
        return redirect(url_for('login'))

    transacao = Transacao.query.get_or_404(id)

    if transacao.autor.id != session['user_id']:
        flash('Operação não permitida.', 'danger')
        return redirect(url_for('dashboard'))

    db.session.delete(transacao)
    db.session.commit()
    flash('Transação excluída com sucesso.', 'success')
    return redirect(url_for('dashboard'))

# --- 3. MUDANÇAS NO DASHBOARD E NOVAS ROTAS DE API ---

@app.route('/dashboard', methods=['GET'])
def dashboard():
    if 'user_id' not in session:
        flash('Você precisa estar logado para ver esta página.', 'warning')
        return redirect(url_for('login'))


    categorias = Categoria.query.filter_by(usuario_id=session['user_id']).order_by(Categoria.nome).all()
    
    return render_template('dashboard.html', 
                            nome_usuario=session['user_name'], 
                            categorias=categorias) # Envia categorias SÓ para o formulário

# NOVA ROTA: Adicionar Transação
@app.route('/dashboard/add_transacao', methods=['POST'])
def add_transacao():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    descricao = request.form['descricao']
    valor = float(request.form['valor'])
    tipo = request.form['tipo']
    data_str = request.form['data']
    data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
    categoria_id = request.form.get('categoria')

    nova_transacao = Transacao(
        descricao=descricao, 
        valor=valor, 
        tipo=tipo, 
        data=data_obj,
        usuario_id=user_id,
        categoria_id=int(categoria_id) if tipo == 'despesa' and categoria_id else None
    )
    
    db.session.add(nova_transacao)
    db.session.commit()
    
    flash('Transação adicionada com sucesso!', 'success')
    return redirect(url_for('dashboard'))


# --- 4. NOVAS ROTAS DE API ---

# API para buscar o resumo do painel
@app.route('/api/resumo')
def api_resumo():
    if 'user_id' not in session:
        return jsonify({'erro': 'Nao autorizado'}), 401
    
    user_id = session['user_id']
    hoje = datetime.utcnow().date()
    primeiro_dia_mes = hoje.replace(day=1)

    total_receitas_query = db.session.query(func.sum(Transacao.valor)).filter(
        Transacao.usuario_id == user_id,
        Transacao.tipo == 'receita',
        Transacao.data >= primeiro_dia_mes
    ).scalar()
    total_receitas = total_receitas_query or 0.0

    total_despesas_query = db.session.query(func.sum(Transacao.valor)).filter(
        Transacao.usuario_id == user_id,
        Transacao.tipo == 'despesa',
        Transacao.data >= primeiro_dia_mes
    ).scalar()
    total_despesas = total_despesas_query or 0.0

    saldo_mes = total_receitas - total_despesas
    
    # Retorna os dados em formato JSON
    return jsonify(
        total_receitas=total_receitas,
        total_despesas=total_despesas,
        saldo_mes=saldo_mes
    )

# API para buscar a lista de transações
@app.route('/api/transacoes')
def api_transacoes():
    if 'user_id' not in session:
        return jsonify({'erro': 'Nao autorizado'}), 401
    
    user_id = session['user_id']
    
    transacoes = Transacao.query.filter_by(usuario_id=user_id).order_by(Transacao.data.desc()).all()
    
    # formatar os dados para JSON
    lista_transacoes = []
    for t in transacoes:
        lista_transacoes.append({
            'id': t.id,
            'descricao': t.descricao,
            'valor': t.valor,
            'tipo': t.tipo,
            'data': t.data.strftime('%d/%m/%Y'),
            'categoria_nome': t.categoria_assoc.nome if t.categoria_assoc else 'N/A'
        })
        
    return jsonify(transacoes=lista_transacoes)


# --- 5. Bloco de Execução (Sem Mudanças) ---
if __name__ == '__main__':
    app.run(debug=True)