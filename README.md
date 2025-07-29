# Congreso Insights

**Congreso Insights** es una herramienta modular que permite automatizar la descarga, análisis y visualización de datos parlamentarios del Congreso de los Diputados de España.

---

## 📁 Estructura del proyecto

```text
congreso_insights/
│
├── main.py                         # Script principal de ejecución
├── README.md                       # Documentación del proyecto
├── requirements.txt                # Dependencias necesarias
├── .gitignore                      # Archivos excluidos del control de versiones
├── diputados.csv                   # Salida: datos de diputados y suplencias
├── grupos.csv                      # Salida: composición de grupos parlamentarios
├── diarios_html/                   # HTMLs descargados de los diarios del Congreso
│
├── analysis/                       # Módulo de análisis de discursos
│   ├── __init__.py
│   └── graph_builder.py            # Construcción y análisis de grafos en Neo4j
│
├── scraping/                       # Módulo de scraping web
│   ├── __init__.py
│   ├── congreso_scraper.py         # Scraper de diarios de sesiones (plenos)
│   ├── scraper_diputados.py        # Scraper del listado de diputados
│   ├── scraper_grupos.py           # Scraper de composición de grupos parlamentarios
│   ├── enriquecedor_suplencias.py  # Obtención de fechas y relaciones de suplencias
│   └── utils/                      # Utilidades compartidas para Selenium
│       ├── __init__.py
│       └── selenium_utils.py       # Inicialización y funciones auxiliares
│
├── test/                           # Tests unitarios del proyecto
│   ├── __init__.py
│   ├── test_congreso_scraper.py    # Tests del scraping de diarios
│   ├── test_graph_builder.py       # Tests del análisis en Neo4j
│   └── test_output/                # Carpeta temporal de salida de tests
```

---

## 🧩 Componentes

- `scraping/`: Descarga automatizada de datos desde el portal del Congreso.
- `analysis/`: Análisis semántico y de redes sobre discursos usando Neo4j y GDS.
- `test/`: Validación del correcto funcionamiento de los scrapers y análisis.
- `diarios_html/`: Carpeta donde se almacenan los HTML de sesiones plenarias.
- `diputados.csv` y `grupos.csv`: Resultados estructurados de scraping y análisis de parlamentarios.

---

## ▶️ Uso

```bash
python main.py (opción)
```

Por ejemplo:

```bash
python main.py analizar
```

---

## 🧰 Requisitos

- Python `3.8+`
- ChromeDriver (compatible con tu versión de Chrome)
- Neo4j (4.x o superior con GDS instalado)

---

## 📦 Instalación

```bash
pip install -r requirements.txt
```
