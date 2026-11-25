from datetime import time
from apps.models import School, Subject, Classroom, User, Schedule


DEFAULT_SCHOOLS = [
    {
        'number': 21,
        'name': "Ixtisoslashtirilgan umumta'lim maktabi",
        'address': "Toshkent shahri, Chilonzor tumani",
        'phone': "+998 71 200 21 21",
    },
    {
        'number': 5,
        'name': "Davlat umumta'lim maktabi",
        'address': "Toshkent shahri, Yunusobod tumani",
        'phone': "+998 71 200 05 05",
    },
]

DEFAULT_SUBJECTS = [
    ("Matematika", "MATH", "fa-calculator"),
    ("Ona tili va adabiyot", "UZB", "fa-book-bookmark"),
    ("Ingliz tili", "ENG", "fa-earth-americas"),
    ("Fizika", "PHYS", "fa-atom"),
    ("Kimyo", "CHEM", "fa-flask-vial"),
    ("Biologiya", "BIO", "fa-dna"),
    ("Informatika", "CS", "fa-laptop-code"),
    ("Tarix", "HIST", "fa-landmark"),
    ("Geografiya", "GEO", "fa-globe"),
    ("Rus tili", "RUS", "fa-language"),
    ("Jismoniy tarbiya", "PE", "fa-person-running"),
    ("Texnologiya", "TECH", "fa-compass-drafting"),
]

# Standart dars vaqtlari (1-6 darslar)
LESSON_SLOTS = [
    (1, time(8, 30), time(9, 15)),
    (2, time(9, 25), time(10, 10)),
    (3, time(10, 20), time(11, 5)),
    (4, time(11, 20), time(12, 5)),
    (5, time(12, 15), time(13, 0)),
    (6, time(13, 10), time(13, 55)),
]

DEFAULT_ROOMS = {
    "Matematika": "204",
    "Ona tili va adabiyot": "205",
    "Ingliz tili": "301",
    "Fizika": "208",
    "Kimyo": "Lab-1",
    "Biologiya": "108",
    "Informatika": "IT-1",
    "Tarix": "210",
    "Geografiya": "212",
    "Rus tili": "304",
    "Jismoniy tarbiya": "Sport zal",
    "Texnologiya": "102",
}


def ensure_default_catalog():
    """Bazadagi asosiy maktab va fanlar ro'yxatini kafolatlaydi."""
    if not School.objects.exists():
        for s in DEFAULT_SCHOOLS:
            School.objects.get_or_create(
                number=s['number'],
                defaults={
                    'name': s['name'],
                    'address': s['address'],
                    'phone': s['phone'],
                },
            )

    subjects = list(Subject.objects.all())
    if not subjects:
        for name, code, icon in DEFAULT_SUBJECTS:
            sub, _ = Subject.objects.get_or_create(
                name=name,
                defaults={'code': code, 'icon': icon},
            )
            subjects.append(sub)
    return subjects


def _pick_teacher_for_subject(subject, classroom):
    """Fan bo'yicha mos ustozni tanlaydi (avval shu maktabdan, keyin umumiy)."""
    if classroom.class_teacher and classroom.class_teacher.subject_id == subject.id:
        return classroom.class_teacher

    teacher = User.objects.filter(
        role='teacher',
        subject=subject,
        school=classroom.school,
    ).order_by('id').first()
    if teacher:
        return teacher

    return User.objects.filter(role='teacher', subject=subject).order_by('id').first()


def generate_full_weekly_schedule(classroom, overwrite=False, lessons_per_day=5):
    """
    Sinf uchun Dushanbadan Shanbagacha (1-6 kunlar) to'liq dars jadvalini yaratadi.
    Yakshanba (7-kun) har doim dam olish kuni sifatida bo'sh qoladi.
    """
    if not classroom:
        return 0

    if overwrite:
        Schedule.objects.filter(classroom=classroom).delete()
    elif Schedule.objects.filter(classroom=classroom).exists():
        return 0

    subjects = ensure_default_catalog()
    if not subjects:
        return 0

    # Ustozli fanlarni oldinga chiqaramiz, lekin barcha fanlar aylanada qatnashadi
    ordered_subjects = sorted(
        subjects,
        key=lambda s: (0 if User.objects.filter(role='teacher', subject=s).exists() else 1, s.id),
    )

    # Sinfga qarab boshlang'ich ofset — sinflar jadvali bir xil bo'lib qolmasligi uchun
    offset = (classroom.id or 0) % len(ordered_subjects)
    rotated_subjects = ordered_subjects[offset:] + ordered_subjects[:offset]

    created_count = 0
    sub_idx = 0
    slots = LESSON_SLOTS[:max(4, min(6, lessons_per_day))]

    for day_num in range(1, 7):  # 1 (Dushanba) .. 6 (Shanba); 7 (Yakshanba) dam olish kuni!
        day_lessons_count = len(slots) if day_num < 6 else min(4, len(slots))
        used_today = set()
        for lesson_num, start_t, end_t in slots[:day_lessons_count]:
            # Bir kunda bir xil fan ketma-ket tushib qolmasligi uchun tanlash
            chosen_sub = None
            for _ in range(len(rotated_subjects)):
                cand = rotated_subjects[sub_idx % len(rotated_subjects)]
                sub_idx += 1
                if cand.id not in used_today or len(rotated_subjects) <= day_lessons_count:
                    chosen_sub = cand
                    used_today.add(cand.id)
                    break
            if not chosen_sub:
                chosen_sub = rotated_subjects[sub_idx % len(rotated_subjects)]
                sub_idx += 1

            teacher = _pick_teacher_for_subject(chosen_sub, classroom)
            room = DEFAULT_ROOMS.get(chosen_sub.name, str(200 + (chosen_sub.id % 20)))

            _, created = Schedule.objects.get_or_create(
                classroom=classroom,
                day_of_week=day_num,
                lesson_number=lesson_num,
                defaults={
                    'subject': chosen_sub,
                    'teacher': teacher,
                    'room_number': room,
                    'start_time': start_t,
                    'end_time': end_t,
                },
            )
            if created:
                created_count += 1

    return created_count


def ensure_classroom_schedule(classroom):
    """Agar sinfning jadvali bo'sh bo'lsa, avtomatik to'liq jadval yaratadi."""
    if classroom and not Schedule.objects.filter(classroom=classroom).exists():
        return generate_full_weekly_schedule(classroom)
    return 0


def assign_teacher_to_schedules(teacher):
    """
    Yangi ustoz yaratilganda, uning faniga mos bo'sh jadval uyachalarini
    yoki sinflardagi shu fanni unga biriktiradi, shunda ustoz kabinetida ham jadval bo'sh qolmaydi.
    """
    if not teacher or teacher.role != 'teacher' or not teacher.subject:
        return 0

    assigned = 0
    # 1. Avval ustozsiz qolgan shu fan darslariga biriktiramiz
    unassigned_qs = Schedule.objects.filter(subject=teacher.subject, teacher__isnull=True)
    if teacher.school:
        school_qs = unassigned_qs.filter(classroom__school=teacher.school)
        if school_qs.exists():
            assigned += school_qs.update(teacher=teacher)
    if assigned == 0 and unassigned_qs.exists():
        assigned += unassigned_qs.update(teacher=teacher)

    # 2. Agar hali ham bu ustozning dars jadvali yo'q bo'lsa, sinflardan jadvalga qo'shamiz
    if not Schedule.objects.filter(teacher=teacher).exists():
        classrooms = Classroom.objects.all()
        if teacher.school:
            school_classes = classrooms.filter(school=teacher.school)
            if school_classes.exists():
                classrooms = school_classes

        for cls in classrooms[:3]:
            ensure_classroom_schedule(cls)
            # Shu fandan dars bo'lsa, lekin teacher bo'lmasa yoki boshqa dars bo'lsa
            qs = Schedule.objects.filter(classroom=cls, subject=teacher.subject)
            if qs.exists():
                # Bitta sinfda bu fanga teacher hali yo'q bo'lsa yoki kam bo'lsa biriktiramiz
                null_qs = qs.filter(teacher__isnull=True)
                if null_qs.exists():
                    assigned += null_qs.update(teacher=teacher)
                else:
                    # Birinchi darsini yangi ustozga biriktiramiz (bo'sh qolmasligi uchun)
                    first_slot = qs.first()
                    if first_slot:
                        first_slot.teacher = teacher
                        first_slot.save(update_fields=['teacher'])
                        assigned += 1
            else:
                # Sinfda bu fan bo'lmasa, bo'sh slotga (6-soatga) qo'shamiz (Mon, Wed, Fri)
                for day_num in (1, 3, 5):
                    used_nums = set(
                        Schedule.objects.filter(classroom=cls, day_of_week=day_num)
                        .values_list('lesson_number', flat=True)
                    )
                    for lesson_num, start_t, end_t in LESSON_SLOTS:
                        if lesson_num not in used_nums:
                            Schedule.objects.create(
                                classroom=cls,
                                day_of_week=day_num,
                                lesson_number=lesson_num,
                                subject=teacher.subject,
                                teacher=teacher,
                                room_number=DEFAULT_ROOMS.get(teacher.subject.name, "201"),
                                start_time=start_t,
                                end_time=end_t,
                            )
                            assigned += 1
                            break

    return assigned
