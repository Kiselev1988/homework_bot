import logging
import os
import requests
import sys
import time
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


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
format = logging.Formatter('%(asctime)s, %(levelname)s, %(message)s')
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
handler.setFormatter(format)


def send_message(bot, message):
    """Отправялет сообщение в Telegramm"""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение отправлено')
    except Exception as error:
        logging.error(error, exc_info=True)


def get_api_answer(current_timestamp):
    """Запрос к API сервису Yandex.Practicum"""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        logging.error(error, exc_info=True)
    if response.status_code != CODE_STATUS:
        logger.error(f'Код ответа API не равен {CODE_STATUS}')
        raise ValueError(f'Код ответа API не равен {CODE_STATUS}')
    return response.json()


def check_response(response):
    """ Проверка ответа API """
    homework = response['homeworks']
    if 'homeworks' not in response:
        logger.error('В запросе нет ключа homeworks')
        raise ValueError('В запросе нет ключа homeworks')
    if not isinstance(homework, list):
        logger.error('Запрос не является списком')
        raise TypeError('Запрос не является списком')
    return homework


def parse_status(homework):
    """Проверка изменения статуса домашней работы."""
    name = homework['homework_name']
    status = homework['status']
    if status not in HOMEWORK_STATUSES:
        logger.error(f'Неизветный статус {status}')
        raise ValueError(f'Неизветный статус {status}')
    verdict = HOMEWORK_STATUSES[status]
    return f'Изменился статус проверки работы "{name}". {verdict}'


def check_tokens():
    """Проверка доступности токенов"""
    if TELEGRAM_TOKEN is None:
        logger.critical('Отсутствует токен Телеграмма')
    if PRACTICUM_TOKEN is None:
        logger.critical('Отсутствует токен Практикума')
    if TELEGRAM_CHAT_ID is None:
        logger.critical('Отсутствует ID чата')
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise ValueError('Токен(ы) не найден(ы)')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)[0]
            message = parse_status(homework)
            send_message(bot, message)
            current_timestamp = int(time.time())
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message, error, exc_info=True)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
