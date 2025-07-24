# main.py

from scraping.congreso_scraper import CongresoScraper

if __name__ == "__main__":
    CHROMEDRIVER_PATH = "C:/Tools/chromedriver/chromedriver.exe"
    OUTPUT_DIR = "diarios_html"

    scraper = CongresoScraper(driver_path=CHROMEDRIVER_PATH, output_dir=OUTPUT_DIR)
    scraper.descargar_plenos()