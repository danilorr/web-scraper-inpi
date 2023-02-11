# coding=utf8
import logging
from datetime import datetime
import pandas as pd
import numpy as np
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, WebDriverException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# noinspection PyArgumentEqualDefault
class WebScraper:

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        file_handler = logging.FileHandler(f'web-scraper-inpi/logs/web_scraper_{datetime.date(datetime.now())}.log', mode='w')
        self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.DEBUG)
        log_format = '%(name)s:%(levelname)s %(asctime)s -  %(message)s'
        formatter = logging.Formatter(log_format)
        file_handler.setFormatter(formatter)

        capa = DesiredCapabilities.CHROME
        capa["pageLoadStrategy"] = "none"
        self.chrome_options = Options()
        self.chrome_options.add_argument('window-size=400,800')
        # self.chrome_options.add_argument('--headless')
        self.driver_url = 'https://busca.inpi.gov.br/pePI/jsp/patentes/PatenteSearchAvancado.jsp'
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.chrome_options, desired_capabilities=capa)
        self.wait = WebDriverWait(self.driver, 60)

        pd.options.display.max_columns = 100
        pd.options.display.max_rows = 100
        pd.options.display.width = 0
        pd.options.display.max_colwidth = 200
        pd.options.display.float_format = '{:,.2f}'.format

        self.is_finished = False
        self.df = pd.DataFrame()
        self.first_feat_dict = {}
        self.second_feat_dict = {}
        self.third_feat_dict = {}
        self.full_dict = {}
        self.count = 0

    def start(self):
        self.open_browser()
        self.navigate_pages()
        self.scrape_site()
        self.close_browser()
        self.create_dataframe_csv()

    def open_browser(self):
        self.logger.debug('Opening Browser')
        try:
            self.driver.get(self.driver_url)
        except WebDriverException:
            self.logger.error(f'The website {self.driver_url} seems to be down')

    def click_continuar(self):
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[class="marcador"] > a')))
        self.driver.execute_script("window.stop();")
        self.driver.find_element(By.CSS_SELECTOR, '[class="marcador"] > a').click()

    def close_1st_tab(self):
        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])

    def click_patente(self):
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-mce-href="menu-servicos/patente"]')))
        self.driver.execute_script("window.stop();")
        self.driver.find_element(By.CSS_SELECTOR, '[data-mce-href="menu-servicos/patente"]').click()

    def click_pesquisa_avancada(self):
        self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Pesquisa Avançada')]")))
        self.driver.execute_script("window.stop();")
        self.driver.find_element(By.XPATH, "//*[contains(text(), 'Pesquisa Avançada')]").click()

    def fill_date_form(self):
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[class="accordion"]')))
        self.driver.execute_script("window.stop();")
        self.driver.find_element(By.CSS_SELECTOR, '[class="accordion"]').click()
        self.driver.find_element(By.CSS_SELECTOR, '[id="campoDataDeposito1"]').send_keys(
            Keys.ARROW_LEFT, Keys.ARROW_LEFT, Keys.ARROW_LEFT, Keys.ARROW_LEFT, Keys.ARROW_LEFT, Keys.ARROW_LEFT,
            Keys.ARROW_LEFT, Keys.ARROW_LEFT, Keys.ARROW_LEFT, Keys.ARROW_LEFT, '01012019')
        self.driver.find_element(By.CSS_SELECTOR, '[id="campoDataDeposito2"]').send_keys(
            Keys.ARROW_LEFT, Keys.ARROW_LEFT, Keys.ARROW_LEFT, Keys.ARROW_LEFT, Keys.ARROW_LEFT, Keys.ARROW_LEFT,
            Keys.ARROW_LEFT, Keys.ARROW_LEFT, Keys.ARROW_LEFT, Keys.ARROW_LEFT, '01122021')

    def change_reg_per_page(self):
        select = Select(self.driver.find_element(By.NAME, 'RegisterPerPage'))
        select.select_by_value('100')

    def click_pesquisar(self):
        self.driver.find_element(By.CSS_SELECTOR, '[value=" pesquisar » "]').click()

    def navigate_pages(self):
        self.click_continuar()
        self.close_1st_tab()
        self.click_patente()
        self.click_pesquisa_avancada()
        self.fill_date_form()
        self.change_reg_per_page()
        self.click_pesquisar()

    def scrape_cards(self):
        self.logger.debug('Scraping cards on new page')
        self.wait.until(EC.presence_of_element_located((By.ID, 'tituloContext')))
        table_id = self.driver.find_element(By.ID, 'tituloContext')
        self.cards = table_id.find_elements(By.TAG_NAME, "tr")

    def open_link(self, card):
        link = card.find_element(By.CSS_SELECTOR, "tr > td > font > a")
        link.send_keys(Keys.CONTROL + Keys.RETURN)
        self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.CONTROL + Keys.TAB)
        self.driver.switch_to.window(self.driver.window_handles[1])

    def get_first_table(self):
        self.wait.until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Rua Mayrink Veiga, 9')]")))
        first_table = self.driver.find_element(By.CSS_SELECTOR, 'table[width="780px"][border="0"]')
        ft_feats = first_table.find_elements(By.TAG_NAME, "tr")
        ft_feats = ft_feats[1:]
        for feat in ft_feats:
            feat_split = feat.text.split(':')
            self.first_feat_dict[feat_split[0]] = ''.join(feat_split[1:])

    def get_second_table(self):
        second_table = self.driver.find_elements(By.CSS_SELECTOR, '[class="accordions"]')[1]

        feat_names = second_table.find_elements(
            By.CSS_SELECTOR, 'thead > tr > th')
        feat_names = np.array(feat_names)
        for feat in feat_names:
            feat_names[np.where(feat_names == feat)] = feat.text
        feat_names[-1] = 'Data Delivery'

        feat_values = second_table.find_elements(
            By.CSS_SELECTOR, 'table > tbody > tr:nth-child(2) > td')
        feat_values = np.array(feat_values[1:13])
        for feat in feat_values:
            feat_values[np.where(feat_values == feat)] = feat.text
        feat_values = np.delete(feat_values, [2, 3, 7, 8])

        for name, value in zip(feat_names, feat_values):
            self.second_feat_dict[name] = value

    def get_third_table(self):
        third_table = self.driver.find_elements(By.CSS_SELECTOR, '[class="accordions"]')[2]

        feat_names = third_table.find_elements(
            By.CSS_SELECTOR, 'thead > tr > th')

        feat_values = third_table.find_elements(
            By.CSS_SELECTOR, 'table > tbody > tr:nth-child(1) > td')
        feat_values = np.array(feat_values)
        for feat in feat_values:
            feat_values[np.where(feat_values == feat)] = feat.text
        feat_values = np.append(feat_values[3:6], feat_values[10:12])

        for name, value in zip(feat_names, feat_values):
            self.third_feat_dict[name.text] = value

    def close_link(self):
        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])

    def scrape_info(self, card):
        self.open_link(card)
        self.get_first_table()
        self.get_second_table()
        self.get_third_table()
        self.close_link()

    def clear_dicts(self):
        self.first_feat_dict.clear()
        self.second_feat_dict.clear()
        self.third_feat_dict.clear()

    def append_dicts_to_df(self):
        self.full_dict = {**self.first_feat_dict, **self.second_feat_dict, **self.third_feat_dict}
        for key in self.full_dict.keys():
            if not any(key in col for col in self.df.columns):
                self.df[key] = np.nan
            self.df.loc[self.count, key] = self.full_dict[key]
        self.clear_dicts()

    def print_df_tail(self):
        self.logger.debug(f"Printing new rows\n{self.df.tail(100)}")

    def check_if_finished(self):
        try:
            self.driver.find_element(By.XPATH, "//*[contains(text(), 'Próxima»')]")
        except NoSuchElementException:
            self.is_finished = True
            self.logger.debug('Arrived at last page')

    def go_to_next_page(self):
        next_page = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Próxima»')]")
        next_page.click()
        self.logger.debug(f'Moving to next page')

    def scrape_site(self):
        while True:
            self.scrape_cards()
            for card in self.cards:
                try:
                    self.scrape_info(card)
                    self.append_dicts_to_df()
                except StaleElementReferenceException:
                    self.logger.warning('A Stale Element Exception has been caught')
                self.count += 1
            self.print_df_tail()
            self.check_if_finished()
            if self.is_finished is True:
                break
            self.go_to_next_page()

    def close_browser(self):
        self.driver.quit()
        self.logger.debug('Closing Browser')

    def create_dataframe_csv(self):
        self.logger.debug('Creating csv file')
        self.df = self.df.drop_duplicates()
        self.df.to_csv(f'web-scraper-inpi/.csv files/dataframe_{datetime.date(datetime.now())}.csv')
        self.logger.debug(f'dataframe.csv file created')
