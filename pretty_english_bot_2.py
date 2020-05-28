from telegram import Update, Bot, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import CallbackContext, Updater, Filters, MessageHandler, CommandHandler
from telegram.utils.request import Request
from google.oauth2.service_account import Credentials
from datetime import date
import requests, gspread, random

scopes = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = Credentials.from_service_account_file('pretty-english-1dcfb496d5b9.json', scopes=scopes)
gc = gspread.authorize(credentials)
wks = gc.open('Vocabulary_for_all').sheet1


# Декоратор для проверок на ошибки
def log_error(f):
    def inner(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            print(f'Ошибка: {e}')
            raise e

    return inner


# кнопочки
add_voc_button = '/Add_in_vocabulary'
start_button = '/start_game'
next_word_button = '/Next_word'
flip_word_button = '/Flip_word'
i_know_button = '/I_know_this_word'
game_buttons = [start_button, next_word_button, flip_word_button, i_know_button, add_voc_button]
gbtc = [i[1:] for i in game_buttons]  # для вызова в диспетчере в функции мейн

# разные переменные для хранения данных в глобале
data = []
spreadsheet_url = ''
random_number = 0
flip_flap = 0


@log_error
def keep_user_gmail(update: Update, context: CallbackContext):
    update.message.reply_text(text='Hello, before you start using this bot, I must create your own vocabulary. '
                                   'Please, enter your Gmail address.',
                              reply_markup=ReplyKeyboardRemove)


@log_error
def make_spreadsheet(update: Update, context: CallbackContext):
    # мы получили гмаил и засунули его в переменную
    user_gmail = update.effective_message.text.lower()

    update.message.reply_text(text='I have your mail. It\'s: ' + user_gmail +
                                   '. Please, wait a second, I am creating your vocabulary.')

    # пробуем открыть таблицу с таким именем, если она уже есть.
    try:
        global wks
        wks = gc.open('Vocabulary ' + user_gmail).sheet1

    # Если её нет, то создаём новую, открываем, шарим, создаём первые ряды
    except:
        sh = gc.create('Vocabulary ' + user_gmail)
        sh.share(user_gmail, perm_type='user', role='writer')
        wks = gc.open('Vocabulary ' + user_gmail).sheet1
        wks.append_row(['Date', 'word_id', 'English', 'Russian main meaning', 'Russian secondary meaning', 'Result'])
        wks.append_row([str(date.today()), 1, 'cat', 'кошка', 'кот', 0])
        wks.format('A1:F1', {'textFormat': {'bold': True}})

    # формируем url
    global spreadsheet_url
    spreadsheet_url = 'https://docs.google.com/spreadsheets/d/' + gc.open('Vocabulary ' + user_gmail).id

    update.message.reply_text(text='At now, you can send me any english word, and I will give you translate. '
                                   'After translate, you can add new word in your vocabulary.\n\n'
                                   'Also, you can write /start_game and repeat words from your vocabulary. \n\n'
                                   'If you want watch and transform your vocabulary, send me /open_vocabulary '
                                   '(be careful, don\'t edit spreadsheet structure and headers!)\n\n'
                                   'Get luck!')


@log_error
def randomise(update: Update, context: CallbackContext):
    if spreadsheet_url == '':
        update.message.reply_text(text='If you want to repeat your words, you must send me your gmail. '
                                       'Otherwise, you can only translate words.',
                                  reply_markup=ReplyKeyboardRemove())
    else:
        global random_number
        all_values_from_wks = wks.get_all_records()
        english_words = [i['English'] for i in all_values_from_wks if i['Result'] == 0]
        russian_words = [i['Russian main meaning'] for i in all_values_from_wks if i['Result'] == 0]
        russian_words_secondary = [i['Russian secondary meaning'] for i in all_values_from_wks if i['Result'] == 0]

        random_number = random.randrange(0, len(english_words))

        def choose_lang_of_word():
            flip_keyword = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=flip_word_button)]],
                resize_keyboard=True)

            eng_or_rus = random.randint(1, 2)
            global flip_flap

            if eng_or_rus == 1:
                update.message.reply_text(
                    text=english_words[random_number].capitalize(),
                    reply_markup=flip_keyword)
                flip_flap = 1

            elif eng_or_rus == 2:
                update.message.reply_text(
                    text=russian_words[random_number].capitalize() + ', ' + russian_words_secondary[random_number],
                    reply_markup=flip_keyword)
                flip_flap = 2

        choose_lang_of_word()


@log_error
def flip(update: Update, context: CallbackContext):
    next_word_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=next_word_button), KeyboardButton(text=i_know_button)]],
        resize_keyboard=True)

    all_values_from_wks = wks.get_all_records()
    english_words = [i['English'] for i in all_values_from_wks if i['Result'] == 0]
    russian_words = [i['Russian main meaning'] for i in all_values_from_wks if i['Result'] == 0]
    russian_words_secondary = [i['Russian secondary meaning'] for i in all_values_from_wks if i['Result'] == 0]

    global flip_flap
    if flip_flap == 1:
        update.message.reply_text(
            text=russian_words[random_number].capitalize() + ', ' + russian_words_secondary[random_number],
            reply_markup=next_word_keyboard)
    elif flip_flap == 2:
        update.message.reply_text(
            text=english_words[random_number].capitalize(),
            reply_markup=next_word_keyboard)


@log_error
def i_know_function(update: Update, context: CallbackContext):
    next_word_keyboard_2 = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=next_word_button)]],
        resize_keyboard=True
    )

    all_values_from_wks = wks.get_all_records()
    english_words = [i['English'] for i in all_values_from_wks if i['Result'] == 0]

    # чекаем где находится слово, которое знаем и в его ряд и столбец резалт бахаем еденичку
    memorized_word = wks.find(english_words[random_number])
    wks.update(f'F{memorized_word.row}', '1')
    update.message.reply_text(
        text='You\'re a good boy!',
        reply_markup=next_word_keyboard_2)


@log_error
def open_vocabulary(update: Update, context: CallbackContext):
    update.message.reply_text(
        text=spreadsheet_url, reply_markup=ReplyKeyboardRemove())


@log_error
def message_handler(update: Update, context: CallbackContext):
    received_text = update.effective_message.text

    add_in_voc_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=add_voc_button),],],
        resize_keyboard=True)

    def translate_me(my_text):
        token = 'dict.1.1.20200506T102743Z.6c8c1b7128d34ccf.9da2a27fef41e4b13079806cef83f416c3f041e8'
        params = {
            'key': token,
            'text': my_text,
            'lang': 'en-ru'
        }
        url = f"https://dictionary.yandex.net/api/v1/dicservice.json/lookup?key={token}&lang={params['lang']}&text={params['text']}"
        response = requests.get(url, params=params)

        if response.json()['def'] != []:
            general_word = response.json()['def'][0]['tr'][0]['text']  # основное значение в строковом формате
            word_id = int(wks.col_values(2)[-1]) + 1

            try:  # добавляем трай, так как в случае, если у слова одно значение, вылезает ошибка
                another_words = response.json()['def'][0]['tr'][0][
                    'syn']  # дополнительные значения в словарях внутри списка
                list_of_words = [i['text'] for i in another_words]
                update.message.reply_text(
                    text=my_text.upper() + ': ' + general_word.capitalize() + ', ' + ', '.join(list_of_words[0:4]),
                    reply_markup=add_in_voc_keyboard)
                global data
                data = [str(date.today()), word_id, my_text, general_word.capitalize(), ', '.join(list_of_words[0:4]), 0]

            except KeyError:
                update.message.reply_text(
                    text=my_text.upper() + ': ' + general_word.capitalize(),
                    reply_markup=add_in_voc_keyboard)
                data = [str(date.today()), word_id, my_text, general_word.capitalize(), '', 0]

        else:
            update.message.reply_text(
                text='I don\'t understand you. Type "cat" or "dog".')

    translate_me(received_text)


@log_error
def add_in_vocabulary(update: Update, context: CallbackContext):
    if spreadsheet_url == '':
        update.message.reply_text(text='If you want to add words in your vocabulary, you must send me your gmail. '
                                       'Otherwise, you can only translate words.',
                                  reply_markup=ReplyKeyboardRemove())
    else:
        values_list = wks.col_values(3)
        if values_list.count(data[2]) != 0:
            update.message.reply_text(text='This word was already in your vocabulary.',
                                      reply_markup=ReplyKeyboardRemove())
        else:
            wks.append_row(data)
            update.message.reply_text(text='Successfully added!', reply_markup=ReplyKeyboardRemove())


@log_error
def main():
    print('Start')

    req = Request(
        connect_timeout=0.5,
    )
    bot = Bot(
        request=req,
        token='TOKEN',
        base_url='https://telegg.ru/orig/bot',
    )
    updater = Updater(
        bot=bot,
        use_context=True,
    )

    updater.dispatcher.add_handler(CommandHandler([gbtc[0], gbtc[1]], callback=randomise))
    updater.dispatcher.add_handler(CommandHandler(gbtc[2], callback=flip))
    updater.dispatcher.add_handler(CommandHandler(gbtc[3], callback=i_know_function))
    updater.dispatcher.add_handler(CommandHandler(gbtc[4], callback=add_in_vocabulary))
    updater.dispatcher.add_handler(MessageHandler(Filters.regex(r'@gmail.com'), callback=make_spreadsheet))
    updater.dispatcher.add_handler(CommandHandler('start', callback=keep_user_gmail))
    updater.dispatcher.add_handler(CommandHandler('Open_vocabulary', callback=open_vocabulary))
    updater.dispatcher.add_handler(MessageHandler(filters=Filters.all, callback=message_handler))

    updater.start_polling()
    updater.idle()

    print('Finish')


if __name__ == '__main__':
    main()