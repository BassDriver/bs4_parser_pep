import logging
import re
from collections import defaultdict
from urllib.parse import urljoin

import requests_cache
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import (
    BASE_DIR, DOWNLOADS, EXPECTED_STATUS, MAIN_DOC_URL, PEP_LIST_URL)
from outputs import control_output
from utils import find_tag, get_soup

DOWNLOAD_COMPLETE = 'Архив был загружен и сохранён: {archive_path}'
VALUE_ERROR = 'Ничего не нашлось'
COMMAND_ARGUMENTS = 'Аргументы командной строки: {args}'
JOB_DONE = 'Парсер завершил работу.'
ERROR_MESSAGE = 'Ошибка при выполнении: {error}'
LINK_ERROR = 'Ссылка {link} недоступна. Ошбика {error}'
INFO_MESSAGE = ('Несовпадение статусов:'
                ' {full_link} -'
                ' Статус в карточке - {status_internal},'
                ' Ожидаемые статусы - {status_external}')


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, Автор')]
    error_messages = []
    for a in tqdm(
        get_soup(
          session, whats_new_url
        ).select(
          '#what-s-new-in-python div.toctree-wrapper li.toctree-l1 > a'
        )
    ):
        version_link = urljoin(whats_new_url, a['href'])
        try:
            soup = get_soup(session, version_link)
            results.append(
                (version_link, find_tag(soup, 'h1').text,
                 find_tag(soup, 'dl').text.replace('\n', ' '))
                )
        except ConnectionError as error:
            error_messages.append(
                LINK_ERROR.format(link=version_link, error=error))

    for error in (
      error for error in error_messages if error_messages != []
    ):
        logging.exception(error)

    return results


def latest_versions(session):
    for ul in get_soup(
      session, MAIN_DOC_URL
    ).select(
      'div.sphinxsidebarwrapper ul'
    ):
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise ValueError(VALUE_ERROR)
    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'

    for a_tag in a_tags:
        text_match = re.search(pattern, a_tag.text)
        if text_match is not None:
            version, status = text_match.groups()
        else:
            version, status = a_tag.text, ''
        results.append(
            (a_tag['href'], version, status)
        )
    return results


def download(session):
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')

    pdf_a4_link = get_soup(
      session, downloads_url
    ).select_one(
      'div[role=main] table.docutils a[href$="pdf-a4.zip"]'
    )['href']

    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    DOWNLOADS_DIR = BASE_DIR / DOWNLOADS
    DOWNLOADS_DIR.mkdir(exist_ok=True)
    archive_path = DOWNLOADS_DIR / filename

    response = session.get(archive_url)
    with open(archive_path, 'wb') as file:
        file.write(response.content)
    logging.info(DOWNLOAD_COMPLETE.format(archive_path=archive_path))


def pep(session):
    soup = get_soup(session, PEP_LIST_URL)
    num_index = find_tag(soup, 'section', attrs={'id': 'numerical-index'})
    pep_list = find_tag(num_index, 'tbody')
    pep_lines = pep_list.find_all('tr')
    status_counter = defaultdict(int)
    info_messages = []
    error_messages = []
    for pep_line in tqdm(pep_lines):
        short_status = pep_line.find('td').text[1:]
        status_external = EXPECTED_STATUS[short_status]
        link = find_tag(pep_line, 'a')['href']
        full_link = urljoin(PEP_LIST_URL, link)
        try:
            soup = get_soup(session, full_link)
            dl_tag = find_tag(soup, 'dl')
            status_line = dl_tag.find(string='Status')
            status_line = status_line.find_parent()
            status_internal = str(
                status_line.next_sibling.next_sibling.string)
            if status_internal not in status_external:
                info_messages.append(INFO_MESSAGE.format(
                    full_link=full_link, status_internal=status_internal,
                    status_external=status_external)
                )
            status_counter[status_internal] += 1
        except ConnectionError as error:
            error_messages.append(
                LINK_ERROR.format(link=full_link, error=error))

    for error in (
      error for error in error_messages if error_messages != []
    ):
        logging.exception(error)

    for info in (
      info for info in info_messages if info_messages != []
    ):
        logging.info(info)
    return [
        ('Статус', 'Количество'),
        *status_counter.items(),
        ('Всего', sum(status_counter.values())),
    ]


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main():
    configure_logging()
    logging.info('Парсер запущен!')

    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    logging.info(COMMAND_ARGUMENTS.format(args=args))

    try:
        session = requests_cache.CachedSession()
        if args.clear_cache:
            session.cache.clear()

        parser_mode = args.mode
        results = MODE_TO_FUNCTION[parser_mode](session)

        if results is not None:
            control_output(results, args)
    except Exception as error:
        logging.exception(ERROR_MESSAGE.format(error=error), stack_info=True)

    logging.info(JOB_DONE)


if __name__ == '__main__':
    main()
