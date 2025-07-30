
# main.py

import argparse
from scraping.congreso_scraper import CongresoScraper
from scraping.scraper_diputados import DiputadosScraper
from scraping.scraper_grupos import GruposScraper
from scraping.scraper_ministros import MinistrosScraper

def main():
    parser = argparse.ArgumentParser(description="Ejecutar scraper del Congreso.")
    parser.add_argument(
        "--modo",
        choices=["plenos", "diputados", "grupos"],
        required=True,
        help="Selecciona el scraper a ejecutar: 'plenos', 'diputados', 'grupos'"
    )
    args = parser.parse_args()

    CHROMEDRIVER_PATH = "C:/Tools/chromedriver/chromedriver.exe"

    if args.modo == "plenos":
        OUTPUT_DIR = "diarios_html"
        scraper = CongresoScraper(driver_path=CHROMEDRIVER_PATH, output_dir=OUTPUT_DIR, legislatura="15")
        scraper.descargar_plenos()
    elif args.modo == "diputados":
        OUTPUT_CSV = "diputados.csv"
        scraper = DiputadosScraper(driver_path=CHROMEDRIVER_PATH, output_csv=OUTPUT_CSV, legislatura="15")
        scraper.ejecutar()
    elif args.modo == "grupos":
        OUTPUT_CSV = "grupos.csv"
        scraper = GruposScraper(driver_path=CHROMEDRIVER_PATH, legislatura="15")
        scraper.ejecutar(output_csv=OUTPUT_CSV)

if __name__ == "__main__":
    main()
