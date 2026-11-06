import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')
django.setup()

from apps.models import School, Subject, Classroom, User, Grade, Schedule, Homework, Attendance
from django.utils import timezone
from datetime import timedelta, date

def create_data():
    print("Namunaviy ma'lumotlar yaratilmoqda...")

    # 1. Maktablar
    school1, _ = School.objects.get_or_create(
        number=21,
        defaults={'name': "Ixtisoslashtirilgan umumta'lim maktabi", 'address': "Toshkent shahri, Chilonzor tumani", 'phone': "+998 71 200 21 21"}
    )
    school2, _ = School.objects.get_or_create(
        number=5,
        defaults={'name': "Davlat umumta'lim maktabi", 'address': "Toshkent shahri, Yunusobod tumani", 'phone': "+998 71 200 05 05"}
    )

    # 2. Fanlar
    subjects_data = [
        ("Matematika", "MATH", "fa-calculator"),
        ("Ona tili va adabiyot", "UZB", "fa-book-bookmark"),
        ("Ingliz tili", "ENG", "fa-earth-americas"),
        ("Fizika", "PHYS", "fa-atom"),
        ("Kimyo", "CHEM", "fa-flask-vial"),
        ("Biologiya", "BIO", "fa-dna"),
        ("Informatika", "CS", "fa-laptop-code"),
        ("Tarix", "HIST", "fa-landmark"),
    ]
    subjects = {}
    for name, code, icon in subjects_data:
        sub, _ = Subject.objects.get_or_create(name=name, defaults={'code': code, 'icon': icon})
        subjects[name] = sub

    # 3. Foydalanuvchilar: Admin
    if not User.objects.filter(username='admin').exists():
        admin_user = User.objects.create_superuser('admin', 'admin@maktab.uz', 'admin123')
        admin_user.role = 'admin'
        admin_user.first_name = "Maktab"
        admin_user.last_name = "Direktori"
        admin_user.school = school1
        admin_user.save()
        print("Admin yaratildi: login: admin, parol: admin123")

    # 4. Ustozlar
    teacher1, created = User.objects.get_or_create(
        username='teacher1',
        defaults={
            'first_name': "Anvar",
            'last_name': "Qodirov",
            'role': 'teacher',
            'school': school1,
            'subject': subjects["Matematika"],
            'phone': "+998 90 111 22 33",
            'bio': "15 yillik tajribaga ega Oliy toifali matematika o'qituvchisi."
        }
    )
    if created:
        teacher1.set_password('12345678')
        teacher1.save()

    teacher2, created = User.objects.get_or_create(
        username='teacher2',
        defaults={
            'first_name': "Nodira",
            'last_name': "Rahimova",
            'role': 'teacher',
            'school': school1,
            'subject': subjects["Ingliz tili"],
            'phone': "+998 90 222 33 44",
            'bio': "IELTS 8.5 sohibi, zamonaviy interaktiv metodlar mutaxassisi."
        }
    )
    if created:
        teacher2.set_password('12345678')
        teacher2.save()

    # 5. Sinflar (28 nafar limit bilan)
    class_9a, _ = Classroom.objects.get_or_create(
        name="9-A",
        school=school1,
        defaults={'grade_level': 9, 'class_teacher': teacher1, 'max_students': 28}
    )
    class_9b, _ = Classroom.objects.get_or_create(
        name="9-B",
        school=school1,
        defaults={'grade_level': 9, 'class_teacher': teacher2, 'max_students': 28}
    )

    # 6. O'quvchilar
    student1, created = User.objects.get_or_create(
        username='student1',
        defaults={
            'first_name': "Jasur",
            'last_name': "Aliyev",
            'role': 'student',
            'school': school1,
            'classroom': class_9a,
            'phone': "+998 99 987 65 43",
            'address': "Toshkent shahri, Chilonzor 9-mavze",
            'birth_date': date(2010, 5, 14),
            'bio': "Dasturlash va aniq fanlarga qiziqaman."
        }
    )
    if created:
        student1.set_password('12345678')
        student1.save()

    # Yana 5 ta o'quvchi qo'shamiz (9-A sinfiga)
    students_names = [
        ("Madina", "Karimova", "student2"),
        ("Sardor", "Umarov", "student3"),
        ("Zilola", "Rustamova", "student4"),
        ("Bobur", "Toshmatov", "student5"),
        ("Kamola", "Saidova", "student6"),
    ]
    for fn, ln, un in students_names:
        st, cr = User.objects.get_or_create(
            username=un,
            defaults={
                'first_name': fn,
                'last_name': ln,
                'role': 'student',
                'school': school1,
                'classroom': class_9a,
                'phone': "+998 90 555 00 11",
                'address': "Toshkent shahri"
            }
        )
        if cr:
            st.set_password('12345678')
            st.save()

    # 7. Baholar (Grade)
    Grade.objects.get_or_create(
        student=student1,
        subject=subjects["Matematika"],
        teacher=teacher1,
        date=timezone.now().date(),
        defaults={'grade': 5, 'comment': "Tenglamalar sistemasini a'lo yechdi"}
    )
    Grade.objects.get_or_create(
        student=student1,
        subject=subjects["Ingliz tili"],
        teacher=teacher2,
        date=timezone.now().date() - timedelta(days=1),
        defaults={'grade': 5, 'comment': "Speaking va Vocabulary mavzusi"}
    )
    Grade.objects.get_or_create(
        student=student1,
        subject=subjects["Fizika"],
        teacher=teacher1,
        date=timezone.now().date() - timedelta(days=2),
        defaults={'grade': 4, 'comment': "Nyuton qonunlari bo'yicha masalalar"}
    )
    Grade.objects.get_or_create(
        student=student1,
        subject=subjects["Matematika"],
        teacher=teacher1,
        date=timezone.now().date() - timedelta(days=4),
        defaults={'grade': 5, 'comment': "Nazorat ishi"}
    )

    # 8. Dars jadvali (Schedule)
    schedule_data = [
        # Dushanba (1)
        (1, 1, subjects["Matematika"], teacher1, "204", "08:30:00", "09:15:00"),
        (1, 2, subjects["Ona tili va adabiyot"], None, "205", "09:25:00", "10:10:00"),
        (1, 3, subjects["Ingliz tili"], teacher2, "301", "10:20:00", "11:05:00"),
        (1, 4, subjects["Fizika"], teacher1, "204", "11:25:00", "12:10:00"),
        # Seshanba (2)
        (2, 1, subjects["Informatika"], None, "Kompyuter xonasi", "08:30:00", "09:15:00"),
        (2, 2, subjects["Matematika"], teacher1, "204", "09:25:00", "10:10:00"),
        (2, 3, subjects["Kimyo"], None, "Kimyo laboratoriyasi", "10:20:00", "11:05:00"),
        # Chorshanba (3)
        (3, 1, subjects["Ingliz tili"], teacher2, "301", "08:30:00", "09:15:00"),
        (3, 2, subjects["Biologiya"], None, "108", "09:25:00", "10:10:00"),
        (3, 3, subjects["Tarix"], None, "210", "10:20:00", "11:05:00"),
        # Payshanba (4)
        (4, 1, subjects["Matematika"], teacher1, "204", "08:30:00", "09:15:00"),
        (4, 2, subjects["Fizika"], teacher1, "204", "09:25:00", "10:10:00"),
        # Juma (5)
        (5, 1, subjects["Ona tili va adabiyot"], None, "205", "08:30:00", "09:15:00"),
        (5, 2, subjects["Informatika"], None, "Kompyuter xonasi", "09:25:00", "10:10:00"),
        # Shanba (6)
        (6, 1, subjects["Ingliz tili"], teacher2, "301", "08:30:00", "09:15:00"),
        (6, 2, subjects["Tarix"], None, "210", "09:25:00", "10:10:00"),
    ]
    for d, num, sub, tchr, room, st, et in schedule_data:
        Schedule.objects.get_or_create(
            classroom=class_9a,
            day_of_week=d,
            lesson_number=num,
            defaults={'subject': sub, 'teacher': tchr, 'room_number': room, 'start_time': st, 'end_time': et}
        )

    # 9. Uy vazifalari (Homework)
    Homework.objects.get_or_create(
        classroom=class_9a,
        subject=subjects["Matematika"],
        teacher=teacher1,
        title="Kvadrat tenglamalarni yechish",
        defaults={
            'description': "Darslikdagi 145-148 mashqlarni to'liq yechish va daftarga yozish. Javoblarni tekshirish.",
            'due_date': timezone.now().date() + timedelta(days=2)
        }
    )
    Homework.objects.get_or_create(
        classroom=class_9a,
        subject=subjects["Ingliz tili"],
        teacher=teacher2,
        title="Unit 4: Future Technologies Essay",
        defaults={
            'description': "Write an essay of 150-200 words on how AI is changing education and daily life.",
            'due_date': timezone.now().date() + timedelta(days=3)
        }
    )

    # 10. Davomat (Attendance)
    today = timezone.now().date()
    Attendance.objects.get_or_create(student=student1, date=today, defaults={'classroom': class_9a, 'status': 'present'})
    Attendance.objects.get_or_create(student=student1, date=today - timedelta(days=1), defaults={'classroom': class_9a, 'status': 'present'})
    Attendance.objects.get_or_create(student=student1, date=today - timedelta(days=2), defaults={'classroom': class_9a, 'status': 'late', 'note': "10 daqiqa kechikdi"})
    Attendance.objects.get_or_create(student=student1, date=today - timedelta(days=3), defaults={'classroom': class_9a, 'status': 'present'})

    print("Barcha namunaviy ma'lumotlar muvaffaqiyatli tayyorlandi!")

if __name__ == '__main__':
    create_data()
