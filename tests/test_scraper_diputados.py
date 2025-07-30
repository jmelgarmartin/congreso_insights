import os
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from scraping.scraper_diputados import DiputadosScraper


@pytest.fixture
def scraper():
    return DiputadosScraper(driver_path="dummy_path", output_csv="dummy.csv", legislatura="15")


def test_init_driver(scraper):
    with patch("scraping.scraper_diputados.iniciar_driver") as mock_init:
        mock_init.return_value = ("driver", "wait")
        scraper._init_driver()
        assert scraper.driver == "driver"
        assert scraper.wait == "wait"


def test_extraer_info_diputado(scraper):
    fila = MagicMock()
    celdas = [MagicMock(text="Grupo X"), MagicMock(text="Provincia Y")]
    fila.find_elements.return_value = celdas
    fila.find_element.return_value.text = "Nombre del Diputado"

    resultado = scraper._extraer_info_diputado(fila)
    assert resultado == {
        "nombre": "Nombre del Diputado",
        "grupo_actual": "Grupo X",
        "provincia": "Provincia Y"
    }


def test_procesar_pagina(scraper):
    fila_mock = MagicMock()
    fila_mock.find_element.return_value.text = "Nombre"
    fila_mock.find_elements.return_value = [MagicMock(text="Grupo"), MagicMock(text="Provincia")]
    scraper.driver = MagicMock()
    scraper.wait = MagicMock()
    scraper.driver.find_elements.return_value = [fila_mock, fila_mock]

    with patch.object(scraper, "_extraer_info_diputado") as mock_extraer:
        mock_extraer.return_value = {
            "nombre": "Nombre",
            "grupo_actual": "Grupo",
            "provincia": "Provincia"
        }
        resultados = scraper._procesar_pagina()
        assert len(resultados) == 2
        assert resultados[0]["nombre"] == "Nombre"


def test_es_ultima_pagina_true(scraper):
    scraper.driver = MagicMock()
    scraper.driver.find_element.return_value.text = "Resultados 1 a 10 de 10"
    assert scraper._es_ultima_pagina() is True


def test_es_ultima_pagina_false(scraper):
    scraper.driver = MagicMock()
    scraper.driver.find_element.return_value.text = "Resultados 1 a 10 de 20"
    assert scraper._es_ultima_pagina() is False


def test_es_ultima_pagina_raises(scraper):
    scraper.driver = MagicMock()
    scraper.driver.find_element.side_effect = Exception("fallo")
    assert scraper._es_ultima_pagina() is False


@patch("scraping.scraper_diputados.esperar_spinner")
@patch("scraping.scraper_diputados.esperar_tabla_cargada")
@patch("scraping.scraper_diputados.hacer_click_esperando")
@patch("scraping.scraper_diputados.seleccionar_opcion_por_valor")
@patch("scraping.scraper_diputados.aceptar_cookies")
def test_buscar_diputados(mock_cookies, mock_seleccionar, mock_click, mock_spinner, mock_tabla, scraper):
    scraper.driver = MagicMock()
    scraper.wait = MagicMock()

    element_legislatura = MagicMock()
    element_legislatura.get_attribute.return_value = "14"  # fuerza cambio
    scraper.driver.find_element.side_effect = [
        element_legislatura,  # _diputadomodule_legislatura
        MagicMock(),  # _diputadomodule_tipo
        MagicMock()  # _diputadomodule_searchButtonDiputadosForm
    ]

    scraper.wait.until.return_value = True

    scraper._buscar_diputados()
    assert mock_seleccionar.call_count >= 2
    assert mock_click.called
    assert mock_spinner.called
    assert mock_tabla.called


@patch("scraping.scraper_diputados.esperar_spinner")
@patch("scraping.scraper_diputados.esperar_tabla_cargada")
def test_siguiente_pagina_true(mock_tabla, mock_spinner, scraper):
    scraper.driver = MagicMock()
    scraper.wait = MagicMock()
    scraper._es_ultima_pagina = MagicMock(return_value=False)

    siguiente_btn = MagicMock()
    scraper.wait.until.return_value = siguiente_btn

    assert scraper._siguiente_pagina() is True
    assert siguiente_btn.click.called or scraper.driver.execute_script.called


@patch("scraping.scraper_diputados.esperar_spinner")
@patch("scraping.scraper_diputados.esperar_tabla_cargada")
def test_siguiente_pagina_false(mock_tabla, mock_spinner, scraper):
    scraper.driver = MagicMock()
    scraper.wait = MagicMock()
    scraper._es_ultima_pagina = MagicMock(return_value=True)

    assert scraper._siguiente_pagina() is False


@patch("scraping.scraper_diputados.esperar_spinner")
@patch("scraping.scraper_diputados.esperar_tabla_cargada")
def test_siguiente_pagina_exception(mock_tabla, mock_spinner, scraper):
    scraper.driver = MagicMock()
    scraper.wait = MagicMock()
    scraper._es_ultima_pagina = MagicMock(return_value=False)
    scraper.wait.until.side_effect = Exception("fallo en wait")
    assert scraper._siguiente_pagina() is False


def test_guardar_csv(tmp_path, scraper):
    df = pd.DataFrame([{"nombre": "Diputado", "grupo_actual": "Grupo", "provincia": "Provincia"}])
    output = tmp_path / "diputados.csv"
    scraper.output_csv = str(output)
    scraper.guardar_csv(df)
    assert output.exists()
    contenido = output.read_text(encoding="utf-8")
    assert "Diputado" in contenido


@patch("scraping.scraper_diputados.EnriquecedorSuplencias")
@patch("scraping.scraper_diputados.pd.DataFrame.to_csv")
@patch.object(DiputadosScraper, "_siguiente_pagina", side_effect=[True, False])
@patch.object(DiputadosScraper, "_procesar_pagina",
              return_value=[{"nombre": "Diputado", "grupo_actual": "Grupo", "provincia": "Provincia"}])
@patch.object(DiputadosScraper, "_buscar_diputados")
@patch.object(DiputadosScraper, "_init_driver")
def test_ejecutar(
        mock_init,
        mock_buscar,
        mock_procesar,
        mock_siguiente,
        mock_csv,
        mock_enriquecedor,
        scraper
):
    mock_enriquecedor.return_value.enriquecer_df_diputados.return_value = pd.DataFrame([
        {"nombre": "Diputado", "grupo_actual": "Grupo", "provincia": "Provincia"}
    ])

    scraper.driver = MagicMock()

    scraper.ejecutar()

    assert mock_init.called
    assert mock_buscar.called
    assert mock_procesar.call_count == 2
    assert mock_siguiente.call_count == 2
    assert mock_csv.called

