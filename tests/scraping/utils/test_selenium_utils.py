# test/utils/test_selenium_utils.py

import pytest
from unittest.mock import mock_open, patch, MagicMock
from selenium.webdriver.common.by import By
from scraping.utils import selenium_utils as utils


@pytest.fixture
def mock_driver():
    return MagicMock()


@pytest.fixture
def mock_wait():
    return MagicMock()


# Test para comprobar que iniciar_driver devuelve una tupla con ChromeDriver y WebDriverWait
@patch("scraping.utils.selenium_utils.webdriver.Chrome")
@patch("scraping.utils.selenium_utils.Service")
@patch("scraping.utils.selenium_utils.Options")
@patch("scraping.utils.selenium_utils.WebDriverWait")
def test_iniciar_driver(mock_wait, mock_options, mock_service, mock_chrome):
    # Mocks individuales
    mock_instance_options = MagicMock()
    mock_options.return_value = mock_instance_options

    mock_driver = MagicMock()
    mock_chrome.return_value = mock_driver
    mock_wait_instance = MagicMock()
    mock_wait.return_value = mock_wait_instance

    # Ejecutar
    driver, wait = utils.iniciar_driver("fake/path/to/chromedriver", headless=True)

    # Comprobaciones
    mock_options.assert_called_once()
    mock_instance_options.add_argument.assert_any_call("--headless=new")
    mock_instance_options.add_argument.assert_any_call("--start-maximized")

    mock_service.assert_called_once_with("fake/path/to/chromedriver")
    mock_chrome.assert_called_once()
    mock_wait.assert_called_once_with(mock_driver, 20)

    # Verifica que la función retorna el driver y el wait esperados
    assert driver == mock_driver
    assert wait == mock_wait_instance


# Test para verificar que se selecciona correctamente una opción por valor en un <select>.
def test_seleccionar_opcion_por_valor_ok():
    mock_select = MagicMock()
    with patch("scraping.utils.selenium_utils.Select") as mock_sel:
        mock_sel.return_value = mock_select
        assert utils.seleccionar_opcion_por_valor("element", "valor") is True
        mock_select.select_by_value.assert_called_once_with("valor")


# Test para manejar errores al seleccionar un valor inexistente en el <select>.
def test_seleccionar_opcion_por_valor_fail():
    with patch("scraping.utils.selenium_utils.Select", side_effect=Exception("fail")):
        assert not utils.seleccionar_opcion_por_valor("element", "valor")


# Test para aceptar cookies si el botón es clicable.
def test_aceptar_cookies_ok(mock_driver, mock_wait):
    clickable = MagicMock()
    mock_wait.until.return_value = clickable
    utils.aceptar_cookies(mock_driver, mock_wait)
    clickable.click.assert_called_once()


# Test para manejar la ausencia del banner de cookies sin lanzar excepción.
def test_aceptar_cookies_fail(mock_driver, mock_wait):
    mock_wait.until.side_effect = Exception("No cookies")
    utils.aceptar_cookies(mock_driver, mock_wait)  # Solo imprime mensaje


# Test para comprobar que se espera a que desaparezca el spinner de carga.
def test_esperar_spinner(mock_wait):
    utils.esperar_spinner(mock_wait)
    mock_wait.until.assert_called_once()


# Test para verificar que se espera correctamente a que una tabla esté cargada.
def test_esperar_tabla_cargada(mock_wait):
    utils.esperar_tabla_cargada(mock_wait, "selector")
    assert mock_wait.until.call_count == 1
    args, kwargs = mock_wait.until.call_args
    assert isinstance(args[0], type(utils.EC.presence_of_element_located((By.CSS_SELECTOR, "selector"))))


# Test para hacer clic en un elemento usando JavaScript una vez que es clicable.
def test_hacer_click_esperando(mock_driver, mock_wait):
    elemento = MagicMock()
    mock_wait.until.return_value = elemento
    utils.hacer_click_esperando(mock_driver, mock_wait, By.ID, "selector")
    mock_driver.execute_script.assert_called_once_with("arguments[0].click();", elemento)


# Test para detectar correctamente que es la última página del paginador.
def test_es_ultima_pagina_true(mock_driver):
    mock_driver.find_element.return_value.text = "Resultados 1 a 10 de 10"
    assert utils.es_ultima_pagina(mock_driver, "element_id") is True


# Test para detectar correctamente que NO es la última página del paginador.
def test_es_ultima_pagina_false(mock_driver):
    mock_driver.find_element.return_value.text = "Resultados 1 a 10 de 100"
    assert utils.es_ultima_pagina(mock_driver, "element_id") is False


# Test para manejar errores al intentar leer el texto del paginador.
def test_es_ultima_pagina_error(mock_driver):
    mock_driver.find_element.side_effect = Exception("fail")
    assert utils.es_ultima_pagina(mock_driver, "element_id") is False


# Test para simular correctamente el avance de página cuando cambia el rango de resultados.
@patch("time.sleep", return_value=None)
def test_click_siguiente_pagina_success(mock_sleep, mock_driver, mock_wait):
    # Simula el rango antes del clic
    paginador_antes = MagicMock()
    paginador_antes.text = "Resultados 1 a 10 de 100"

    # Simula el botón de siguiente
    boton = MagicMock()

    # Simula el rango después del clic
    paginador_despues = MagicMock()
    paginador_despues.text = "Resultados 11 a 20 de 100"

    # Define el comportamiento encadenado de find_element
    mock_driver.find_element.side_effect = [
        paginador_antes,  # lectura inicial del rango
        boton,  # clic en botón siguiente
        paginador_despues  # nueva lectura tras clic
    ]

    mock_wait.until.return_value = True

    result = utils.click_siguiente_pagina(
        driver=mock_driver,
        wait=mock_wait,
        xpath_siguiente="//xpath",
        by_tabla=By.CSS_SELECTOR,
        selector_tabla="tabla",
        id_paginador="id_del_paginador"
    )

    assert result is True


# Test para simular error al hacer clic en el botón de paginación.
@patch("time.sleep", return_value=None)
def test_click_siguiente_pagina_fail_click(mock_sleep, mock_driver, mock_wait):
    mock_driver.find_element.side_effect = Exception("click fail")
    assert not utils.click_siguiente_pagina(mock_driver, mock_wait, "//xpath", By.CSS_SELECTOR, "tabla")


# Test para manejar correctamente el caso en que no se puede leer el rango anterior pero sigue funcionando.
@patch("time.sleep", return_value=None)
def test_click_siguiente_pagina_fallback(mock_sleep, mock_driver, mock_wait):
    # Simula que no se puede leer el rango anterior, pero que luego sí encuentra el botón de "siguiente"
    boton = MagicMock()
    paginador = MagicMock(text="Resultados 11 a 20 de 100")

    mock_driver.find_element.side_effect = [
        Exception("range fail"),  # intento leer el rango anterior
        boton,  # clic botón siguiente
        paginador,  # nuevo rango de resultados
    ]
    mock_wait.until.return_value = True

    result = utils.click_siguiente_pagina(mock_driver, mock_wait, "//xpath", By.CSS_SELECTOR, "tabla", "element_id")
    assert result is True


# Test para extraer correctamente el rango de resultados desde el paginador.
def test_get_rango_resultados_ok(mock_driver):
    mock_driver.find_element.return_value.text = "Resultados 1 a 20 de 50"
    assert utils.get_rango_resultados(mock_driver, "element_id") == (20, 50)


# Test para manejar errores al leer el paginador sin romper el flujo.
def test_get_rango_resultados_fail(mock_driver):
    mock_driver.find_element.side_effect = Exception("fail")
    assert utils.get_rango_resultados(mock_driver, "element_id") == (None, None)


# Test para guardar correctamente el contenido HTML de un selector en un archivo.
@patch("scraping.utils.selenium_utils.BeautifulSoup")
@patch("builtins.open", new_callable=mock_open)
def test_guardar_html_contenido_ok(mock_open_fn, mock_bs, mock_driver, mock_wait):
    """
    Test para comprobar que guardar_html_contenido guarda correctamente
    el contenido HTML en un archivo si el selector existe.
    """
    # Simula que el contenido existe
    contenido_html = "<section>Contenido</section>"
    mock_driver.page_source = "<html></html>"
    mock_wait.until.return_value = True
    mock_soup = MagicMock()
    mock_soup.select_one.return_value = contenido_html
    mock_bs.return_value = mock_soup

    # Ejecutar función
    result = utils.guardar_html_contenido(mock_driver, mock_wait, "selector", "archivo.html")

    # Comprobaciones
    assert result is True
    mock_open_fn.assert_called_once_with("archivo.html", "w", encoding="utf-8")
    mock_open_fn().write.assert_called_once_with(contenido_html)


# Test para comprobar que si no se encuentra el contenido, no se guarda archivo.
@patch("scraping.utils.selenium_utils.BeautifulSoup")
def test_guardar_html_contenido_fail(mock_bs, mock_driver, mock_wait):
    mock_bs.return_value.select_one.return_value = None
    mock_driver.page_source = "<html></html>"
    mock_wait.until.return_value = True
    assert not utils.guardar_html_contenido(mock_driver, mock_wait, "selector", "archivo.html")


@patch("time.sleep", return_value=None)
def test_click_siguiente_pagina_detecta_cambio_rango(mock_sleep, mock_driver, mock_wait):
    paginador_antes = MagicMock()
    paginador_antes.text = "Resultados 1 a 10 de 100"

    boton = MagicMock()

    paginador_despues = MagicMock()
    paginador_despues.text = "Resultados 11 a 20 de 100"

    mock_driver.find_element.side_effect = [
        paginador_antes,  # rango anterior
        boton,  # clic
        paginador_despues  # nuevo rango
    ]
    mock_wait.until.return_value = True

    result = utils.click_siguiente_pagina(
        mock_driver, mock_wait,
        xpath_siguiente="//xpath",
        by_tabla=By.CSS_SELECTOR,
        selector_tabla="tabla",
        id_paginador="id_del_paginador"
    )
    assert result is True


@patch("time.sleep", return_value=None)
def test_click_siguiente_pagina_lanza_excepcion_final(mock_sleep, mock_driver, mock_wait):
    paginador = MagicMock()
    paginador.text = "Resultados 1 a 10 de 100"
    boton = MagicMock()

    mock_driver.find_element.side_effect = [
        paginador,  # rango antes
        boton  # botón siguiente
    ]
    mock_driver.execute_script.return_value = None
    mock_wait.until.side_effect = Exception("fallo inesperado")

    result = utils.click_siguiente_pagina(
        mock_driver, mock_wait,
        xpath_siguiente="//xpath",
        by_tabla=By.CSS_SELECTOR,
        selector_tabla="tabla",
        id_paginador="id_del_paginador"
    )
    assert result is False


@patch("scraping.utils.selenium_utils.BeautifulSoup")
@patch("builtins.open", new_callable=mock_open)
def test_guardar_html_contenido_excepcion_en_open(mock_open_fn, mock_bs, mock_driver, mock_wait):
    mock_driver.page_source = "<html></html>"
    mock_wait.until.return_value = True

    contenido = "<div>contenido</div>"
    mock_bs.return_value.select_one.return_value = contenido

    mock_open_fn.side_effect = Exception("no se pudo abrir archivo")

    result = utils.guardar_html_contenido(mock_driver, mock_wait, "selector", "archivo.html")
    assert result is False


@patch("time.sleep", return_value=None)
def test_click_siguiente_pagina_ejecuta_break(mock_sleep, mock_driver, mock_wait):
    """
    Fuerza la ejecución del 'break' en click_siguiente_pagina simulando un cambio real de rango.
    """

    # Antes: grupo(1) == "1"
    paginador_antes = MagicMock()
    paginador_antes.text = "Resultados 1 a 10 de 100"

    # Botón de siguiente
    boton = MagicMock()

    # Después: grupo(1) == "2" → debe disparar el break
    paginador_despues = MagicMock()
    paginador_despues.text = "Resultados 2 a 20 de 100"

    mock_driver.find_element.side_effect = [
        paginador_antes,  # para obtener rango anterior
        boton,            # clic siguiente
        paginador_despues  # nuevo texto tras clic
    ]

    # Simula que la tabla se carga correctamente
    mock_wait.until.return_value = True

    result = utils.click_siguiente_pagina(
        driver=mock_driver,
        wait=mock_wait,
        xpath_siguiente="//xpath",
        by_tabla=By.CSS_SELECTOR,
        selector_tabla="tabla",
        id_paginador="id_del_paginador"
    )

    assert result is True
