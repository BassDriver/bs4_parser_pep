import logging

from bs4 import BeautifulSoup
from requests import RequestException
from exceptions import ParserFindTagException


CONNECTION_ERROR='Возникла ошибка при загрузке страницы {url}'
ERROR_MESSAGE = 'Не найден тег {tag} {attrs}'


def get_response(session, url, encoding='utf-8'):
    try:
        response = session.get(url)
        response.encoding = encoding
        return response
    except RequestException:
        raise ConnectionError(CONNECTION_ERROR.format(url=url))


def find_tag(soup, tag, attrs=None):
    searched_tag = soup.find(tag) if attrs is None else soup.find(tag, attrs)
    if searched_tag is None:
        raise ParserFindTagException(
            ERROR_MESSAGE.format(tag=tag, attrs=attrs)
        )
    return searched_tag


def get_soup(session, url):
    response = get_response(session, url)
    soup = BeautifulSoup(response.text, features='lxml')
    return soup
