from json import dumps

import telebot
import requests
from telebot.types import Message
from flask import request, Flask

from client_bot import settings, db, text_handler
from client_bot.media_handler import MediaHandler

WEBHOOK_HOST = settings.BOT_HOST
WEBHOOK_PORT = settings.BOT_PORT
ssl_cert = '/hdd/certs/webhook_cert.pem'
ssl_cert_key = '/hdd/certs/webhook_pkey.pem'
base_url = f'{WEBHOOK_HOST}:{WEBHOOK_PORT}'
route_path = f'/{settings.URI}/'

bot = telebot.TeleBot(settings.USER_BOT_TOKEN)

app = Flask(__name__)


def download_file(file_id: str, filename: str):
    link = f'https://api.telegram.org/file/bot{settings.USER_BOT_TOKEN}/' \
        f'{bot.get_file(file_id).file_path}'
    with open(filename, 'wb') as out:
        r = requests.get(link, stream=True)
        for chunk in r:
            out.write(chunk)


@app.route(route_path, methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return 'ok'


def report(message: Message):
    report_bot = telebot.TeleBot(settings.REPORT_BOT_TOKEN)
    formatted_message = dumps(message.json, indent=2, ensure_ascii=False)
    report_msg = f'<b>Попытка доступа в клиентский бот!</b>\n\n<code>' \
                 f'{formatted_message}</code>'
    report_bot.send_message(264275085, report_msg, parse_mode='HTML')


def check_auth(func):
    def wrapper(message):
        if db.check_auth(message.from_user.id):
            return func(message)
        else:
            response = '`Доступ запрещен. Обратитесь к администратору`'
            bot.send_message(message.from_user.id, response,
                             parse_mode='Markdown')
            report(message)
    return wrapper


@bot.message_handler(commands=['start'])
@check_auth
def handle_start(message):
    bot.send_message(
        message.from_user.id,
        'Welcome!'
    )


@bot.message_handler(func=lambda message: True, content_types=['text'])
@check_auth
def handle_text_message(message: Message):
    text_handler.TextHandler(message).handle_text()


@bot.message_handler(func=lambda message: True, content_types=['photo'])
@check_auth
def handle_photo(message: Message):
    file_id = message.photo[-1].file_id
    download_file(file_id, file_id)
    caption = message.caption
    MediaHandler(message.from_user.id, file_id, caption).handle_media()


@bot.message_handler(func=lambda message: True, content_types=['document'])
@check_auth
def handle_document(message: Message):
    file_id = message.document.file_id
    file_name = message.document.file_name
    download_file(file_id, file_name)
    caption = message.caption
    MediaHandler(message.from_user.id, file_name, caption,
                 media_type='document').handle_media()


@bot.message_handler(func=lambda message: True, content_types=['voice'])
@check_auth
def handle_voice(message: Message):
    file_id = message.voice.file_id
    link = f'https://api.telegram.org/file/bot{settings.USER_BOT_TOKEN}/' \
           f'{bot.get_file(file_id).file_path}'
    MediaHandler(message.from_user.id, link, media_type='voice').handle_media()


ignoring_types = ['sticker', 'audio', 'video', 'video_note', 'location', 'contact', '']


@bot.message_handler(func=lambda message: True, content_types=ignoring_types)
@check_auth
def handle_text_message(message: Message):
    response = '<code>Бот не поддерживает отправку сообщений такого ' \
               'типа. Пожалуйста, отправьте текст, фото или документ.</code>'
    bot.send_message(message.from_user.id, response, parse_mode='HTML')


if __name__ == '__main__':
    bot.polling(True, timeout=50)
