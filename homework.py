from http import HTTPStatus
import time
import requests
import os
import logging
import sys
import telegram
from dotenv import load_dotenv 
from telegram import Bot
from exceptions import IncorrectHttpStatus


load_dotenv()


PRACTICUM_TOKEN =  os.getenv('PRACTICUM_TOKEN')
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
    bot = Bot(token='{TELEGRAM_TOKEN}')
    bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    """
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
    except IncorrectHttpStatus as err:
        logger.error(f'Ошибка при запросе к основному API:{err}')
        raise IncorrectHttpStatus(
            f'Ошибка при запросе к основному API:{err}'
        )
    if response.status_code != HTTPStatus.OK:
        logger.error('недоступность эндпоинта')
        raise Exception('недоступность эндпоинта')

    return response.json()
def check_response(response):
    """
    Проверяем ответ API. В случае корректности -
    возвращаем 'homeworks'.
    """
    if isinstance(response['homeworks'], list):
        return response['homeworks']
    else:
        raise Exception
   

def parse_status(homework):
    """
    Извлекаем из 'homeworks' статус и,
    в случае успеха, возвращаем вердикт.
    """
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except TypeError as error:
        logging.error(f'Возникла ошибка {error} при запросе.')


def check_tokens():
    """Проверяем, что все токены на месте."""
    env_vars = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return all(env_vars)


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    status = None
    error = None
    if check_tokens() is False:
        sys.exit()
    else:
        while True:
            try:
                response = get_api_answer(
                    current_timestamp=current_timestamp
                )
                homeworks = check_response(response)
                if len(homeworks) == 0:
                   logger.debug('В ответе сервера отсутсвуют новые записи.')
                new_status = homeworks[0].get('status')
                message = parse_status(homeworks[0])
                if new_status != status:
                    send_message(bot, message)
                    logger.info(f'В телеграмм отправлено сообщение: {message}')
                else:
                    logger.info('Статус домашней работы не изменился.')
                    current_timestamp = response['current_date']
            except Exception as new_error:
                message = f'Сбой в работе программы: {new_error}'
                logger.error(f'Сбой в работе программы: {new_error}')
                if error != str(new_error):
                    error = str(new_error)
                    send_message(bot, message)
            finally:
                time.sleep(RETRY_TIME)
if __name__ == '__main__':
    main()
