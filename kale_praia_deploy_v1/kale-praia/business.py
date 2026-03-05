"""
Regras de negócio KALE PRAIA — conforme Diretrizes de Marca v1.0
"""
from datetime import datetime, timedelta

# ─── TABELA DE PREÇOS ───
PRECOS = {
    'barragem':   {'valor': 100.0, 'duracao': 90, 'hora_extra': False, 'valor_extra': 0},
    'aluno_kale': {'valor': 80.0,  'duracao': 60, 'hora_extra': True,  'valor_extra': 50},
    'nao_aluno':  {'valor': 110.0, 'duracao': 60, 'hora_extra': True,  'valor_extra': 70},
}

MULTA_CANCELAMENTO  = 40.0
MULTA_REAGENDAMENTO = 40.0
LIMITE_HORAS        = 48
PRAZO_DEVOLUCAO_DIAS = 5


def calcular_reserva(categoria: str, hora_extra: bool = False) -> dict:
    """
    Calcula valor total de uma reserva.
    Retorna: { valor_base, valor_extra, valor_total, duracao_min, erro? }
    """
    if categoria not in PRECOS:
        return {'erro': f'Categoria inválida: {categoria}'}

    regra = PRECOS[categoria]

    if hora_extra and not regra['hora_extra']:
        return {'erro': 'Categoria Barragem não permite hora extra'}

    valor_base  = regra['valor']
    valor_extra = regra['valor_extra'] if hora_extra else 0.0
    valor_total = valor_base + valor_extra
    duracao     = regra['duracao'] + (60 if hora_extra else 0)

    return {
        'valor_base':  valor_base,
        'valor_extra': valor_extra,
        'valor_total': valor_total,
        'duracao_min': duracao,
        'hora_extra':  hora_extra,
        'erro':        None
    }


def calcular_cancelamento(data_reserva_str: str, horario_str: str, valor_pago: float) -> dict:
    """
    Regras:
    - >= 48h antes: devolução total, sem multa
    - <  48h antes: multa R$40, devolve restante
    """
    dt_reserva = _parse_dt(data_reserva_str, horario_str)
    horas_ate  = _horas_ate(dt_reserva)

    if horas_ate >= LIMITE_HORAS:
        return {
            'tipo':      'integral',
            'multa':     0.0,
            'devolucao': valor_pago,
            'mensagem':  'Devolução integral — sem multas',
            'prazo':     f'{PRAZO_DEVOLUCAO_DIAS} dias úteis',
            'horas_ate': round(horas_ate, 1),
        }
    else:
        devolucao = max(0.0, valor_pago - MULTA_CANCELAMENTO)
        return {
            'tipo':      'com_multa',
            'multa':     MULTA_CANCELAMENTO,
            'devolucao': devolucao,
            'mensagem':  f'Multa de R$ {MULTA_CANCELAMENTO:.0f} aplicada',
            'prazo':     f'{PRAZO_DEVOLUCAO_DIAS} dias úteis',
            'horas_ate': round(horas_ate, 1),
        }


def calcular_reagendamento(data_reserva_str: str, horario_str: str) -> dict:
    """
    Regras:
    - >= 48h antes: gratuito
    - <  48h antes: taxa R$40
    """
    dt_reserva = _parse_dt(data_reserva_str, horario_str)
    horas_ate  = _horas_ate(dt_reserva)

    if horas_ate >= LIMITE_HORAS:
        return {
            'gratuito': True,
            'taxa':     0.0,
            'mensagem': 'Reagendamento gratuito',
            'horas_ate': round(horas_ate, 1),
        }
    else:
        return {
            'gratuito': False,
            'taxa':     MULTA_REAGENDAMENTO,
            'mensagem': f'Taxa de reagendamento: R$ {MULTA_REAGENDAMENTO:.0f}',
            'horas_ate': round(horas_ate, 1),
        }


def validar_multiplas_quadras(quadras: list, duracao_min: int) -> dict:
    """
    - Máximo 2 quadras simultâneas
    - Máximo 3 horas (180 min) consecutivas
    """
    if len(quadras) > 2:
        return {'valido': False, 'erro': 'Máximo de 2 quadras por reserva'}
    if duracao_min > 180:
        return {'valido': False, 'erro': 'Duração máxima de 3 horas consecutivas'}
    return {'valido': True, 'mensagem': f'{len(quadras)} quadra(s) — {duracao_min}min — OK'}


def cancelamento_chuva(reserva_id: int) -> dict:
    """Reagendamento automático por chuva — sem cobrança, sem devolução."""
    return {
        'tipo':     'chuva',
        'taxa':     0.0,
        'devolucao': 0.0,
        'mensagem': 'Reagendamento automático por condições climáticas — sem custos adicionais',
    }


# ─── HELPERS ───
def _parse_dt(data_str: str, horario_str: str) -> datetime:
    """Converte 'YYYY-MM-DD' + 'HH:MM' em datetime."""
    return datetime.strptime(f'{data_str} {horario_str}', '%Y-%m-%d %H:%M')

def _horas_ate(dt_reserva: datetime) -> float:
    """Retorna horas entre agora e a reserva (pode ser negativo se já passou)."""
    delta = dt_reserva - datetime.now()
    return delta.total_seconds() / 3600
