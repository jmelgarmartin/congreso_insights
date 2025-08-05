# test/scraping/test_congreso_scraper.py

import pytest
from unittest.mock import patch, MagicMock
from scraping.congreso_scraper import CongresoScraper


@pytest.fixture
def scraper():
    """
    Fixture que devuelve una instancia del scraper con rutas falsas.
    """
    return CongresoScraper(driver_path="fake/path", output_dir="fake/output", legislatura="15")


# Test para verificar que el constructor asigna correctamente los atributos
def test_congreso_scraper_init(scraper):
    assert scraper.url == "https://www.congreso.es/busqueda-de-publicaciones"
    assert scraper.driver_path == "fake/path"
    assert scraper.output_dir == "fake/output"
    assert scraper.legislatura == "15"


# Test para verificar que _apply_filters ejecuta correctamente la lógica de filtrado
@patch("scraping.congreso_scraper.hacer_click_esperando")
@patch("scraping.congreso_scraper.seleccionar_opcion_por_valor")
@patch("scraping.congreso_scraper.Select")
@patch("scraping.congreso_scraper.EC")
def test_apply_filters_ok(mock_ec, mock_select, mock_sel_valor, mock_click, scraper):
    scraper.driver = MagicMock()
    scraper.wait = MagicMock()
    scraper.driver.find_element.return_value = MagicMock()
    mock_ec.presence_of_element_located.return_value = True
    scraper.wait.until.return_value = True

    scraper._apply_filters()

    assert scraper.driver.find_element.call_count >= 3
    mock_sel_valor.assert_called()
    mock_click.assert_called_once()


# Test para comprobar que _apply_filters lanza excepción y cierra el driver si algo falla
@patch("scraping.congreso_scraper.Select", side_effect=Exception("fallo"))
def test_apply_filters_exception(mock_select, scraper):
    scraper.driver = MagicMock()
    scraper.wait = MagicMock()
    scraper.driver.quit = MagicMock()
    scraper.wait.until.return_value = True

    with pytest.raises(Exception):
        scraper._apply_filters()

    scraper.driver.quit.assert_called_once()


# Test que verifica que _procesar_fila guarda un archivo nuevo correctamente
@patch("scraping.congreso_scraper.guardar_html_contenido", return_value=True)
@patch("os.path.exists", return_value=False)
def test_procesar_fila_guarda(mock_exists, mock_guardar, scraper):
    fila = MagicMock()
    td = MagicMock(text="DSCD-15-PL-1")
    fila.find_elements.return_value = [td]

    enlace = MagicMock()
    enlace.get_attribute.return_value = "http://fake.link"
    fila.find_element.return_value = enlace

    scraper.driver = MagicMock()
    scraper.driver.window_handles = ["main", "popup"]
    scraper.driver.switch_to.window = MagicMock()
    scraper.wait = MagicMock()

    result = scraper._procesar_fila(fila)

    assert result is True
    mock_guardar.assert_called_once()


# Test que verifica que _procesar_fila devuelve False si el archivo ya existe
@patch("os.path.exists", return_value=True)
def test_procesar_fila_ya_existe(mock_exists, scraper):
    fila = MagicMock()
    fila.find_elements.return_value = [MagicMock(text="DSCD-15-PL-1")]
    result = scraper._procesar_fila(fila)
    assert result is False


# Test que verifica que _procesar_fila devuelve False si no es un pleno
def test_procesar_fila_no_es_pleno(scraper):
    fila = MagicMock()
    fila.find_elements.return_value = [MagicMock(text="DSCD-15-CM-1")]
    result = scraper._procesar_fila(fila)
    assert result is False


# Test para descargar plenos con una sola página y sin errores
@patch("scraping.congreso_scraper.click_siguiente_pagina", return_value=False)
@patch("scraping.congreso_scraper.get_rango_resultados", return_value=(10, 10))
@patch("scraping.congreso_scraper.CongresoScraper._procesar_fila", return_value=True)
@patch("scraping.congreso_scraper.CongresoScraper._apply_filters")
@patch("scraping.congreso_scraper.aceptar_cookies")
@patch("scraping.congreso_scraper.iniciar_driver")
def test_descargar_plenos_simple(mock_iniciar, mock_cookies, mock_filtros, mock_procesar, mock_rangos, mock_click,
                                 scraper):
    driver = MagicMock()
    wait = MagicMock()
    driver.find_elements.return_value = [MagicMock(), MagicMock()]
    mock_iniciar.return_value = (driver, wait)

    scraper.descargar_plenos()

    mock_filtros.assert_called_once()
    assert mock_procesar.call_count >= 1
    driver.quit.assert_called_once()


@patch("scraping.congreso_scraper.guardar_html_contenido", return_value=False)
@patch("os.path.exists", return_value=False)
def test_procesar_fila_sin_contenido(mock_exists, mock_guardar, scraper):
    """
    Test para comprobar el mensaje cuando no se encuentra contenido HTML en la página.
    """
    fila = MagicMock()
    td = MagicMock(text="DSCD-15-PL-1")
    fila.find_elements.return_value = [td]

    enlace = MagicMock()
    enlace.get_attribute.return_value = "http://fake.link"
    fila.find_element.return_value = enlace

    scraper.driver = MagicMock()
    scraper.driver.window_handles = ["main", "popup"]
    scraper.driver.switch_to.window = MagicMock()
    scraper.wait = MagicMock()

    result = scraper._procesar_fila(fila)

    assert result is True  # el método sigue devolviendo True aunque no haya contenido
    mock_guardar.assert_called_once()


@patch("scraping.congreso_scraper.click_siguiente_pagina", return_value=False)
@patch("scraping.congreso_scraper.get_rango_resultados", return_value=(10, 10))
@patch("scraping.congreso_scraper.CongresoScraper._procesar_fila", side_effect=Exception("fallo inesperado"))
@patch("scraping.congreso_scraper.CongresoScraper._apply_filters")
@patch("scraping.congreso_scraper.aceptar_cookies")
@patch("scraping.congreso_scraper.iniciar_driver")
def test_descargar_plenos_error_en_fila(mock_iniciar, mock_cookies, mock_apply, mock_procesar, mock_rango, mock_click,
                                        scraper):
    """
    Test para cubrir la excepción lanzada en _procesar_fila dentro del bucle de filas.
    """
    mock_driver = MagicMock()
    mock_wait = MagicMock()
    mock_driver.find_elements.return_value = [MagicMock()]
    mock_iniciar.return_value = (mock_driver, mock_wait)

    scraper.descargar_plenos()

    assert mock_procesar.call_count >= 3  # intenta 3 veces
    mock_driver.quit.assert_called_once()


@patch("scraping.congreso_scraper.hacer_click_esperando")
@patch("scraping.congreso_scraper.seleccionar_opcion_por_valor")
@patch("scraping.congreso_scraper.Select")
@patch("scraping.congreso_scraper.EC")
def test_apply_filters_prints(mock_ec, mock_select, mock_sel_valor, mock_click, scraper):
    """
    Test para cubrir los prints de filtros aplicados y resultados cargados.
    """
    scraper.driver = MagicMock()
    scraper.wait = MagicMock()
    scraper.driver.find_element.return_value = MagicMock()

    # Simula que ambos wait.until funcionan
    scraper.wait.until.side_effect = [True, True]
    mock_ec.presence_of_element_located.return_value = MagicMock()

    scraper._apply_filters()

    assert mock_click.called
    assert mock_sel_valor.call_count == 2


@patch("scraping.congreso_scraper.click_siguiente_pagina", return_value=True)
@patch("scraping.congreso_scraper.get_rango_resultados", return_value=(100, 100))
@patch("scraping.congreso_scraper.CongresoScraper._procesar_fila", return_value=True)
@patch("scraping.congreso_scraper.CongresoScraper._apply_filters")
@patch("scraping.congreso_scraper.aceptar_cookies")
@patch("scraping.congreso_scraper.iniciar_driver")
def test_descargar_plenos_ultima_pagina(mock_iniciar, mock_cookies, mock_filtros, mock_procesar, mock_rango, mock_click,
                                        scraper):
    """
    Test para cubrir el print de 'Última página detectada.' al alcanzar el final de resultados.
    """
    mock_driver = MagicMock()
    mock_wait = MagicMock()
    mock_driver.find_elements.return_value = [MagicMock()]
    mock_iniciar.return_value = (mock_driver, mock_wait)

    scraper.descargar_plenos()

    mock_rango.assert_called_once()
    mock_driver.quit.assert_called_once()


@patch("scraping.congreso_scraper.click_siguiente_pagina", return_value=False)
@patch("scraping.congreso_scraper.get_rango_resultados", return_value=(10, 100))
@patch("scraping.congreso_scraper.CongresoScraper._procesar_fila", return_value=True)
@patch("scraping.congreso_scraper.CongresoScraper._apply_filters")
@patch("scraping.congreso_scraper.aceptar_cookies")
@patch("scraping.congreso_scraper.iniciar_driver")
def test_descargar_plenos_no_hay_mas_paginas(mock_iniciar, mock_cookies, mock_filtros, mock_procesar, mock_rango,
                                             mock_click, scraper):
    """
    Test para cubrir el print de 'No hay más páginas.' cuando click_siguiente_pagina devuelve False.
    """
    mock_driver = MagicMock()
    mock_wait = MagicMock()
    mock_driver.find_elements.return_value = [MagicMock()]
    mock_iniciar.return_value = (mock_driver, mock_wait)

    scraper.descargar_plenos()

    mock_click.assert_called_once()
    mock_driver.quit.assert_called_once()


@patch("scraping.congreso_scraper.hacer_click_esperando")
@patch("scraping.congreso_scraper.seleccionar_opcion_por_valor")
@patch("scraping.congreso_scraper.Select")
@patch("scraping.congreso_scraper.EC")
def test_apply_filters_cobertura_final(mock_ec, mock_select, mock_sel_valor, mock_click, scraper, capsys):
    """
    Test para cubrir los prints 'Aplicando filtros...' y 'Resultados cargados.'
    en el método _apply_filters().
    """
    # Configura mocks
    scraper.driver = MagicMock()
    scraper.wait = MagicMock()
    scraper.driver.find_element.return_value = MagicMock()

    # Simula que los dos `until` se ejecutan correctamente
    scraper.wait.until.side_effect = [True, True]
    mock_ec.presence_of_element_located.return_value = MagicMock()

    # Ejecutar
    scraper._apply_filters()

    # Captura y verifica los prints
    captured = capsys.readouterr()
    assert "Aplicando filtros..." in captured.out
    assert "Resultados cargados." in captured.out


@patch("scraping.congreso_scraper.iniciar_driver")
@patch("scraping.congreso_scraper.get_rango_resultados")
@patch("scraping.congreso_scraper.click_siguiente_pagina", return_value=False)
@patch("scraping.congreso_scraper.guardar_html_contenido", return_value=True)
@patch("scraping.congreso_scraper.hacer_click_esperando")
@patch("scraping.congreso_scraper.seleccionar_opcion_por_valor")
@patch("scraping.congreso_scraper.Select")
@patch("scraping.congreso_scraper.EC")
def test_descargar_plenos_cobertura_final(
    mock_ec, mock_select, mock_sel_valor, mock_click, mock_guardar, mock_next, mock_rango, mock_iniciar_driver, scraper
):
    """
    Test para cubrir el 'if i >= len(filas_actualizadas)' y 'pagina += 1'
    en descargar_plenos().
    """
    # Preparamos mocks del driver y el wait
    driver_mock = MagicMock()
    wait_mock = MagicMock()
    mock_iniciar_driver.return_value = (driver_mock, wait_mock)

    scraper.driver, scraper.wait = driver_mock, wait_mock

    # Fila simulada
    fila = MagicMock()
    driver_mock.find_elements.side_effect = [
        [fila],  # filas iniciales
        []       # filas_actualizadas vacías → se cumple i >= len()
    ]

    wait_mock.until.return_value = True
    mock_rango.return_value = (1, 100)

    scraper._apply_filters = MagicMock()
    scraper._procesar_fila = MagicMock(return_value=False)

    scraper.descargar_plenos()

    # Afirmación básica de finalización
    assert driver_mock.quit.called


@patch("scraping.congreso_scraper.iniciar_driver")
@patch("scraping.congreso_scraper.get_rango_resultados")
@patch("scraping.congreso_scraper.click_siguiente_pagina", side_effect=[True, False])
@patch("scraping.congreso_scraper.guardar_html_contenido", return_value=True)
@patch("scraping.congreso_scraper.hacer_click_esperando")
@patch("scraping.congreso_scraper.seleccionar_opcion_por_valor")
@patch("scraping.congreso_scraper.Select")
@patch("scraping.congreso_scraper.EC")
def test_descargar_plenos_cobertura_pagina_incrementada(
    mock_ec, mock_select, mock_sel_valor, mock_click, mock_guardar, mock_next, mock_rango, mock_iniciar
):
    """
    Test para garantizar que se ejecuta la línea `pagina += 1`
    en el método descargar_plenos().
    """
    from scraping.congreso_scraper import CongresoScraper

    # Crear scraper con mocks
    scraper = CongresoScraper(driver_path="fake/path", output_dir="fake/output")

    # Simular driver y wait devueltos por iniciar_driver()
    mock_driver = MagicMock()
    mock_wait = MagicMock()
    mock_iniciar.return_value = (mock_driver, mock_wait)

    scraper._apply_filters = MagicMock()

    # Mock de filas encontradas
    fila = MagicMock()
    mock_driver.find_elements.side_effect = [
        [fila], [fila],  # Primera página
        [fila], [fila],  # Segunda página
        []               # Tercera iteración: se detiene
    ]

    mock_rango.return_value = (1, 100)
    mock_ec.presence_of_element_located.return_value = MagicMock()
    scraper._procesar_fila = MagicMock(return_value=False)

    # Ejecutar
    scraper.descargar_plenos()

    # Verificamos que hubo 2 iteraciones (y por tanto un incremento de página)
    assert scraper._procesar_fila.call_count == 2
    assert mock_next.call_count == 2  # click_siguiente_pagina fue llamado 2 veces