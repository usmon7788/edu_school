import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')
django.setup()

from apps.models import School, Subject, Classroom, User, Grade, Schedule, Homework, Attendance
from apps.schedule_utils import DEFAULT_SCHOOLS, DEFAULT_SUBJECTS, generate_full_weekly_schedule
from django.utils import timezone
from datetime import timedelta, date


def create_data():
    print("Namunaviy ma'lumotlar yaratilmoqda...")

    # 1. Maktablar
    schools = []
    for s_data in DEFAULT_SCHOOLS:
        school, _ = School.objects.get_or_create(
            number=s_data['number'],
            defaults={
                'name': s_data['name'],
                'address': s_data['address'],
                'phone': s_data['phone'],
            },
        )
        schools.append(school)
    school1 = schools[0]
    school2 = schools[1] if len(schools) > 1 else school1

    # Mavjud admin foydalanuvchilariga maktab biriktirish (agar bo'sh bo'lsa)
    User.objects.filter(role='admin', school__isnull=True).update(school=school1)

    # 2. Fanlar (12 ta asosiy maktab fani)
    subjects = {}
    for name, code, icon in DEFAULT_SUBJECTS:
        sub, _ = Subject.objects.get_or_create(
            name=name,
            defaults={'code': code, 'icon': icon},
        )
        subjects[name] = sub

    # 3. Admin (agar umuman admin bo'lmasa)
    if not User.objects.filter(username='admin').exists():
        admin_user = User.objects.create_superuser('admin', 'admin@maktab.uz', 'admin123')
        admin_user.role = 'admin'
        admin_user.first_name = "Maktab"
        admin_user.last_name = "Direktori"
        admin_user.school = school1
        admin_user.save()
        print("Admin yaratildi: login: admin, parol: admin123")

    # 4. Ustozlar (har bir asosiy fan uchun ustoz)
    teachers_spec = [
        ('teacher1', "Anvar", "Qodirov", "Matematika", "+998 90 111 22 33",
         "15 yillik tajribaga ega Oliy toifali matematika o'qituvchisi.", school1),
        ('teacher2', "Nodira", "Rahimova", "Ingliz tili", "+998 90 222 33 44",
         "IELTS 8.5 sohibi, zamonaviy interaktiv metodlar mutaxassisi.", school1),
        ('teacher3', "Dilshod", "Karimov", "Fizika", "+998 90 333 44 55",
         "Fizika va astronomiya fanlari bo'yicha olimpiada murabbiyi.", school1),
        ('teacher4', "Malika", "Tursunova", "Ona tili va adabiyot", "+998 90 444 55 66",
         "Ona tili va adabiyot fani o'qituvchisi, ko'plab maqolalar muallifi.", school1),
        ('teacher5', "Azizbek", "Nazarov", "Informatika", "+998 90 555 66 77",
         "Dasturlash va IT texnologiyalar yo'nalishi ustozi.", school1),
        ('teacher6', "Gulnora", "Xasanova", "Kimyo", "+998 90 666 77 88",
         "Kimyo laboratoriyasi rahbari va tajribali pedagog.", school1),
        ('teacher7', "Rustam", "Alimov", "Tarix", "+998 90 777 88 99",
         "O'zbekiston va jahon tarixi fani o'qituvchisi.", school1),
        ('teacher8', "Zuhra", "Mirzayeva", "Biologiya", "+998 90 888 99 00",
         "Biologiya va ekologiya fanlari o'qituvchisi.", school1),
    ]
    teachers = {}
    for un, fn, ln, sub_name, phone, bio, sch in teachers_spec:
        t_obj, created = User.objects.get_or_create(
            username=un,
            defaults={
                'first_name': fn,
                'last_name': ln,
                'role': 'teacher',
                'school': sch,
                'subject': subjects[sub_name],
                'phone': phone,
                'bio': bio,
                'initial_password': '12345678',
            },
        )
        if created:
            t_obj.set_password('12345678')
            t_obj.save()
        elif not t_obj.initial_password:
            t_obj.initial_password = '12345678'
            t_obj.save(update_fields=['initial_password'])
        teachers[un] = t_obj

    teacher1 = teachers['teacher1']
    teacher2 = teachers['teacher2']
    teacher3 = teachers['teacher3']
    teacher4 = teachers['teacher4']
    teacher5 = teachers['teacher5']

    # 5. Sinflar (8-A, 9-A, 9-B, 10-A, 11-A)
    classrooms_spec = [
        ("9-A", 9, school1, teacher1),
        ("9-B", 9, school1, teacher2),
        ("10-A", 10, school1, teacher3),
        ("11-A", 11, school1, teacher4),
        ("8-A", 8, school1, teacher5),
    ]
    classrooms = {}
    for cname, glevel, sch, cteacher in classrooms_spec:
        cls, _ = Classroom.objects.get_or_create(
            name=cname,
            school=sch,
            defaults={'grade_level': glevel, 'class_teacher': cteacher, 'max_students': 28},
        )
        classrooms[cname] = cls

    class_9a = classrooms["9-A"]
    class_9b = classrooms["9-B"]
    class_10a = classrooms["10-A"]
    class_11a = classrooms["11-A"]
    class_8a = classrooms["8-A"]

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
            'bio': "Dasturlash va aniq fanlarga qiziqaman.",
            'initial_password': '12345678',
        },
    )
    if created:
        student1.set_password('12345678')
        student1.save()

    students_list = [
        ("Madina", "Karimova", "student2", class_9a),
        ("Sardor", "Umarov", "student3", class_9a),
        ("Zilola", "Rustamova", "student4", class_9a),
        ("Bobur", "Toshmatov", "student5", class_9a),
        ("Kamola", "Saidova", "student6", class_9a),
        ("Dilnoza", "Yusupova", "student7", class_9b),
        ("Behruz", "Ismoilov", "student8", class_9b),
        ("Sevinch", "Raxmatova", "student9", class_10a),
        ("Doston", "Mamatov", "student10", class_10a),
        ("Asal", "Qosimova", "student11", class_11a),
        ("Temur", "Ergashev", "student12", class_11a),
        ("Farzona", "Sobirova", "student13", class_8a),
        ("Javohir", "Xolmatov", "student14", class_8a),
    ]
    for fn, ln, un, cls in students_list:
        st, cr = User.objects.get_or_create(
            username=un,
            defaults={
                'first_name': fn,
                'last_name': ln,
                'role': 'student',
                'school': school1,
                'classroom': cls,
                'phone': "+998 90 555 00 11",
                'address': "Toshkent shahri",
                'initial_password': '12345678',
            },
        )
        if cr:
            st.set_password('12345678')
            st.save()

    # 7. To'liq haftalik dars jadvali (Dushanba-Shanba to'liq, Yakshanba dam olish kuni)
    for cls in Classroom.objects.all():
        generate_full_weekly_schedule(cls, overwrite=True, lessons_per_day=5)

    # 8. Baholar (Grade)
    today = timezone.now().date()
    grades_spec = [
        (student1, "Matematika", teacher1, today, 5, "Tenglamalar sistemasini a'lo yechdi"),
        (student1, "Ingliz tili", teacher2, today - timedelta(days=1), 5, "Speaking va Vocabulary mavzusi"),
        (student1, "Fizika", teacher3, today - timedelta(days=2), 4, "Nyuton qonunlari bo'yicha masalalar"),
        (student1, "Informatika", teacher5, today - timedelta(days=3), 5, "Python algoritmlari"),
        (student1, "Ona tili va adabiyot", teacher4, today - timedelta(days=4), 5, "Insho yozish"),
    ]
    for st, sub_name, tch, dt, val, cmt in grades_spec:
        Grade.objects.get_or_create(
            student=st,
            subject=subjects[sub_name],
            teacher=tch,
            date=dt,
            defaults={'grade': val, 'comment': cmt},
        )

    # 9. Uy vazifalari (Homework)
    homeworks_spec = [
        (class_9a, "Matematika", teacher1, "Kvadrat tenglamalarni yechish",
         "Darslikdagi 145-148 mashqlarni to'liq yechish va daftarga yozish. Javoblarni tekshirish.", 2),
        (class_9a, "Ingliz tili", teacher2, "Unit 4: Future Technologies Essay",
         "Write an essay of 150-200 words on how AI is changing education and daily life.", 3),
        (class_9a, "Fizika", teacher3, "Mexanik harakat va tezlik",
         "12-mavzuni o'qib kelish va 45-betdagi 1-4 masalalarni yechish.", 2),
        (class_9b, "Ingliz tili", teacher2, "Grammar: Conditional Sentences",
         "Workbook pages 34-36, exercises 1-5.", 3),
        (class_10a, "Fizika", teacher3, "Termodinamika qonunlari",
         "Laboratoriya daftariga tajriba xulosalarini rasmiylashtirish.", 4),
    ]
    for cls, sub_name, tch, title, desc, days_ahead in homeworks_spec:
        Homework.objects.get_or_create(
            classroom=cls,
            subject=subjects[sub_name],
            teacher=tch,
            title=title,
            defaults={
                'description': desc,
                'due_date': today + timedelta(days=days_ahead),
            },
        )

    # 10. Davomat (Attendance)
    Attendance.objects.get_or_create(
        student=student1,
        date=today,
        subject=subjects["Matematika"],
        defaults={'classroom': class_9a, 'teacher': teacher1, 'status': 'present'},
    )
    Attendance.objects.get_or_create(
        student=student1,
        date=today - timedelta(days=1),
        subject=subjects["Ingliz tili"],
        defaults={'classroom': class_9a, 'teacher': teacher2, 'status': 'present'},
    )
    Attendance.objects.get_or_create(
        student=student1,
        date=today - timedelta(days=2),
        subject=subjects["Fizika"],
        defaults={'classroom': class_9a, 'teacher': teacher3, 'status': 'late', 'note': "10 daqiqa kechikdi"},
    )

    print("Barcha namunaviy ma'lumotlar muvaffaqiyatli tayyorlandi!")
    print(f"Maktablar: {School.objects.count()} | Fanlar: {Subject.objects.count()} | Sinflar: {Classroom.objects.count()}")
    print(f"Ustozlar: {User.objects.filter(role='teacher').count()} | O'quvchilar: {User.objects.filter(role='student').count()} | Dars jadvallari: {Schedule.objects.count()}")


if __name__ == '__main__':
    create_data()
    try:
        from create_sample_posts import populate_posts
        populate_posts()
    except Exception as exc:
        print(f"Postlarni yaratishda ogohlantirish: {exc}")
