import logging
import os
import time
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

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
NETWORK_ERROR = 'Ошибка {error} соединения с {url}, {headers}, {params}'
API_ERROR = ('Ошибка запроса к API. Код ответа:{status}, {url}, {headers},'
             '{params}'
             )
TYPE_HOMEWORKS = 'Запрос вернул некорректный тип {type}'
UNKNOWN_STATUS = 'Неизветный статус {status}'
HOMEWORK_STATUS = 'Изменился статус проверки работы "{name}". {status}'
TOKENS_ERROR = 'Нет токена {token}'
TOKEN_NOT_FOUND = 'Токен(ы) не найден(ы)'
BOT_SEND_ERROR_MESSSAGE = 'Сбой в работе программы: {error}'
RESPONSE_JSON_ERROR = ('Ошибка:{error_value}. Код статуса:{error}, {url},'
                       '{headers}, {params}')
TOKENS = ('PRACTICUM_TOKEN', 'TELEGRAM_CHAT_ID', 'TELEGRAM_TOKEN')
KEY_HOMEWORKS_ERROR = 'В запросе нет ключа homeworks'

LOG_FILENAME = __file__ + '.log'
logger = logging.getLogger(__name__)
handler = RotatingFileHandler(
    LOG_FILENAME,
    maxBytes=50000000,
    backupCount=5)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)
format = logging.Formatter('%(asctime)s, %(levelname)s, %(message)s')
handler.setFormatter(format)


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
    parameters = dict(
        url=ENDPOINT,
        headers=HEADERS,
        params={'from_date': current_timestamp})
    try:
        response = requests.get(**parameters)
    except requests.RequestException as error:
        raise ConnectionError(NETWORK_ERROR.format(error=error, **parameters))
    if response.status_code != CODE_STATUS:
        raise ValueError(API_ERROR.format(
            status=response.status_code,
            **parameters
        ))
    response_json = response.json()
    for error in ['code', 'error']:
        if error in response_json:
            raise ValueError(RESPONSE_JSON_ERROR.format(
                error_value=response_json[error],
                error=error,
                **parameters
            ))
    return response_json


def check_response(response):
    """Проверка ответа API."""
    if not isinstance(response, dict):
        raise TypeError(TYPE_HOMEWORKS.format(type=type(response)))
    if 'homeworks' not in response:
        raise ValueError(KEY_HOMEWORKS_ERROR)
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError(TYPE_HOMEWORKS.format(type=type(homeworks)))
    return homeworks


def parse_status(homework):
    """Проверка изменения статуса домашней работы."""
    name = homework['homework_name']
    status = homework['status']
    if status not in VERDICTS:
        raise ValueError(UNKNOWN_STATUS.format(status=status))
    return HOMEWORK_STATUS.format(name=name, status=VERDICTS[status])


def check_tokens():
    """Проверка доступности токенов."""
    tokens_error = [name for name in TOKENS if globals()[name] is None]
    if tokens_error:
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
            if check_response(response):
                send_message(bot, parse_status(check_response(response)[0]))
            current_timestamp = response.get('current_date', current_timestamp)
        except Exception as error:
            message = BOT_SEND_ERROR_MESSSAGE.format(error=error)
            logger.exception(message)
            send_message(bot, message)
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
