# tests/analysis/test_graph_builder.py

import pytest
import pandas as pd
import logging
from unittest.mock import patch, MagicMock

from neo4j.exceptions import CypherSyntaxError, ServiceUnavailable
from analysis.graph_builder import GraphBuilder


@patch("analysis.graph_builder.GraphDatabase.driver")
def test_crear_indices_maneja_errores(mock_driver_class, caplog):
    """Verifica que se loguean errores si ocurre una excepción al crear índices."""
    mock_session = MagicMock()
    mock_session.run.side_effect = [CypherSyntaxError("índice incorrecto")] * 4
    mock_driver = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_driver_class.return_value = mock_driver

    builder = GraphBuilder(uri="bolt://fake", user="neo4j", password="test", database="Congreso")
    with caplog.at_level(logging.ERROR, logger="analysis.graph_builder"):
        builder.crear_indices()
    assert "Error creando constraint para Diputado" in caplog.text
    assert "Error creando constraint para Grupo" in caplog.text
    assert "Error creando constraint para Provincia" in caplog.text


@patch("analysis.graph_builder.GraphDatabase.driver")
def test_importar_grupos_maneja_errores(mock_driver_class, caplog):
    """Verifica que se loguean warnings si ocurre una excepción al importar grupos."""
    mock_session = MagicMock()
    # Primera llamada funciona, segunda lanza excepción
    mock_session.run.side_effect = [None, CypherSyntaxError("fallo")]
    mock_driver = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_driver_class.return_value = mock_driver
    builder = GraphBuilder(uri="bolt://fake", user="neo4j", password="test", database="Congreso")
    df = pd.DataFrame([
        {"nombre": "X", "grupo_parlamentario": "G", "fecha_alta": "01/01/2023", "fecha_baja": "", "legislatura":"15"},
        {"nombre": "Y", "grupo_parlamentario": "G2", "fecha_alta": "02/01/2023", "fecha_baja": "", "legislatura":"15"}
    ])
    with patch("pandas.read_csv", return_value=df):
        with caplog.at_level(logging.WARNING, logger="analysis.graph_builder"):
            builder.importar_grupos("fake.csv", "15")
    assert any("Error procesando fila" in r.getMessage() for r in caplog.records)


@patch("analysis.graph_builder.GraphDatabase.driver")
def test_importar_diputados_maneja_errores(mock_driver_class, caplog):
    """Verifica que se loguean warnings si ocurre una excepción al crear relaciones en diputados."""
    mock_session = MagicMock()
    # Primera llamada funciona, segunda lanza excepción
    mock_session.run.side_effect = [None, CypherSyntaxError("fallo")]
    mock_driver = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_driver_class.return_value = mock_driver
    builder = GraphBuilder(uri="bolt://fake", user="neo4j", password="test", database="Congreso")
    df = pd.DataFrame([
        {"nombre": "A", "provincia": "Diputado por Lugo", "sustituye_a": "", "fecha_alta_suplencia": "",
         "fecha_baja_suplencia": "", "legislatura":"15"},
        {"nombre": "Y", "provincia": "Diputada por Cádiz", "sustituye_a": "", "fecha_alta_suplencia": "",
         "fecha_baja_suplencia": "", "legislatura":"15"}
    ])
    with patch("pandas.read_csv", return_value=df):
        with caplog.at_level(logging.WARNING, logger="analysis.graph_builder"):
            builder.importar_diputados("fake.csv", "15")
    assert any("Error creando relación REPRESENTA_A" in r.getMessage() for r in caplog.records)


@patch("analysis.graph_builder.GraphDatabase.driver")
def test_importar_diputados_suplencia_warning(mock_driver_class, caplog):
    """Cubre el except Exception de la suplencia en importar_diputados (líneas 133-134)."""
    mock_session = MagicMock()
    # Primera llamada funciona (representa), segunda (suplencia) lanza excepción
    mock_session.run.side_effect = [None, CypherSyntaxError("fallo en suplencia")]
    mock_driver = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_driver_class.return_value = mock_driver
    builder = GraphBuilder(uri="bolt://fake", user="neo4j", password="test", database="Congreso")
    df = pd.DataFrame([
        {"nombre": "A", "provincia": "Diputado por Lugo", "sustituye_a": "B", "fecha_alta_suplencia": "",
         "fecha_baja_suplencia": "", "legislatura":"15"}
    ])
    with patch("pandas.read_csv", return_value=df):
        with caplog.at_level(logging.WARNING, logger="analysis.graph_builder"):
            builder.importar_diputados("fake.csv", "15")
    assert any("Error creando suplencia" in r.getMessage() for r in caplog.records)


@patch("analysis.graph_builder.GraphDatabase.driver")
def test_close_cierra_driver(mock_driver_class):
    """Cubre la línea de self.driver.close()."""
    mock_driver = MagicMock()
    mock_driver_class.return_value = mock_driver
    builder = GraphBuilder(uri="bolt://fake", user="neo4j", password="test", database="Congreso")
    builder.close()
    mock_driver.close.assert_called_once()


@patch("analysis.graph_builder.GraphDatabase.driver")
def test_importar_grupos_crea_relaciones(mock_driver_class):
    """Testea que importar_grupos() crea nodos Diputado y Grupo, y establece la relación PERTENECE_A."""
    mock_session = MagicMock()
    mock_driver = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_driver_class.return_value = mock_driver

    builder = GraphBuilder(uri="bolt://fake", user="neo4j", password="test", database="Congreso")
    df = pd.DataFrame([{
        "nombre": "Diputado X",
        "grupo_parlamentario": "PSOE",
        "fecha_alta": "01/01/2023",
        "fecha_baja": "",
        "legislatura": "15"
    }])
    with patch("pandas.read_csv", return_value=df):
        builder.importar_grupos("fake.csv", "15")

    calls = mock_session.run.call_args_list
    assert any(
        call_args[1].get("nombre") == "Diputado X" and
        call_args[1].get("grupo") == "PSOE" and
        call_args[1].get("fecha_alta") == "2023-01-01"
        for call_args in calls
    )


@patch("analysis.graph_builder.GraphDatabase.driver")
def test_importar_diputados_con_suplencia(mock_driver_class):
    """Testea que importar_diputados() crea nodos Diputado y Provincia y la relación de suplencia."""
    mock_session = MagicMock()
    mock_driver = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_driver_class.return_value = mock_driver

    builder = GraphBuilder(uri="bolt://fake", user="neo4j", password="test", database="Congreso")
    df = pd.DataFrame([{
        "nombre": "Diputada Y",
        "provincia": "Diputada por Córdoba",
        "sustituye_a": "Diputado Z",
        "fecha_alta_suplencia": "15/02/2024",
        "fecha_baja_suplencia": "",
        "legislatura": "15"
    }])
    with patch("pandas.read_csv", return_value=df):
        builder.importar_diputados("diputados.csv", "15")

    calls = mock_session.run.call_args_list
    assert any(
        call_args[1].get("nombre") == "Diputada Y" and
        call_args[1].get("provincia") == "Córdoba"
        for call_args in calls
    )
    assert any(
        call_args[1].get("sustituto") == "Diputada Y" and
        call_args[1].get("sustituido") == "Diputado Z" and
        call_args[1].get("fecha_alta") == "2024-02-15"
        for call_args in calls
    )


def test_formatear_fecha_valida():
    """Verifica que una fecha en formato DD/MM/YYYY se convierte correctamente."""
    assert GraphBuilder.formatear_fecha("01/12/2023") == "2023-12-01"


def test_formatear_fecha_vacia():
    """Verifica que una cadena vacía devuelva cadena vacía."""
    assert GraphBuilder.formatear_fecha("") == ""


def test_formatear_fecha_invalida(caplog):
    """Verifica que una fecha mal formada retorna cadena vacía y deja un warning."""
    with caplog.at_level(logging.WARNING, logger="analysis.graph_builder"):
        assert GraphBuilder.formatear_fecha("invalida") == ""
    assert "Fecha inválida" in caplog.text


def test_normalizar_provincia_quita_prefijo():
    """Verifica que se elimina el prefijo 'Diputado por' o 'Diputada por' de la provincia."""
    assert GraphBuilder.normalizar_provincia("Diputada por Cádiz") == "Cádiz"
    assert GraphBuilder.normalizar_provincia("Diputado por Lugo") == "Lugo"
    assert GraphBuilder.normalizar_provincia("Barcelona") == "Barcelona"
    assert GraphBuilder.normalizar_provincia("") == ""


@patch("analysis.graph_builder.GraphDatabase.driver")
def test_init_service_unavailable_logs_error(mock_driver_class, caplog):
    """
    Testea que se loguea un error y se relanza la excepción si Neo4j no está disponible al inicializar.
    """
    mock_driver_class.side_effect = ServiceUnavailable("Fallo de conexión")
    with caplog.at_level(logging.ERROR, logger="analysis.graph_builder"):
        with pytest.raises(ServiceUnavailable):
            GraphBuilder(uri="bolt://fake", user="neo4j", password="test", database="Congreso")
    assert "No se pudo conectar a Neo4j" in caplog.text


@patch("analysis.graph_builder.GraphDatabase.driver")
def test_crear_indices_ok(mock_driver_class, caplog):
    """Verifica que crear_indices loguea INFO si no hay errores."""
    mock_session = MagicMock()
    mock_session.run.side_effect = [None, None, None, None]  # Ningún error
    mock_driver = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_driver_class.return_value = mock_driver

    builder = GraphBuilder(uri="bolt://fake", user="neo4j", password="test", database="Congreso")

    with caplog.at_level(logging.INFO, logger="analysis.graph_builder"):
        builder.crear_indices()
        # Verifica que el log de info esté presente para al menos un constraint
        assert any("Constraint 'diputado_nombre_unico' verificado para Diputado.nombre" in r.getMessage()
                   for r in caplog.records)

@patch("analysis.graph_builder.GraphDatabase.driver")
def test_importar_grupos_columnas_incompletas(mock_driver_class):
    """Verifica que importar_grupos lanza ValueError si faltan columnas."""
    mock_driver = MagicMock()
    mock_driver_class.return_value = mock_driver
    builder = GraphBuilder(uri="bolt://fake", user="neo4j", password="test", database="Congreso")

    # DataFrame sin las columnas requeridas
    df = pd.DataFrame([{"foo": 1, "bar": 2}])
    with patch("pandas.read_csv", return_value=df):
        with pytest.raises(ValueError, match="Faltan columnas requeridas"):
            builder.importar_grupos("fake.csv", "15")

def test_normalizar_provincia_no_str():
    """Verifica que normalizar_provincia devuelve el argumento tal cual si no es string."""
    res = GraphBuilder.normalizar_provincia(1234)
    assert res == 1234
    res = GraphBuilder.normalizar_provincia(None)
    assert res is None


@patch("analysis.graph_builder.GraphDatabase.driver")
def test_importar_diputados_columnas_incompletas(mock_driver_class):
    """Verifica que importar_diputados lanza ValueError si faltan columnas requeridas."""
    mock_driver = MagicMock()
    mock_driver_class.return_value = mock_driver
    builder = GraphBuilder(uri="bolt://fake", user="neo4j", password="test", database="Congreso")

    # DataFrame SIN columna "legislatura"
    df = pd.DataFrame([{
        "nombre": "Diputado X",
        "provincia": "Lugo",
        "sustituye_a": "",
        "fecha_alta_suplencia": "",
        "fecha_baja_suplencia": ""
        # Falta "legislatura"
    }])
    with patch("pandas.read_csv", return_value=df):
        with pytest.raises(ValueError, match="Faltan columnas requeridas en el CSV"):
            builder.importar_diputados("fake.csv", "15")
