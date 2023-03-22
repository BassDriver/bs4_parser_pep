import logging
import re
from collections import Counter
from urllib.parse import urljoin

import requests_cache
from bs4 import BeautifulSoup
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import BASE_DIR, EXPECTED_STATUS, MAIN_DOC_URL, PEP_LIST_URL
from outputs import control_output
from utils import find_tag, get_response

PEP_LIST_URL = 'https://peps.python.org/'

if __name__ == '__main__':
    session = requests_cache.CachedSession()
    response = session.get(PEP_LIST_URL)
    soup = BeautifulSoup(response.text, 'lxml')
    num_index = find_tag(soup, 'section', attrs={'id': 'numerical-index'})
    pep_list = find_tag(num_index, 'tbody')
    pep_lines = pep_list.find_all('tr')
    total_pep_count = 0
    status_counter = {}
    results = [('State', 'Qty')]
    for pep_line in tqdm(pep_lines):
        total_pep_count += 1
        short_status = pep_line.find('td').text[1:]
        try:
            status_ext = EXPECTED_STATUS[short_status]
        except KeyError:
            status_ext = {}
            logging.info(
                f'\nОшибочный статус в общем списке: {short_status}\n'
                f'Строка PEP: {pep_line}'
            )
        link = find_tag(pep_line, 'a')['href']
        full_link = urljoin(PEP_LIST_URL, link)
        response = session.get(full_link)
        soup = BeautifulSoup(response.text, 'lxml')
        dl_tag = find_tag(soup, 'dl')
        status_line = dl_tag.find(string='Status')
        if not status_line:
            logging.error(f'{full_link} - не найдена строка статуса')
            continue
        status_line = status_line.find_parent()
        status_int = status_line.next_sibling.next_sibling.string
        if status_int not in status_ext:
            logging.info(
                '\nНесовпадение статусов:\n'
                f'{full_link}\n'
                f'Статус в карточке - {status_int}\n'
                f'Ожидаемые статусы - {status_ext}'
            )
        if status_int in status_counter:
            status_counter[status_int] += 1
        if status_int not in status_counter:
            status_counter[status_int] = 1
    for status in status_counter:
        results.append((status, status_counter[status]))
    sum_from_cards = sum(status_counter.values())
    if total_pep_count != sum_from_cards:
        logging.error(
            f'\n Ошибка в сумме:\n'
            f'Всего PEP: {total_pep_count}'
            f'Всего статусов из карточек: {sum_from_cards}'
        )
        results.append(('Total', sum_from_cards))
    else:
        results.append(('Total', total_pep_count))
    print(results)
