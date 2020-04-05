import json
import random
from collections import deque
from datetime import datetime
from Settings import TOKEN, WEBHOOK
from flask import Flask, request, Response, render_template
from sqlalchemy import create_engine, ForeignKey, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import NullPool
from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration
from viberbot.api.viber_requests import ViberMessageRequest, ViberConversationStartedRequest
from viberbot.api.messages import (
    TextMessage
)

engine = create_engine('postgres://gbdxkaqyfukfdt:75e542c2e41d9c1d1ee1faa8461b1f46e59113eb481e5be5a00aef1baf7ccee7@ec2-54-195-247-108.eu-west-1.compute.amazonaws.com:5432/dd2v5hjmkb5m1d', echo=True)
Base = declarative_base()
Session = sessionmaker(engine)

app = Flask(__name__)

bot_configuration = BotConfiguration(
    name='MyLearningEnglishBot4',
    avatar='http://viber.com/avatar.jpg',
    auth_token=TOKEN
)

viber = Api(bot_configuration)

START_KEYBOARD = {
"Type": "keyboard",
"Buttons": [
        {
            "Columns": 6,
            "Rows": 1,
            "BgColor": "#e6f5ff",
            "ActionBody": "Поехали!",
            "Text": "Поехали!"
        }
    ]
}

MAIN_KEYBOARD = {
"Type": "keyboard",
"Buttons": [
        {
            "Columns": 3,
            "Rows": 1,
            "BgColor": "#e6f5ff"
        },
        {
            "Columns": 3,
            "Rows": 1,
            "BgColor": "#e6f5ff"
        },
        {
            "Columns": 3,
            "Rows": 1,
            "BgColor": "#e6f5ff"
        },
        {
            "Columns": 3,
            "Rows": 1,
            "BgColor": "#e6f5ff"
        },
        {
            "Columns": 6,
            "Rows": 1,
            "BgColor": "#e6f5ff",
            "ActionBody": "Показать пример",
            "Text": "Показать пример"
        }
    ]
}

class AllUsersInfo(Base):
    __tablename__ = 'allusersinfo'
    user_id = Column(Integer, primary_key=True)
    viber_id = Column(String, nullable=False, unique=True)
    all_answers_count = Column(Integer, nullable=False, default=0)
    correct_answers_count = Column(Integer, nullable=False, default=0)
    question = Column(String)
    answer_time = Column(DateTime)
    words = relationship('Learning', back_populates='allusersinfo')


class LearningProcess(Base):
    __tablename__ = 'learningprocess'
    user_id = Column(Integer, ForeignKey('allusersinfo.user_id'), primary_key=True, nullable=False)
    word = Column(String, primary_key=True, nullable=False)
    right_answers_count = Column(Integer, nullable=False, default=0)
    answer_time = Column(DateTime)
    allusersinfo = relationship('AllUsersInfo', back_populates='words')


class Settings(Base):
    __tablename__ = 'settings'
    id = Column(Integer, primary_key=True)
    id_set = Column(Integer, nullable=False, unique=True)
    repeat_time = Column(Integer, nullable=False)
    words_count = Column(Integer, nullable=False)
    learnedwords_count = Column(Integer, nullable=False)


class TokenHolder():
    def __init__(self):
        self.q = deque(maxlen=10)

    def add_token(self, token):
        self.q.append(token)

    def check_token(self, token):
        if token in self.q:
            return True
        return False

    def get_all(self):
        print(self.q)


def add_user(viber_id):
    session = Session()
    try:
        session.add(AllUsersInfo(viber_id=viber_id, all_answers_count=0, correct_answers_count=0))
        session.commit()
        session.close()
    except:
        session.rollback()
        session.close()


def add_settings():
    session = Session()
    try:
        session.add(Settings(id_set=1, repeat_time=1800, words_count=10, learnedwords_count=5))
        session.commit()
        session.close()
    except:
        session.rollback()
        session.close()


def send_question(viber_id):
    session = Session()
    select_query = session.query(AllUsersInfo.all_answers_count, AllUsersInfo.correct_answers_count, AllUsersInfo.user_id,
                                 AllUsersInfo.answer_time).filter(AllUsersInfo.viber_id == viber_id).one()
    session.close()

    session = Session()
    settings = session.query(Settings.words_count, Settings.learnedwords_count).filter(Settings.id_set == 1).one()
    session.close()

    if select_query[0] >= settings[0]:
        temp_correct_answers_count = select_query[1]
        session = Session()
        update_query = session.query(AllUsersInfo).filter(AllUsersInfo.viber_id == viber_id).one()
        update_query.all_answers_count = 0
        update_query.correct_answers_count = 0
        session.commit()
        session.close()

        session = Session()
        select_query2 = session.query(Learning.word).filter(Learning.user_id == select_query[2]).filter(
            Learning.right_answers_count >= settings[1]).count()
        session.close()
        return TextMessage(text=f'У вас {temp_correct_answers_count} верных из {settings[0]}. '
                                f'Вы уже выучили {select_query2} слов. '
                                f'Осталось выучить {50 - select_query2} слов. '
                                f'Последний опрос пройден {str(select_query[3])[:16]}. '
                                f'Хотите ещё раз сыграть?',
                           keyboard=START_KEYBOARD, tracking_data='tracking_data')
    else:
        temp_answers = []
        temp_correct_answer = 100
        question = {}
        while temp_correct_answer >= settings[1]:
            question = random.choice(data)
            session = Session()
            try:
                session.add(Learning(user_id=select_query[2], word=question['word']))
                session.commit()
                session.close()
            except:
                session.rollback()
                session.close()

            session = Session()
            select_query2 = session.query(Learning.right_answers_count).filter(Learning.user_id == select_query[2]).filter(
                Learning.word == question['word']).one()
            session.close()
            temp_correct_answer = select_query2[0]

        session = Session()
        update_query = session.query(AllUsersInfo).filter(AllUsersInfo.viber_id == viber_id).one()
        update_query.question = str(question)
        session.commit()
        session.close()

        temp_answers.append(question['translation'])

        for i in range(3):
            temp_answers.append(random.choice(data)['translation'])
        random.shuffle(temp_answers)
        for i in range(4):
            temp_question = {'question_number': f'{select_query[0]}',
                             'answer': f"{temp_answers[i]}"}
            MAIN_KEYBOARD['Buttons'][i]['Text'] = f'{temp_answers[i]}'
            MAIN_KEYBOARD['Buttons'][i]['ActionBody'] = f'{temp_question}'
			
        return TextMessage(text=f'{select_query[0] + 1}.Как переводится слово {question["word"]}',
                           keyboard=MAIN_KEYBOARD, tracking_data='tracking_data')


def check_answer(viber_id, user_answer):
    check = 'Неверно'
    session = Session()
    select_query = session.query(AllUsersInfo.question, AllUsersInfo.user_id, AllUsersInfo.all_answers_count).filter(AllUsersInfo.viber_id == viber_id).one()
    session.close()
    question = eval(select_query[0])

    session = Session()
    update_query = session.query(AllUsersInfo).filter(AllUsersInfo.viber_id == viber_id).one()
    update_query.all_answers_count += 1
    update_query.answer_time = datetime.utcnow()
    session.commit()
    session.close()

    if user_answer == question['translation']:
        session = Session()
        update_query1 = session.query(AllUsersInfo).filter(AllUsersInfo.viber_id == viber_id).one()
        update_query1.correct_answers_count += 1
        session.commit()
        session.close()

        session = Session()
        update_query2 = session.query(Learning).filter(Learning.word == question['word']).filter(
            Learning.user_id == select_query[1]).one()
        update_query2.right_answers_count += 1
        update_query2.answer_time = datetime.utcnow()
        session.commit()
        session.close()

        session = Session()
        select_query2 = session.query(Learning.right_answers_count).filter(Learning.word == question['word']).filter(
            Learning.user_id == select_query[1]).one()
        session.close()
        check = f'Верно. Количество правильных ответов: {select_query2[0]}'
		
    return TextMessage(text=check, keyboard=MAIN_KEYBOARD, tracking_data='tracking_data')


def send_example(viber_id):
    session = Session()
    select_query = session.query(AllUsersInfo.question).filter(AllUsersInfo.viber_id == viber_id).one()
    session.close()
    question = eval(select_query[0])
	
    return TextMessage(text=f'{random.choice(question["examples"])}',
                       keyboard=MAIN_KEYBOARD, tracking_data='tracking_data')


def update_time(viber_id):
    session = Session()
    update_query = session.query(AllUsersInfo).filter(AllUsersInfo.viber_id == viber_id).one()
    update_query.answer_time = datetime.utcnow()
    session.commit()
    session.close()
	
    return TextMessage(text='Прохождение теста отложено на полчаса')


def get_question_number(viber_id):
    session = Session()
    select_query = session.query(AllUsersInfo.all_answers_count).filter(AllUsersInfo.viber_id == viber_id).one()
    session.close()
	
    return select_query[0]


@app.route('/')
def hello():
    return render_template('index.html')


@app.route('/settings')
def settings():
    session = Session()
    select_query = session.query(Settings.repeat_time, Settings.words_count, Settings.learnedwords_count).one()
    session.close()
	
    return render_template('settings.html', repeat_time=select_query[0], words_count=select_query[1],
                           learnedwords_count=select_query[2])


@app.route('/accept', methods=['POST'])
def accept():
    repeat_time = int(request.form.get('repeat_time'))
    words_count = int(request.form.get('words_count'))
    learnedwords_count = int(request.form.get('learnedwords_count'))

    session = Session()
    update_query = session.query(Settings).one()
    update_query.repeat_time = repeat_time
    update_query.words_count = words_count
    update_query.learnedwords_count = learnedwords_count
	
    session.commit()
    session.close()
	
    return 'Настройки установлены!'


with open("english_words.json", "r", encoding='utf-8') as f:
    data = json.load(f)
message_tokens = TokenHolder()

@app.route('/incoming', methods=['POST'])
def incoming():
    Base.metadata.create_all(engine)
    add_settings()
    viber_request = viber.parse_request(request.get_data())
    print(viber_request)
    if isinstance(viber_request, ViberConversationStartedRequest):
        # идентификация/добавление нового пользователя
        new_current_id = viber_request.user.id
        add_user(new_current_id)
        viber.send_messages(viber_request.user.id, [
            TextMessage(text="Hello! Let's learn English!",
                        keyboard=START_KEYBOARD, tracking_data='tracking_data')
        ])
    if isinstance(viber_request, ViberMessageRequest):
        if not message_tokens.check_token(viber_request.message_token):
            message_tokens.add_token(viber_request.message_token)
            message_tokens.get_all()
            current_id = viber_request.sender.id
            message = viber_request.message
            if isinstance(message, TextMessage):
                text = message.text
                print(text)
                # чтение введёного текста
                if text == "Поехали!":
                    bot_response = send_question(current_id)
                    viber.send_messages(current_id, bot_response)
                elif text == "Показать пример":
                    bot_response = send_example(current_id)
                    viber.send_messages(current_id, bot_response)
                elif text == "Отложить":
                    bot_response = update_time(current_id)
                    viber.send_messages(current_id, bot_response)
                else:
                    answer = eval(text)
                    question_number = get_question_number(current_id)
                    if int(question_number) == int(answer['question_number']):
                        bot_response_1 = check_answer(current_id, answer['answer'])
                        bot_response_2 = send_question(current_id)
                        viber.send_messages(current_id, [bot_response_1, bot_response_2])
    return Response(status=200)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=80)
