from django import template

register = template.Library()

SUBJECT_TRANSLATIONS = {
    'uz': {
        'Matematika': 'Matematika',
        'Ona tili va adabiyot': 'Ona tili va adabiyot',
        'Ingliz tili': 'Ingliz tili',
        'Fizika': 'Fizika',
        'Kimyo': 'Kimyo',
        'Biologiya': 'Biologiya',
        'Informatika': 'Informatika',
        'Tarix': 'Tarix',
        'Texnalogiya': 'Texnalogiya',
        'Texnologiya': 'Texnalogiya',
        'Geografiya': 'Geografiya',
        'Rus tili': 'Rus tili',
        'Jismoniy tarbiya': 'Jismoniy tarbiya',
        'Musiqa': 'Musiqa',
        'Tasviriy san\'at': 'Tasviriy san\'at',
    },
    'ru': {
        'Matematika': 'Математика',
        'Ona tili va adabiyot': 'Родной язык и литература',
        'Ingliz tili': 'Английский язык',
        'Fizika': 'Физика',
        'Kimyo': 'Химия',
        'Biologiya': 'Биология',
        'Informatika': 'Информатика',
        'Tarix': 'История',
        'Texnalogiya': 'Технология',
        'Texnologiya': 'Технология',
        'Geografiya': 'География',
        'Rus tili': 'Русский язык',
        'Jismoniy tarbiya': 'Физкультура',
        'Musiqa': 'Музыка',
        'Tasviriy san\'at': 'Изобразительное искусство',
    },
    'en': {
        'Matematika': 'Mathematics',
        'Ona tili va adabiyot': 'Native Language & Literature',
        'Ingliz tili': 'English Language',
        'Fizika': 'Physics',
        'Kimyo': 'Chemistry',
        'Biologiya': 'Biology',
        'Informatika': 'Computer Science',
        'Tarix': 'History',
        'Texnalogiya': 'Technology',
        'Texnologiya': 'Technology',
        'Geografiya': 'Geography',
        'Rus tili': 'Russian Language',
        'Jismoniy tarbiya': 'Physical Education',
        'Musiqa': 'Music',
        'Tasviriy san\'at': 'Visual Arts',
    }
}

DAY_TRANSLATIONS = {
    'uz': {1: 'Dushanba', 2: 'Seshanba', 3: 'Chorshanba', 4: 'Payshanba', 5: 'Juma', 6: 'Shanba', 7: 'Yakshanba'},
    'ru': {1: 'Понедельник', 2: 'Вторник', 3: 'Среда', 4: 'Четверг', 5: 'Пятница', 6: 'Суббота', 7: 'Воскресенье'},
    'en': {1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 4: 'Thursday', 5: 'Friday', 6: 'Saturday', 7: 'Sunday'},
}

STATUS_TRANSLATIONS = {
    'uz': {'present': 'Keldi', 'absent': 'Kelmadi', 'excused': 'Sababli', 'late': 'Kechikdi'},
    'ru': {'present': 'Присутствовал', 'absent': 'Отсутствовал', 'excused': 'По уважительной', 'late': 'Опоздал'},
    'en': {'present': 'Present', 'absent': 'Absent', 'excused': 'Excused', 'late': 'Late'},
}

ROLE_TRANSLATIONS = {
    'uz': {'student': "O'quvchi", 'teacher': 'Ustoz', 'admin': "Maktab Ma'muri"},
    'ru': {'student': 'Ученик', 'teacher': 'Учитель', 'admin': 'Администратор'},
    'en': {'student': 'Student', 'teacher': 'Teacher', 'admin': 'Administrator'},
}

@register.filter
def t_sub(name, lang='uz'):
    if not name:
        return ''
    lang_dict = SUBJECT_TRANSLATIONS.get(lang, SUBJECT_TRANSLATIONS['uz'])
    return lang_dict.get(str(name), str(name))

@register.filter
def t_day(day_num, lang='uz'):
    try:
        day_int = int(day_num)
        return DAY_TRANSLATIONS.get(lang, DAY_TRANSLATIONS['uz']).get(day_int, str(day_num))
    except (ValueError, TypeError):
        return str(day_num)

@register.filter
def t_status(status, lang='uz'):
    if not status:
        return ''
    return STATUS_TRANSLATIONS.get(lang, STATUS_TRANSLATIONS['uz']).get(str(status).lower(), str(status))

@register.filter
def t_role(role, lang='uz'):
    if not role:
        return ''
    return ROLE_TRANSLATIONS.get(lang, ROLE_TRANSLATIONS['uz']).get(str(role).lower(), str(role))

@register.filter
def dict_lookup(dictionary, key):
    if not dictionary:
        return None
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

