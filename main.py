# main.py

import argparse
from scraping.congreso_scraper import CongresoScraper
from scraping.scraper_diputados import DiputadosScraper
from scraping.scraper_grupos import GruposScraper
from analysis.graph_builder import GraphBuilder
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE
import logging
import os

logging.basicConfig(level=logging.INFO)


def configurar_logging(nombre_proceso):
    os.makedirs("logs", exist_ok=True)
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s [%(name)s] %(message)s',
        handlers=[
            logging.FileHandler(f"logs/{nombre_proceso}.log", mode="w", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )


def main():
    """
    Punto de entrada principal del sistema. Ejecuta distintos modos según el argumento --modo.
    """
    parser = argparse.ArgumentParser(description="Ejecutar scrapers o construcción del grafo del Congreso.")
    parser.add_argument(
        "--modo",
        choices=["plenos", "diputados", "grupos", "grafogrupos", "grafodiputados"],
        required=True,
        help="Selecciona el modo: 'plenos', 'diputados', 'grupos', 'grafogrupos', 'grafodiputados'"
    )
    parser.add_argument(
        "--legislatura",
        default="15",
        help="Número de legislatura a procesar (por defecto 15)"
    )
    args = parser.parse_args()

    # Determina el nombre del log según el modo
    log_name = args.modo
    configurar_logging(log_name)

    # Ruta al ejecutable de ChromeDriver (ajústala según tu sistema)
    CHROMEDRIVER_PATH = "C:/Tools/chromedriver/chromedriver.exe"
    csv_dir = f"csv/{args.legislatura}"
    os.makedirs(csv_dir, exist_ok=True)

    if args.modo == "plenos":
        OUTPUT_DIR = f"diarios_html/{args.legislatura}"
        scraper = CongresoScraper(driver_path=CHROMEDRIVER_PATH, output_dir=OUTPUT_DIR, legislatura=args.legislatura)
        scraper.descargar_plenos()

    elif args.modo == "diputados":
        OUTPUT_CSV = os.path.join(csv_dir, "diputados.csv")
        scraper = DiputadosScraper(driver_path=CHROMEDRIVER_PATH, output_csv=OUTPUT_CSV, legislatura=args.legislatura)
        scraper.ejecutar()

    elif args.modo == "grupos":
        OUTPUT_CSV = os.path.join(csv_dir, "grupos.csv")
        scraper = GruposScraper(driver_path=CHROMEDRIVER_PATH, legislatura=args.legislatura)
        scraper.ejecutar(output_csv=OUTPUT_CSV)

    elif args.modo == "grafogrupos":
        CSV_PATH = os.path.join(csv_dir, "grupos.csv")
        builder = GraphBuilder(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE)
        builder.importar_grupos(CSV_PATH, args.legislatura)
        builder.close()

    elif args.modo == "grafodiputados":
        CSV_PATH = os.path.join(csv_dir, "diputados.csv")
        builder = GraphBuilder(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE)
        builder.importar_diputados(CSV_PATH, args.legislatura)
        builder.close()


if __name__ == "__main__":
    main()
