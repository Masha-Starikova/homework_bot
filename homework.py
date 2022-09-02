import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import exceptions

load_dotenv()


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
logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s'
)
handler = logging.StreamHandler(stream=sys.stdout)
logger = logging.getLogger(__name__)


def send_message(bot, message):
    """Отправляем сообщение в чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except exceptions.SendMessageFailure:
        raise exceptions.SendMessageFailure('Сообщения не отправлены')
    else:
        logger.info(f'В телеграмм отправлено сообщение: {message}')


def get_api_answer(current_timestamp):
    """.
    Делаем запрос к эндпоинту API,
    в случае успешного ответа - возвращаем ответ.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except exceptions.IncorrectHttpStatus as err:
        raise exceptions.IncorrectHttpStatus(
            f'Ошибка при запросе к основному API:{err}'
        )
    else:
        logger.info('Мы начали запрос к API.')
    if response.status_code != HTTPStatus.OK:
        logger.error('недоступность эндпоинта')
        raise Exception('недоступность эндпоинта')
    return response.json()


def check_response(response):
    """.
    Проверяем ответ API. В случае корректности -
    возвращаем 'homeworks'.
    """
    if not isinstance(response, dict):
        raise TypeError('Ответ API отличен от словаря')
    try:
        homeworks = response.get('homeworks')
    except KeyError as error:
        logger.error(f'Ошибка доступа по ключу homeworks: {error}')
        raise KeyError(f'Ошибка доступа по ключу homeworks: {error}')
    if 'homeworks' not in response:
        if 'current_date' not in response:
            logger.error('Список домашних работ пуст')
            raise TypeError('Список домашних работ пуст')
    if not isinstance(homeworks, list):
        logger.error('Данные не читаемы')
        raise exceptions.IncorrectFormatResponse('Данные не читаемы')
    return homeworks


def parse_status(homework):
    """.
    Извлекаем из 'homeworks' статус и,
    в случае успеха, возвращаем вердикт.
    """
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if 'homework_name' not in homework:
        raise KeyError('Нет домашнего задания')
    if homework_status not in HOMEWORK_STATUSES:
        raise ValueError('Не документированный статус')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем, что все токены на месте."""
    env_vars = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return all(env_vars)


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if check_tokens() is False:
        sys.exit()
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            for homework in homeworks:
                last_homework = {
                    homework['homework_name']: homework['status']
                }
                message = parse_status(homework)
                if last_homework != homework['status']:
                    send_message(bot, message)
                    logger.info('Сообщение было отправлено')
                else:
                    logger.debug('Статус не изменился')
                    message = ('Статус не был изменён')
                    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
