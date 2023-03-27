import csv
import datetime as dt
import logging

from prettytable import PrettyTable
from constants import (
    BASE_DIR, DATETIME_FORMAT, OUTPUT_ATTR_FILE, OUTPUT_ATTR_PRETTY, RESULTS)


FILE_SAVED = 'Файл с результатами был сохранён: {file_path}'
OUTPUTS = {
        OUTPUT_ATTR_PRETTY: 'pretty_output',
        OUTPUT_ATTR_FILE: 'file_output',
        None: 'default_output'
    }


def control_output(results, cli_args):
    eval(OUTPUTS[cli_args.output])(results, cli_args)


def default_output(results, cli_args):
    for row in results:
        print(*row)


def pretty_output(results, cli_args):
    table = PrettyTable()
    table.field_names = results[0]
    table.align = 'l'
    table.add_rows(results[1:])
    print(table)


def file_output(results, cli_args):
    RESULTS_DIR = BASE_DIR / RESULTS
    RESULTS_DIR.mkdir(exist_ok=True)
    parser_mode = cli_args.mode
    now = dt.datetime.now()
    now_formatted = now.strftime(DATETIME_FORMAT)
    file_name = f'{parser_mode}_{now_formatted}.csv'
    file_path = RESULTS_DIR / file_name
    with open(file_path, 'w', encoding='utf-8') as f:
        csv.writer(
          f, csv.unix_dialect()
        ).writerows(
          results
        )
    logging.info(FILE_SAVED.format(file_path=file_path))
