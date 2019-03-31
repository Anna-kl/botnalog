"""
This script runs the BotNalog application using a development server.
"""

from os import environ
from BotNalog import app


from selenium import webdriver
import requests
import datetime
import sqlalchemy
import re
import os
import json
from sqlalchemy import desc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import parser_nalog as parser
import configparser

token = '714164842:AAEtzkdK-6Mf48GZGajbBWSqjCOQjPUM7y4'
proxies = {
    'http': 'http://40.68.149.233:8080' ,
    'https': 'https://40.68.149.233:8080'

}

url = 'postgresql://{}:{}@{}:5432/{}'.format('postgres' , '2537300' , 'localhost' , 'postgres')
con = sqlalchemy.create_engine(url , echo=True)
meta = sqlalchemy.MetaData(bind=con , reflect=True , schema='nalog')

# parser.get_director(5041006160)


def get_last_update():
    currency = meta.tables [ 'nalog.bot_data' ]
    cursor_select = currency.select().with_only_columns([ currency.c.update_id ]).order_by(desc(currency.c.update_id))
    data = con.execute(cursor_select)
    for item in data:
        return item [ 0 ]
    return -1


def record_update(data):
    currency = meta.tables [ 'nalog.bot_data' ]
    try:
        key = data [ 'message' ]
        key = 'message'
    except:
        key = 'edited_message'

    cursor_select = currency.select().where(currency.c.id_message == data [ key ] [ 'message_id' ])
    select_data = con.execute(cursor_select)
    if select_data.rowcount == 0:
        insert_data = dict(
            id_message=data [ key ] [ 'message_id' ] ,
            message=data [ key ] [ 'text' ] ,
            id_sender=data [ key ] [ 'from' ] [ 'id' ] ,
            dttm=data [ key ] [ 'date' ] ,
            update_id=data [ 'update_id' ] ,
            id_chat=data [ key ] [ 'chat' ] [ 'id' ]
        )

        cursor = currency.insert(insert_data)
        con.execute(cursor)
    insert_sender(data [ key ] [ 'from' ])
    info_message = dict(
        last_update_id=data [ 'update_id' ] ,
        last_chat_text=data [ key ] [ 'text' ] ,
        id_message=data [ key ] [ 'message_id' ] ,
        last_chat_id=data [ key ] [ 'chat' ] [ 'id' ] ,
        last_chat_name=data [ key ] [ 'chat' ] [ 'first_name' ]
    )
    return info_message


def insert_sender(data):
    cursor = meta.tables [ 'nalog.bot_sender' ]
    cursor_select = cursor.select().where(cursor.c.id == data [ 'id' ])
    select_data = con.execute(cursor_select)
    if select_data.rowcount == 0:
        try:
            language_code = data [ 'language_code' ] ,
        except:
            language_code='ru'
        sender = dict(
            id=data [ 'id' ] ,
            first_name=data [ 'first_name' ] ,
            username=data [ 'username' ] ,
            language_code=language_code ,
            status=-1
         )

        cursor_select = cursor.insert(sender)
        con.execute(cursor_select)


def start(bot , update):
    bot.send_message(chat_id=update.message.chat_id , text="I'm a bot, please talk to me!")


def check_message(text):
    if re.search('\d{10}' , text):
        return True
    else:
        return False


def get_inn(input_inn):
    driver = webdriver.Firefox()
    driver.get('https://egrul.nalog.ru/index.html')

    editor = driver.find_element_by_id('query')
    editor.send_keys(input_inn)
    driver.find_element_by_id('btnSearch').click()
    header = WebDriverWait(driver , 10).until(
        EC.visibility_of_element_located((By.XPATH , '/html/body/div[1]/div[3]/div/div[1]/div[4]/div/div[2]/a')))
    inn = WebDriverWait(driver , 10).until(
        EC.visibility_of_element_located((By.XPATH , '/html/body/div[1]/div[3]/div/div[1]/div[4]/div/div[3]')))
    result_inn = dict(
        header=header.text ,
        text=inn.text
    )
    return result_inn


class BotHandler:

    def __init__(self , token):
        self.token = token
        self.api_url = "https://api.telegram.org/bot{}/".format(token)

    def get_updates(self , offset=None , timeout=30):
        method = 'getUpdates'
        params = {'timeout': timeout , 'offset': offset}
        resp = requests.get(self.api_url + method , params , proxies=proxies)
        result_json = resp.json() [ 'result' ]
        return result_json

    def send_message(self , chat_id , text):
        params = {'chat_id': chat_id , 'text': text}
        method = 'sendMessage'
        resp = requests.post(self.api_url + method , params , proxies=proxies)
        return resp

    def send_document(self , chat_id , file_inn):
        file = os.listdir('/home/bot/Data/send/')
        files_name = ''
        for item in file:
            if re.search(file_inn , item):
                files_name = item
                break
        if files_name == '':
            return -1
        method = 'sendDocument'
        files = open('/home/bot/Data/send/' + files_name , 'rb')

        resp = requests.post(self.api_url + method , data={'chat_id': chat_id} , files={'document': files} ,
                             proxies=proxies)
        return resp

    def send_keyboard(self , chat_id , text):
        reply_markup = {'keyboard': [ [ 'Скачать файл' ] , [ 'Пропустить' ] ] , 'resize_keyboard': True ,
                        'one_time_keyboard': True}
        reply_markup = json.dumps(reply_markup)

        params = {'chat_id': chat_id , 'text': text , 'reply_markup': reply_markup ,
                  'disable_web_page_preview': 'true' , }
        method = 'sendMessage'
        resp = requests.post(self.api_url + method , params , proxies=proxies)
        return resp

    def get_last_update(self):
        get_result = self.get_updates()

        if len(get_result) > 0:
            last_update = get_result [ -1 ]
        else:
            last_update = get_result [ len(get_result) ]

        return last_update


greet_bot = BotHandler(token)
greetings = ('здравствуй' , 'привет' , 'ку' , 'здорово' , 'добрый день' , 'доброе утро' , 'здравствуйте')
now = datetime.datetime.now()


def insert_send_message(text , info_message):
    currency = meta.tables [ 'nalog.send_message' ]
    inn = get_only_inn(info_message [ 'last_chat_text' ])
    insert_data = dict(
        id_message=info_message [ 'id_message' ] ,
        message=text ,
        dttm=datetime.datetime.now() ,
        inn=int(inn) ,
        id_chat=info_message [ 'last_chat_id' ]
    )
    cursor = currency.insert(insert_data)
    con.execute(cursor)


def get_last_inn(chat_id):
    currency_inn = meta.tables [ 'nalog.send_message' ]
    currency_id = meta.tables [ 'nalog.bot_data' ]
    id_message = currency_inn.select().with_only_columns([ currency_inn.c.inn ]).where(
        currency_inn.c.id_chat == chat_id).order_by(desc(currency_inn.c.dttm))
    id_message = con.execute(id_message)
    for item in id_message:
        id_message = item
        break
    # select_db=currency_id.select().with_only_columns([currency_id.c.message]).where(currency_id.c.id_message==id_message[0])
    # select_db=con.execute(select_db)
    # for item in select_db:
    #     inn_text=item
    #     break
    return id_message [ 0 ]

def return_info_director(director):
    result='Должность - {}. Фамилия И.О: {} {} {}'.format(director['position'],director['surnames'],director['name'],director['second_name'])
    return result

def get_only_inn(text):
    temp = re.search('\d{10}' , text)
    return temp.group(0)

def return_info_founders(text):
    result=''
    for item in text:
        result+='Фамилия И.О. - {} {} {}\n'.format(item['surnames'],item['name'],item['second_name'])
    return result


def search_inn(info_message,config):
    inn=parser.get_simple_data (info_message [ 'last_chat_text' ])
    # last_inn=get_only_inn(last_chat_text)
    if inn == -1:
        greet_bot.send_message (info_message [ 'last_chat_id' ] , 'Сервис временно не доступен')
        return -1
    elif inn == -2:
        greet_bot.send_message (info_message [ 'last_chat_id' ] , 'Данный ИНН отсутсвует в базе данных')
        return -1
    while True:
        try:
            source_text=config [ 'Source' ] [ 'text' ]
            greet_bot.send_message (info_message [ 'last_chat_id' ] ,
                                    source_text + '\nИнформация по фирме\n{} '.format (inn))
            insert_send_message (inn , info_message)
            print (inn)
            inn_text=get_last_inn (info_message [ 'last_chat_id' ])
            director=parser.get_director (inn_text)
            if director == -1:
                greet_bot.send_message (info_message [ 'last_chat_id' ] , 'Информация о директоре не обнаружена')

            else:
                greet_bot.send_message (info_message [ 'last_chat_id' ] ,
                                        'Информация о директоре \n{}'.format (return_info_director (director)))
            founders=parser.get_founders (inn_text)
            if founders == -1:
                greet_bot.send_message (info_message [ 'last_chat_id' ] ,
                                        'Информация об учредителях не обнаружена')

            else:
                greet_bot.send_message (info_message [ 'last_chat_id' ] ,
                                        'Информация об учредителях \n{}'.format (return_info_founders (founders)))

            greet_bot.send_keyboard (info_message [ 'last_chat_id' ] , 'Загрузить полную выписку')
            new_offset=get_last_update ()
            new_offset+=1
            try:
                message_bot=greet_bot.get_updates (new_offset)

                info_message_last=record_update (message_bot[0])
            except:
                greet_bot.send_keyboard (info_message [ 'last_chat_id' ] , 'Введите новый запрос')
                break
            last_update=message_bot [ 0 ]
            last_chat_text=last_update [ 'message' ] [ 'text' ]

            if last_chat_text == 'Скачать файл':

                greet_bot.send_document (info_message [ 'last_chat_id' ] , str (inn_text))
                break
            elif last_chat_text == 'Пропустить':
                inn_text=get_last_inn (info_message [ 'last_chat_id' ])
                os.remove ('/home/Data/send/' + str (inn_text) + '.pdf')
                break
            elif info_message_last['last_chat_id']!=info_message['last_chat_id']:
                main_delay(info_message_last,config)
                greet_bot.send_message (info_message [ 'last_chat_id' ] , 'Жду еще ИНН')
                break
        except Exception as e:
            print (e.args)
            continue


def main_delay(info_message, config):
    today=now.day
    hour=now.hour
    if check_message (info_message [ 'last_chat_text' ]):
        greet_bot.send_message (info_message [ 'last_chat_id' ] , 'Идет загрузка информации....')
        if len (info_message [ 'last_chat_text' ]) > 10:
            info_message [ 'last_chat_text' ]=get_only_inn (info_message [ 'last_chat_text' ])
        search_inn (info_message , config)

    elif info_message [ 'last_chat_text' ] == '/start':

        temp_text=config [ 'Start' ] [ 'text' ]
        greet_bot.send_message (info_message [ 'last_chat_id' ] , '{} '.format (temp_text))

    else:

        if info_message [ 'last_chat_text' ].lower () in greetings and today == now.day and 6 <= hour < 12:
            greet_bot.send_message (info_message [ 'last_chat_id' ] ,
                                    'Доброе утро, {}.\n Жду ИНН'.format (info_message [ 'last_chat_name' ]))
            today+=1

        elif info_message [ 'last_chat_text' ].lower () in greetings and today == now.day and 12 <= hour < 17:
            greet_bot.send_message (info_message [ 'last_chat_id' ] ,
                                    'Добрый день, {}.\n Жду ИНН'.format (info_message [ 'last_chat_name' ]))
            today+=1

        elif info_message [ 'last_chat_text' ].lower () in greetings and today == now.day and 17 <= hour < 23:
            greet_bot.send_message (info_message [ 'last_chat_id' ] ,
                                    'Добрый вечер, {}.\n  Жду ИНН'.format (info_message [ 'last_chat_name' ]))
            today+=1

        else:
            greet_bot.send_message (info_message [ 'last_chat_id' ] ,
                                    'Введите ИНН, 10 цифр, {}.\n'.format (info_message [ 'last_chat_name' ]))
            today+=1
    return -1







from flask import Flask
app = Flask(__name__)

@app.route("/")
def main():

    config = configparser.ConfigParser()
    temp=os.getcwd() + '/config.ini'
    
    config.read(os.getcwd() + '/config.ini' , encoding='utf8')

    while True:
        new_offset = get_last_update()
        new_offset += 1
        try:
            message_bot = greet_bot.get_updates(new_offset)
        except Exception as e:
            print(e.args)
            continue
        # last_update = greet_bot.get_last_update()
        if len(message_bot) == 0:
            continue

        last_update = message_bot [ 0 ]
        info_message = record_update(last_update)
        # last_update_id = last_update['update_id']
        # last_chat_text = last_update['message']['text']
        print(info_message)
        # last_chat_id = last_update['message']['chat']['id']
        # last_chat_name = last_update['message']['chat']['first_name']

        main_delay(info_message,config)

        # new_offset = info_message [ 'last_chat_id' ] + 1


if __name__ == "__main__":
    app.run()