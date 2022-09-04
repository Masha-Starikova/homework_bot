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
        logger.info(f'В телеграмм отправлено сообщение: {message}')
    except exceptions.SendMessageFailure:
        raise exceptions.SendMessageFailure('Сообщения не отправлены')


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
        logger.info('Мы начали запрос к API.')
    except exceptions.IncorrectHttpStatus as err:
        raise exceptions.IncorrectHttpStatus(
            f'Ошибка при запросе к основному API:{err}'
        )
    if response.status_code != HTTPStatus.OK:
        raise Exception('недоступность эндпоинта')
    return response.json()


def check_response(response):
    """.
    Проверяем ответ API. В случае корректности -
    возвращаем 'homeworks'.
    """
    if not isinstance(response, dict):
        raise TypeError('Ответ API отличен от словаря')
    homeworks = response.get('homeworks')
    if 'homeworks' and 'current_date' not in response:
        raise TypeError('Список домашних работ пуст')
    if not isinstance(homeworks, list):
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
        sys.exit('Ошибка. Небыли получены необходимые данные.')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                if homeworks[0].get('status') is not None:
                    print(homeworks[0].get('status'))
                    logger.info('Сообщение было отправлено')
                    message = parse_status(homeworks[0])
                else:
                    logger.debug('Статус не изменился')
                    message = ('Статус не был изменён')
                send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
