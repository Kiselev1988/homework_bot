import logging
import os
import time
import json

import requests
import telegram
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler


load_dotenv()


CODE_STATUS = 200
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
STATUS = 'Новый статус домашней работы {name} - {verdict}'
SEND_MESSAGE_ERROR = 'Ошибка {error} отправки сообщения {message}.'
SEND_MESSAGE_SUCCSES = 'Cообщение {message} успешно отправлено.'
NETWORK_ERROR = 'Ошибка соединения с {url}, {headers}, {params}'
API_ERROR = ('Ошибка запроса к API. Код ответа:{status}, {url}, {headers},'
             '{params}'
             )
TYPE_HOMEWORKS = 'Запрос вернул некорректный тип {type}'
UNKNOWN_VERDICT = 'Неизветный статус {verdict}'
HOMEWORK_STATUS = 'Изменился статус проверки работы "{name}". {verdict}'
TOKENS_ERROR = 'Нет токена {token}'
TOKEN_NOT_FOUND = 'Токен(ы) не найден(ы)'
MESSSAGE = 'Сбой в работе программы: {error}'

LOG_FILENAME = __file__ + '.log'
logger = logging.getLogger(__name__)
handler = RotatingFileHandler(
    LOG_FILENAME,
    maxBytes=50000000,
    backupCount=5)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)
format = logging.Formatter('%(asctime)s, %(levelname)s, %(message)s')


def send_message(bot, message):
    """Отправляет сообщение в Telegramm."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(SEND_MESSAGE_SUCCSES.format(message))
    except Exception as error:
        logger.exception(SEND_MESSAGE_ERROR.format(
            error=error, message=message
        ))


def get_api_answer(current_timestamp):
    """Запрос к API сервису Yandex.Practicum."""
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
    except requests.RequestException:
        raise ConnectionError(NETWORK_ERROR.format(
            url=ENDPOINT, headers=HEADERS, params=params
        ))
    if response.status_code != CODE_STATUS:
        raise ValueError(API_ERROR.format(
            status=response.status_code,
            url=ENDPOINT, headers=HEADERS, params=params
        ))
    try:
        return response.json()
    except json.decoder.JSONDecodeError as error:
        raise ValueError(response.text, error)


def check_response(response):
    """Проверка ответа API."""
    homeworks = response['homeworks']
    if not isinstance(response, dict):
        raise TypeError(TYPE_HOMEWORKS.format(type=response))
    if not isinstance(homeworks, list):
        raise TypeError(TYPE_HOMEWORKS.format(type=homeworks))
    if 'homeworks' not in response:
        raise ValueError('В запросе нет ключа homeworks')
    return homeworks


def parse_status(homework):
    """Проверка изменения статуса домашней работы."""
    name = homework['homework_name']
    verdict = homework['status']
    if verdict not in VERDICTS:
        raise ValueError(UNKNOWN_VERDICT.format(verdict=verdict))
    return HOMEWORK_STATUS.format(name=name, verdict=VERDICTS[verdict])


def check_tokens():
    """Проверка доступности токенов."""
    tokens = ['PRACTICUM_TOKEN', 'TELEGRAM_CHAT_ID', 'TELEGRAM_TOKEN']
    tokens_error = ''
    for name in tokens:
        if globals()[name] is None:
            tokens_error += f'{name}'
    if tokens_error != '':
        logger.critical(TOKENS_ERROR.format(token=tokens_error))
        return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise ValueError(TOKEN_NOT_FOUND)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            message = parse_status(check_response(response)[0])
            send_message(bot, message)
            response.get('current_date', current_timestamp)
        except Exception as error:
            message = MESSSAGE.format(error=error)
            logger.exception(message)
            send_message(bot, message)
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
