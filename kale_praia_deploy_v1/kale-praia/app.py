from flask import Flask, render_template, request, jsonify
from datetime import datetime
import re, sqlite3

from database import get_db, init_db
from business import (
    calcular_reserva, calcular_cancelamento,
    calcular_reagendamento, validar_multiplas_quadras,
    cancelamento_chuva, PRECOS
)

app = Flask(__name__)

def detect_device(ua):
    ua = ua.lower()
    if re.search(r'(iphone|android.*mobile|windows phone)', ua):
        return 'mobile'
    elif re.search(r'(ipad|android(?!.*mobile)|tablet)', ua):
        return 'tablet'
    return 'desktop'

with app.app_context():
    init_db()

@app.route('/')
def index():
    device = detect_device(request.headers.get('User-Agent', ''))
    return render_template('index.html', device=device)

@app.route('/agendar')
def agendar():
    return render_template('agendar.html')

# ── CLIENTES ──

@app.route('/api/clientes', methods=['GET'])
def api_clientes():
    db = get_db()
    rows = db.execute("""
        SELECT c.*, COUNT(r.id) as total_reservas,
               COALESCE(SUM(CASE WHEN r.status='pago' THEN r.valor_total ELSE 0 END),0) as total_gasto
        FROM clientes c LEFT JOIN reservas r ON r.cliente_id=c.id
        GROUP BY c.id ORDER BY c.nome
    """).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/clientes', methods=['POST'])
def api_criar_cliente():
    data = request.json
    nome = (data.get('nome') or '').strip()
    if not nome:
        return jsonify({'erro': 'Nome obrigatório'}), 400
    categoria = data.get('categoria', 'nao_aluno')
    if categoria not in PRECOS:
        return jsonify({'erro': 'Categoria inválida'}), 400
    db = get_db()
    cur = db.execute("INSERT INTO clientes (nome, telefone, categoria) VALUES (?,?,?)",
                     (nome, data.get('telefone',''), categoria))
    db.commit()
    cid = cur.lastrowid
    db.close()
    return jsonify({'id': cid, 'mensagem': f'Cliente {nome} cadastrado!'})

# ── RESERVAS ──

@app.route('/api/reservas', methods=['GET'])
def api_reservas():
    status = request.args.get('status')
    quadra = request.args.get('quadra')
    data   = request.args.get('data')
    w, p   = [], []
    if status: w.append("r.status=?"); p.append(status)
    if quadra: w.append("r.quadra=?"); p.append(int(quadra))
    if data:   w.append("r.data=?");   p.append(data)
    where = ("WHERE " + " AND ".join(w)) if w else ""
    db = get_db()
    rows = db.execute(f"""
        SELECT r.*, c.nome as cliente_nome, c.telefone as cliente_telefone
        FROM reservas r JOIN clientes c ON c.id=r.cliente_id
        {where} ORDER BY r.data, r.horario_inicio
    """, p).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/reservar', methods=['POST'])
def api_reservar():
    data       = request.json
    cliente_id = data.get('cliente_id')
    quadra     = data.get('quadra')
    data_res   = data.get('data')
    horario    = data.get('horario')
    categoria  = data.get('categoria')
    hora_extra = data.get('hora_extra', False)

    if not all([cliente_id, quadra, data_res, horario, categoria]):
        return jsonify({'erro': 'Campos obrigatórios faltando'}), 400

    calc = calcular_reserva(categoria, hora_extra)
    if calc.get('erro'):
        return jsonify({'erro': calc['erro']}), 400

    db = get_db()
    if not db.execute("SELECT id FROM clientes WHERE id=?", (cliente_id,)).fetchone():
        db.close(); return jsonify({'erro': 'Cliente não encontrado'}), 404

    if db.execute("""SELECT id FROM reservas
        WHERE quadra=? AND data=? AND horario_inicio=? AND status NOT IN ('cancelado','reagendado')
    """, (quadra, data_res, horario)).fetchone():
        db.close(); return jsonify({'erro': 'Horário já reservado'}), 409

    qtd = db.execute("""SELECT COUNT(*) as c FROM reservas
        WHERE cliente_id=? AND data=? AND horario_inicio=? AND status NOT IN ('cancelado','reagendado')
    """, (cliente_id, data_res, horario)).fetchone()['c']
    if qtd >= 2:
        db.close(); return jsonify({'erro': 'Limite de 2 quadras simultâneas atingido'}), 400

    cur = db.execute("""INSERT INTO reservas
        (cliente_id,quadra,data,horario_inicio,categoria,duracao_min,hora_extra,valor_base,valor_extra,valor_total,status)
        VALUES (?,?,?,?,?,?,?,?,?,?,'reservado')
    """, (cliente_id, quadra, data_res, horario, categoria,
          calc['duracao_min'], 1 if hora_extra else 0,
          calc['valor_base'], calc['valor_extra'], calc['valor_total']))
    db.commit()
    rid = cur.lastrowid
    db.close()
    return jsonify({'id': rid, 'valor_total': calc['valor_total'], 'mensagem': f'Reserva #{rid} criada!'})

@app.route('/api/reservas/<int:rid>/pagar', methods=['POST'])
def api_pagar(rid):
    db = get_db()
    r = db.execute("SELECT * FROM reservas WHERE id=?", (rid,)).fetchone()
    if not r: db.close(); return jsonify({'erro': 'Não encontrada'}), 404
    if r['status'] != 'reservado': db.close(); return jsonify({'erro': f'Status: {r["status"]}'}), 400
    db.execute("UPDATE reservas SET status='pago', atualizado_em=datetime('now','localtime') WHERE id=?", (rid,))
    db.execute("INSERT INTO movimentacoes (reserva_id,tipo,descricao) VALUES (?,?,?)",
               (rid, 'pagamento', f'Pago R$ {r["valor_total"]:.2f}'))
    db.commit(); db.close()
    return jsonify({'mensagem': f'Pagamento #{rid} confirmado!'})

@app.route('/api/reservas/<int:rid>/cancelar', methods=['POST'])
def api_cancelar(rid):
    db = get_db()
    r = db.execute("SELECT * FROM reservas WHERE id=?", (rid,)).fetchone()
    if not r: db.close(); return jsonify({'erro': 'Não encontrada'}), 404
    if r['status'] == 'cancelado': db.close(); return jsonify({'erro': 'Já cancelada'}), 400
    calc = calcular_cancelamento(r['data'], r['horario_inicio'], r['valor_total'])
    db.execute("UPDATE reservas SET status='cancelado', atualizado_em=datetime('now','localtime') WHERE id=?", (rid,))
    db.execute("INSERT INTO movimentacoes (reserva_id,tipo,descricao,multa,devolucao) VALUES (?,?,?,?,?)",
               (rid, 'cancelamento', calc['mensagem'], calc['multa'], calc['devolucao']))
    db.commit(); db.close()
    return jsonify({**calc, 'reserva_id': rid})

@app.route('/api/reservas/<int:rid>/reagendar', methods=['POST'])
def api_reagendar(rid):
    data = request.json
    nd, nh = data.get('nova_data'), data.get('novo_horario')
    if not nd or not nh: return jsonify({'erro': 'Nova data e horário obrigatórios'}), 400
    db = get_db()
    r = db.execute("SELECT * FROM reservas WHERE id=?", (rid,)).fetchone()
    if not r: db.close(); return jsonify({'erro': 'Não encontrada'}), 404
    if r['status'] == 'cancelado': db.close(); return jsonify({'erro': 'Cancelada'}), 400
    calc = calcular_reagendamento(r['data'], r['horario_inicio'])
    if db.execute("""SELECT id FROM reservas WHERE quadra=? AND data=? AND horario_inicio=?
        AND status NOT IN ('cancelado','reagendado') AND id!=?""", (r['quadra'], nd, nh, rid)).fetchone():
        db.close(); return jsonify({'erro': 'Novo horário já reservado'}), 409
    db.execute("UPDATE reservas SET data=?, horario_inicio=?, status='reservado', atualizado_em=datetime('now','localtime') WHERE id=?", (nd, nh, rid))
    db.execute("INSERT INTO movimentacoes (reserva_id,tipo,descricao,multa) VALUES (?,?,?,?)",
               (rid, 'reagendamento', f'Para {nd} {nh}. {calc["mensagem"]}', calc['taxa']))
    db.commit(); db.close()
    return jsonify({**calc, 'reserva_id': rid, 'nova_data': nd, 'novo_horario': nh})

@app.route('/api/reservas/<int:rid>/chuva', methods=['POST'])
def api_chuva(rid):
    data = request.json
    nd, nh = data.get('nova_data'), data.get('novo_horario')
    if not nd or not nh: return jsonify({'erro': 'Nova data e horário obrigatórios'}), 400
    db = get_db()
    r = db.execute("SELECT * FROM reservas WHERE id=?", (rid,)).fetchone()
    if not r: db.close(); return jsonify({'erro': 'Não encontrada'}), 404
    calc = cancelamento_chuva(rid)
    db.execute("UPDATE reservas SET data=?, horario_inicio=?, atualizado_em=datetime('now','localtime') WHERE id=?", (nd, nh, rid))
    db.execute("INSERT INTO movimentacoes (reserva_id,tipo,descricao) VALUES (?,?,?)",
               (rid, 'chuva', f'Reagendado por chuva para {nd} {nh}'))
    db.commit(); db.close()
    return jsonify({**calc, 'reserva_id': rid})

# ── STATS ──

@app.route('/api/stats', methods=['GET'])
def api_stats():
    hoje = datetime.now().strftime('%Y-%m-%d')
    db   = get_db()
    res  = db.execute("SELECT COUNT(*) as c FROM reservas WHERE data=? AND status!='cancelado'", (hoje,)).fetchone()['c']
    rec  = db.execute("SELECT COALESCE(SUM(valor_total),0) as s FROM reservas WHERE data=? AND status='pago'", (hoje,)).fetchone()['s']
    can  = db.execute("SELECT COUNT(*) as c FROM reservas WHERE data=? AND status='cancelado'", (hoje,)).fetchone()['c']
    cli  = db.execute("SELECT COUNT(*) as c FROM clientes").fetchone()['c']
    mul  = db.execute("""SELECT COALESCE(SUM(m.multa),0) as s FROM movimentacoes m
        JOIN reservas r ON r.id=m.reserva_id WHERE DATE(m.criado_em)=? AND m.tipo='cancelamento'""", (hoje,)).fetchone()['s']
    db.close()
    return jsonify({'reservas_hoje': res, 'receita_hoje': rec, 'cancelamentos_hoje': can,
                    'multas_hoje': mul, 'total_clientes': cli, 'meta_diaria': 2000})

@app.route('/api/calcular', methods=['POST'])
def api_calcular():
    data = request.json
    acao = data.get('acao')
    if acao == 'reserva':
        return jsonify(calcular_reserva(data.get('categoria'), data.get('hora_extra', False)))
    elif acao == 'cancelamento':
        return jsonify(calcular_cancelamento(data.get('data'), data.get('horario'), float(data.get('valor_pago', 0))))
    elif acao == 'reagendamento':
        return jsonify(calcular_reagendamento(data.get('data'), data.get('horario')))
    return jsonify({'erro': 'Ação inválida'}), 400

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=10000)
