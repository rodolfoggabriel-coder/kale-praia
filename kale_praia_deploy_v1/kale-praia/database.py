import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'kale.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS clientes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nome        TEXT NOT NULL,
            telefone    TEXT,
            categoria   TEXT NOT NULL DEFAULT 'nao_aluno',
            criado_em   TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS reservas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id      INTEGER REFERENCES clientes(id),
            quadra          INTEGER NOT NULL,         -- 1 a 4
            data            TEXT NOT NULL,            -- YYYY-MM-DD
            horario_inicio  TEXT NOT NULL,            -- HH:MM
            categoria       TEXT NOT NULL,            -- barragem | aluno_kale | nao_aluno
            duracao_min     INTEGER NOT NULL,         -- 60 ou 90
            hora_extra      INTEGER DEFAULT 0,        -- 0 ou 1
            valor_base      REAL NOT NULL,
            valor_extra     REAL DEFAULT 0,
            valor_total     REAL NOT NULL,
            status          TEXT DEFAULT 'reservado', -- reservado | pago | cancelado | reagendado
            criado_em       TEXT DEFAULT (datetime('now','localtime')),
            atualizado_em   TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS aulas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nome        TEXT NOT NULL,
            quadras     TEXT NOT NULL,   -- JSON array ex: [1,2]
            dias        TEXT NOT NULL,   -- JSON array ex: ["seg","qua"]
            inicio      TEXT NOT NULL,   -- HH:MM
            fim         TEXT NOT NULL,   -- HH:MM
            cor         TEXT DEFAULT '#5c6bc0',
            ativo       INTEGER DEFAULT 1,
            criado_em   TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS movimentacoes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            reserva_id  INTEGER REFERENCES reservas(id),
            tipo        TEXT NOT NULL,   -- cancelamento | reagendamento | pagamento | chuva
            descricao   TEXT,
            multa       REAL DEFAULT 0,
            devolucao   REAL DEFAULT 0,
            criado_em   TEXT DEFAULT (datetime('now','localtime'))
        );
    """)

    # Seed de clientes mock se vazio
    count = c.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
    if count == 0:
        clientes_seed = [
            ('Ana Paula Costa',  '(61) 99123-0001', 'aluno_kale'),
            ('Bruno Martins',    '(61) 99123-0002', 'aluno_kale'),
            ('Carla Ribeiro',    '(61) 99123-0003', 'barragem'),
            ('Diego Fonseca',    '(61) 99123-0004', 'nao_aluno'),
            ('Eduarda Lima',     '(61) 99123-0005', 'aluno_kale'),
            ('Felipe Santos',    '(61) 99123-0006', 'aluno_kale'),
            ('Gabriela Moura',   '(61) 99123-0007', 'nao_aluno'),
            ('Henrique Torres',  '(61) 99123-0008', 'barragem'),
            ('Isabela Nunes',    '(61) 99123-0009', 'aluno_kale'),
            ('João Carvalho',    '(61) 99123-0010', 'aluno_kale'),
        ]
        c.executemany("INSERT INTO clientes (nome, telefone, categoria) VALUES (?,?,?)", clientes_seed)

        # Seed de reservas mock
        reservas_seed = [
            (1, 1, '2026-03-04', '08:00', 'aluno_kale',  60, 0, 80,  0,  80,  'pago'),
            (2, 2, '2026-03-04', '09:00', 'aluno_kale',  60, 0, 80,  0,  80,  'pago'),
            (3, 1, '2026-03-04', '10:00', 'barragem',    90, 0, 100, 0,  100, 'reservado'),
            (4, 4, '2026-03-04', '11:00', 'nao_aluno',   60, 0, 110, 0,  110, 'pago'),
            (5, 2, '2026-03-04', '14:00', 'aluno_kale',  60, 0, 80,  0,  80,  'cancelado'),
            (6, 6, '2026-03-05', '08:00', 'aluno_kale',  60, 0, 80,  0,  80,  'reservado'),
            (7, 3, '2026-03-05', '09:00', 'barragem',    90, 0, 100, 0,  100, 'pago'),
            (8, 8, '2026-03-05', '10:00', 'barragem',    90, 0, 100, 0,  100, 'pago'),
            (9, 5, '2026-03-06', '17:00', 'aluno_kale',  60, 0, 80,  0,  80,  'reservado'),
            (10,9, '2026-03-06', '18:00', 'aluno_kale',  60, 0, 80,  0,  80,  'pago'),
        ]
        c.executemany("""
            INSERT INTO reservas 
            (cliente_id, quadra, data, horario_inicio, categoria, duracao_min, hora_extra,
             valor_base, valor_extra, valor_total, status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, reservas_seed)

    conn.commit()
    conn.close()
