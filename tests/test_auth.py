"""Tests del módulo auth — funciones que no requieren BD."""
import pytest
from kuboc_core import auth


# ── hash_pin ────────────────────────────────────────────────

def test_hash_pin_determinista():
    """El mismo PIN debe producir el mismo hash siempre."""
    h1 = auth.hash_pin('123456')
    h2 = auth.hash_pin('123456')
    assert h1 == h2


def test_hash_pin_distintos_pins_distinto_hash():
    h1 = auth.hash_pin('123456')
    h2 = auth.hash_pin('123457')
    assert h1 != h2


def test_hash_pin_no_devuelve_pin_plano():
    pin = '987654'
    h = auth.hash_pin(pin)
    assert pin not in h, 'el hash debe NO contener el PIN en plano'


def test_hash_pin_longitud_consistente():
    """SHA-256 hex = 64 chars."""
    assert len(auth.hash_pin('1')) == len(auth.hash_pin('123456789'))


def test_hash_pin_empty_pin_no_crashea():
    """Aunque sea PIN vacío, no debe explotar."""
    h = auth.hash_pin('')
    assert isinstance(h, str)


# ── signed_token + verify_signed ────────────────────────────

def test_signed_token_round_trip():
    """Firmar y verificar el mismo payload retorna el original."""
    payload = {'usuario_id': 1, 'sistema': 'facturas'}
    token = auth.signed_token(payload)
    recovered = auth.verify_signed(token)
    assert recovered == payload


def test_verify_signed_token_invalido_devuelve_none():
    assert auth.verify_signed('token-falso') is None
    assert auth.verify_signed('') is None


def test_signed_token_distintos_payloads_distintos_tokens():
    t1 = auth.signed_token({'a': 1})
    t2 = auth.signed_token({'a': 2})
    assert t1 != t2


def test_signed_token_con_payload_complejo():
    payload = {
        'usuario_id': 42,
        'rol': 'admin',
        'proyectos': [1, 2, 3],
        'metadata': {'ip': '192.168.1.1'},
    }
    token = auth.signed_token(payload)
    recovered = auth.verify_signed(token)
    assert recovered == payload


# ── Manipulación maliciosa ────────────────────────────────────

def test_signed_token_tampered_devuelve_none():
    """Si alguien modifica el token, verify debe devolver None."""
    token = auth.signed_token({'usuario_id': 1})
    # Modificar último carácter (rompe firma)
    if len(token) > 1:
        tampered = token[:-1] + ('X' if token[-1] != 'X' else 'Y')
        assert auth.verify_signed(tampered) is None
