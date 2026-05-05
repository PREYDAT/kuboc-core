"""Configuración común para tests de kuboc-core.

Estos tests NO requieren Postgres real — los que tocan BD usan mocks.
Para tests de integración con Postgres real, definir DATABASE_URL_TEST y
ejecutar con `pytest -m integration`.
"""
import os
import sys
from pathlib import Path

# Asegurar que kuboc_core es importable desde tests
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Setear secret de test antes de importar config
os.environ.setdefault('KUBOC_CORE_SECRET', 'test-secret-32-chars-long-xxxxxxxxxxxxxxx')
os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost:5432/test_kuboc')
