from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Q
from apps.models import User, School, Classroom, Subject, Grade, Schedule, Homework, Attendance
from apps.schedule_utils import (
    ensure_default_catalog,
    generate_full_weekly_schedule,
    ensure_classroom_schedule,
    assign_teacher_to_schedules,
    LESSON_SLOTS,
)
import random
import string


def is_admin_or_staff(user):
    return user.is_authenticated and (user.role == 'admin' or user.is_staff or user.is_superuser)


def generate_password(length=6):
    """Foydalanuvchi so'ragandek, tasodifiy sonlar (masalan: 6 xonali raqam) bilan parol yaratish"""
    return str(random.randint(100000, 999999))


def generate_username(first_name='user'):
    """Ism kiritilganda unga tasodifiy raqam qo'shib login generatsiya qilish (masalan: ali_4829)"""
    base = ''.join(c for c in first_name.lower() if c.isalnum()) or 'user'
    while True:
        cand = f"{base}_{random.randint(1000, 9999)}"
        if not User.objects.filter(username=cand).exists():
            return cand


@login_required
@user_passes_test(is_admin_or_staff)
def admin_panel_dashboard(request):
    ensure_default_catalog()
    schools = School.objects.all()
    subjects = Subject.objects.all().order_by('name')
    classrooms = Classroom.objects.select_related('school', 'class_teacher').annotate(
        real_student_count=Count('students', filter=Q(students__role='student'))
    ).all()
    teachers = User.objects.filter(role='teacher').select_related('subject', 'school')
    students = User.objects.filter(role='student')

    class_stats = []
    for c in classrooms:
        count = getattr(c, 'real_student_count', 0)
        max_c = c.max_students or 28
        percentage = int((count / max_c) * 100) if max_c > 0 else 0
        class_stats.append({
            'classroom': c,
            'count': count,
            'max': max_c,
            'percentage': min(100, percentage),
            'available': max(0, max_c - count),
            'is_full': count >= max_c,
        })

    context = {
        'total_schools': schools.count(),
        'total_classrooms': classrooms.count(),
        'total_teachers': teachers.count(),
        'total_students': students.count(),
        'total_subjects': subjects.count(),
        'total_schedules': Schedule.objects.count(),
        'class_stats': class_stats,
        'teachers': teachers,
        'schools': schools,
        'subjects': subjects,
    }
    return render(request, 'admin_panel/dashboard.html', context)


# ── Ustoz yaratish ──────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_admin_or_staff)
def create_teacher(request):
    ensure_default_catalog()
    schools = School.objects.all()
    subjects = Subject.objects.all()
    new_credentials = None

    if request.method == 'POST':
        first_name  = request.POST.get('first_name', '').strip()
        last_name   = request.POST.get('last_name', '').strip()
        username    = request.POST.get('username', '').strip()
        phone       = request.POST.get('phone', '').strip()
        school_id   = request.POST.get('school_id')
        subject_id  = request.POST.get('subject_id')
        
        # Parol avtomatik ravishda 6 xonali tasodifiy son bilan yaratiladi
        password = generate_password()

        # Agar username kiritilmagan bo'lsa, ismdan foydalanib yagona login yasaymiz
        if not username:
            username = generate_username(first_name or 'ustoz')

        if not subject_id:
            messages.error(request, "Dars beradigan fanni tanlash shart!")
        elif User.objects.filter(username=username).exists():
            messages.error(request, f"'{username}' logini allaqachon band! Boshqa login kiriting.")
        else:
            teacher = User(
                username=username,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                role='teacher',
                initial_password=password,
            )
            teacher.set_password(password)
            if school_id:
                teacher.school_id = school_id
            elif schools.exists():
                teacher.school = schools.first()
            if subject_id:
                teacher.subject_id = subject_id
            teacher.save()
            assigned_lessons = assign_teacher_to_schedules(teacher)
            new_credentials = {
                'full_name': teacher.full_name,
                'username': username,
                'password': password,
                'role': "Ustoz",
                'subject': teacher.subject.name if teacher.subject else "—",
            }
            messages.success(
                request,
                f"Ustoz {teacher.full_name} muvaffaqiyatli yaratildi! Login: {username} | Parol: {password}"
                + (f" ({assigned_lessons} ta dars jadvaliga biriktirildi)" if assigned_lessons else "")
            )

    return render(request, 'admin_panel/create_teacher.html', {
        'schools': schools,
        'subjects': subjects,
        'new_credentials': new_credentials,
    })


# ── O'quvchi yaratish ───────────────────────────────────────────────────────
@login_required
@user_passes_test(is_admin_or_staff)
def create_student(request):
    ensure_default_catalog()
    schools = School.objects.all()
    classrooms = Classroom.objects.select_related('school').all()
    new_credentials = None

    if request.method == 'POST':
        first_name   = request.POST.get('first_name', '').strip()
        last_name    = request.POST.get('last_name', '').strip()
        username     = request.POST.get('username', '').strip()
        phone        = request.POST.get('phone', '').strip()
        classroom_id = request.POST.get('classroom_id')
        school_id    = request.POST.get('school_id')

        # Parol avtomatik ravishda 6 xonali tasodifiy son bilan yaratiladi
        password = generate_password()

        if not username:
            username = generate_username(first_name or 'oquvchi')

        if not classroom_id:
            messages.error(request, "O'quvchi uchun sinf tanlanishi shart!")
        elif User.objects.filter(username=username).exists():
            messages.error(request, f"'{username}' logini allaqachon band! Boshqa login kiriting.")
        else:
            classroom = Classroom.objects.filter(pk=classroom_id).first()
            if classroom and classroom.student_count() >= classroom.max_students:
                messages.error(request, f"'{classroom.name}' sinfi to'lgan! (Maksimal {classroom.max_students} nafar limit)")
                return render(request, 'admin_panel/create_student.html', {
                    'schools': schools, 'classrooms': classrooms, 'new_credentials': None
                })

            student = User(
                username=username,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                role='student',
                classroom=classroom,
                school=classroom.school if classroom else (School.objects.filter(pk=school_id).first() if school_id else None),
                initial_password=password,
            )
            student.set_password(password)
            student.save()
            if classroom:
                ensure_classroom_schedule(classroom)
            new_credentials = {
                'full_name': student.full_name,
                'username': username,
                'password': password,
                'role': "O'quvchi",
                'classroom': classroom.name if classroom else "—",
            }
            messages.success(request, f"O'quvchi {student.full_name} muvaffaqiyatli yaratildi! Login: {username} | Parol: {password}")

    return render(request, 'admin_panel/create_student.html', {
        'schools': schools,
        'classrooms': classrooms,
        'new_credentials': new_credentials,
    })


# ── Sinf yaratish (Classroom Create) ─────────────────────────────────────────
@login_required
@user_passes_test(is_admin_or_staff)
def create_classroom(request):
    ensure_default_catalog()
    schools = School.objects.all()
    teachers = User.objects.filter(role='teacher').select_related('subject')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        grade_level = request.POST.get('grade_level', '1').strip()
        school_id = request.POST.get('school_id')
        teacher_id = request.POST.get('teacher_id')
        max_students = request.POST.get('max_students', '28').strip()

        if not name:
            messages.error(request, "Sinf nomi kiritilishi shart!")
        elif not school_id:
            messages.error(request, "Maktab tanlanishi shart!")
        elif Classroom.objects.filter(name=name, school_id=school_id).exists():
            messages.error(request, f"'{name}' sinfi ushbu maktabda allaqachon mavjud!")
        else:
            school = get_object_or_404(School, pk=school_id)
            curator = None
            if teacher_id:
                curator = User.objects.filter(pk=teacher_id, role='teacher').first()
                if curator:
                    # Agar bu o'qituvchi boshqa sinfga rahbar bo'lsa, eskisidan ajratamiz
                    old_class = Classroom.objects.filter(class_teacher=curator).first()
                    if old_class:
                        messages.warning(request, f"{curator.full_name} avval '{old_class.name}' sinfiga rahbar edi. Rahbarlik ushbu yangi sinfga biriktirildi.")
                        old_class.class_teacher = None
                        old_class.save()

            classroom = Classroom.objects.create(
                name=name,
                grade_level=int(grade_level) if grade_level.isdigit() else 1,
                school=school,
                class_teacher=curator,
                max_students=int(max_students) if max_students.isdigit() else 28
            )
            created_lessons = generate_full_weekly_schedule(classroom)
            messages.success(
                request,
                f"'{classroom.name}' sinfi muvaffaqiyatli yaratildi! "
                f"Kurator: {curator.full_name if curator else 'Tanlanmagan'} | "
                f"Dushanba-Shanba jadvali ({created_lessons} ta dars) avtomatik tuzildi."
            )
            return redirect('classroom_manage', class_id=classroom.id)

    return render(request, 'admin_panel/create_classroom.html', {
        'schools': schools,
        'teachers': teachers,
    })


@login_required
@user_passes_test(is_admin_or_staff)
def classroom_manage(request, class_id):
    classroom = get_object_or_404(Classroom, pk=class_id)
    students = classroom.students.filter(role='student').order_by('last_name', 'first_name')
    teachers = User.objects.filter(role='teacher')

    current_count = students.count()
    max_capacity = classroom.max_students or 28
    is_full = current_count >= max_capacity
    available_seats = max(0, max_capacity - current_count)
    unassigned_students = User.objects.filter(role='student', classroom__isnull=True)

    return render(request, 'admin_panel/classroom_detail.html', {
        'classroom': classroom,
        'students': students,
        'teachers': teachers,
        'current_count': current_count,
        'max_capacity': max_capacity,
        'is_full': is_full,
        'available_seats': available_seats,
        'unassigned_students': unassigned_students,
    })


@login_required
@user_passes_test(is_admin_or_staff)
def add_student_to_class(request, class_id):
    classroom = get_object_or_404(Classroom, pk=class_id)

    if classroom.student_count() >= classroom.max_students:
        messages.error(request, f"Xatolik: '{classroom.name}' sinfida joy qolmagan! Maksimal {classroom.max_students} nafar.")
        return redirect('classroom_manage', class_id=classroom.id)

    if request.method == 'POST':
        action_type = request.POST.get('action_type')

        if action_type == 'create_new':
            username   = request.POST.get('username')
            first_name = request.POST.get('first_name')
            last_name  = request.POST.get('last_name')
            password   = request.POST.get('password', '12345678')
            phone      = request.POST.get('phone', '')

            if User.objects.filter(username=username).exists():
                messages.error(request, f"'{username}' logini allaqachon mavjud!")
            else:
                student = User.objects.create_user(
                    username=username, first_name=first_name, last_name=last_name,
                    password=password, role='student',
                    classroom=classroom, school=classroom.school, phone=phone,
                    initial_password=password
                )
                ensure_classroom_schedule(classroom)
                messages.success(request, f"O'quvchi {student.full_name} qo'shildi! Login: {username} | Parol: {password}")

        elif action_type == 'assign_existing':
            student_id = request.POST.get('student_id')
            if student_id:
                student = get_object_or_404(User, pk=student_id, role='student')
                student.classroom = classroom
                student.school = classroom.school
                student.save()
                ensure_classroom_schedule(classroom)
                messages.success(request, f"{student.full_name} {classroom.name} sinfiga biriktirildi!")

    return redirect('classroom_manage', class_id=classroom.id)


@login_required
@user_passes_test(is_admin_or_staff)
def remove_student_from_class(request, class_id, student_id):
    classroom = get_object_or_404(Classroom, pk=class_id)
    student = get_object_or_404(User, pk=student_id, classroom=classroom)

    action = request.POST.get('action', 'unassign')
    if action == 'delete':
        student_name = student.full_name
        student.delete()
        messages.success(request, f"O'quvchi {student_name} tizimdan o'chirildi.")
    else:
        student.classroom = None
        student.save()
        messages.success(request, f"O'quvchi {student.full_name} {classroom.name} sinfidan chiqarildi.")

    return redirect('classroom_manage', class_id=classroom.id)


@login_required
@user_passes_test(is_admin_or_staff)
def change_class_teacher(request, class_id):
    classroom = get_object_or_404(Classroom, pk=class_id)

    if request.method == 'POST':
        teacher_id = request.POST.get('teacher_id')
        if teacher_id in ('', 'remove'):
            classroom.class_teacher = None
            classroom.save()
            messages.warning(request, f"{classroom.name} sinfidan rahbar o'chirildi.")
        else:
            teacher = get_object_or_404(User, pk=teacher_id, role='teacher')
            old = classroom.class_teacher
            classroom.class_teacher = teacher
            classroom.save()
            if old:
                messages.success(request, f"Ustoz almashtirildi: {old.full_name} → {teacher.full_name}")
            else:
                messages.success(request, f"{classroom.name} sinfiga {teacher.full_name} biriktirildi!")

    return redirect('classroom_manage', class_id=classroom.id)


@login_required
@user_passes_test(is_admin_or_staff)
def delete_teacher(request, teacher_id):
    teacher = get_object_or_404(User, pk=teacher_id, role='teacher')
    if request.method == 'POST':
        teacher_name = teacher.full_name
        Classroom.objects.filter(class_teacher=teacher).update(class_teacher=None)
        teacher.delete()
        messages.success(request, f"Ustoz {teacher_name} tizimdan muvaffaqiyatli olib tashlandi!")
    return redirect('admin_panel_dashboard')


@login_required
@user_passes_test(is_admin_or_staff)
def delete_student(request, student_id):
    student = get_object_or_404(User, pk=student_id, role='student')
    if request.method == 'POST':
        student_name = student.full_name
        student.delete()
        messages.success(request, f"O'quvchi {student_name} tizimdan butunlay o'chirildi.")
    referer = request.META.get('HTTP_REFERER', 'admin_panel_dashboard')
    return redirect(referer)


@login_required
@user_passes_test(is_admin_or_staff)
def reset_teacher_password(request, teacher_id):
    teacher = get_object_or_404(User, pk=teacher_id, role='teacher')
    if request.method == 'POST':
        new_pass = generate_password()
        teacher.set_password(new_pass)
        teacher.initial_password = new_pass
        teacher.save(update_fields=['password', 'initial_password'])
        messages.success(request, f"Ustoz {teacher.full_name} (@{teacher.username}) uchun yangi parol o'rnatildi: {new_pass}")
    referer = request.META.get('HTTP_REFERER', 'admin_panel_dashboard')
    return redirect(referer)


# ── Kundalik Jadvali (Admin Timetable Management) ───────────────────────────
@login_required
@user_passes_test(is_admin_or_staff)
def admin_timetable(request):
    from django.utils import timezone
    ensure_default_catalog()
    classrooms = Classroom.objects.select_related('school', 'class_teacher').order_by('grade_level', 'name')
    subjects = Subject.objects.all().order_by('name')
    teachers = User.objects.filter(role='teacher').select_related('subject').order_by('first_name', 'last_name')

    class_id = request.GET.get('class_id') or request.POST.get('class_id')
    selected_class = None
    if class_id and str(class_id).isdigit():
        selected_class = classrooms.filter(pk=int(class_id)).first()
    if not selected_class:
        selected_class = classrooms.first()

    if request.method == 'POST':
        action = request.POST.get('action')
        timetable_url = reverse('admin_timetable')
        target_url = f"{timetable_url}?class_id={selected_class.id}" if selected_class else timetable_url

        if action == 'auto_generate' and selected_class:
            created = generate_full_weekly_schedule(selected_class, overwrite=True)
            messages.success(request, f"'{selected_class.name}' sinfi uchun Dushanba-Shanba to'liq jadvali ({created} ta dars) yangilandi! Yakshanba dam olish kuni.")
            return redirect(target_url)

        elif action == 'auto_generate_all':
            total_created = 0
            for cls in classrooms:
                total_created += generate_full_weekly_schedule(cls, overwrite=True)
            messages.success(request, f"Barcha {classrooms.count()} ta sinf uchun to'liq haftalik jadval ({total_created} ta dars) yaratildi! Yakshanba dam olish kuni.")
            return redirect(target_url)

        elif action == 'add_lesson' and selected_class:
            day_of_week = request.POST.get('day_of_week')
            lesson_number = request.POST.get('lesson_number')
            subject_id = request.POST.get('subject_id')
            teacher_id = request.POST.get('teacher_id')
            room_number = request.POST.get('room_number', '').strip()

            if not (day_of_week and day_of_week.isdigit() and 1 <= int(day_of_week) <= 6):
                messages.error(request, "Yakshanba dam olish kuni! Faqat Dushanba-Shanba (1-6) kunlariga dars qo'yish mumkin.")
            elif not (lesson_number and lesson_number.isdigit() and 1 <= int(lesson_number) <= 7):
                messages.error(request, "Dars soati 1 dan 7 gacha bo'lishi kerak.")
            elif not subject_id:
                messages.error(request, "Fan tanlanishi shart!")
            else:
                d_int = int(day_of_week)
                l_int = int(lesson_number)
                slot_times = {num: (st, et) for num, st, et in LESSON_SLOTS}
                st, et = slot_times.get(l_int, (None, None))
                Schedule.objects.update_or_create(
                    classroom=selected_class,
                    day_of_week=d_int,
                    lesson_number=l_int,
                    defaults={
                        'subject_id': int(subject_id),
                        'teacher_id': int(teacher_id) if teacher_id and teacher_id.isdigit() else None,
                        'room_number': room_number or '201',
                        'start_time': st,
                        'end_time': et,
                    },
                )
                messages.success(request, f"{selected_class.name} sinfi jadvali saqlandi!")
            return redirect(target_url)

        elif action == 'delete_lesson':
            schedule_id = request.POST.get('schedule_id')
            if schedule_id and schedule_id.isdigit():
                Schedule.objects.filter(pk=int(schedule_id)).delete()
                messages.info(request, "Dars jadvaldan olib tashlandi.")
            return redirect(target_url)

        elif action == 'add_subject':
            sub_name = request.POST.get('subject_name', '').strip()
            sub_code = request.POST.get('subject_code', '').strip().upper()
            if sub_name:
                _, created = Subject.objects.get_or_create(
                    name=sub_name,
                    defaults={'code': sub_code or sub_name[:4].upper(), 'icon': 'fa-book'}
                )
                if created:
                    messages.success(request, f"'{sub_name}' fani bazaga qo'shildi!")
                else:
                    messages.info(request, f"'{sub_name}' fani allaqachon mavjud.")
            return redirect(target_url)

    if selected_class:
        ensure_classroom_schedule(selected_class)

    days_data = []
    if selected_class:
        for day_num, day_name in Schedule.DAYS_OF_WEEK:
            lessons = Schedule.objects.filter(
                classroom=selected_class,
                day_of_week=day_num,
            ).select_related('subject', 'teacher').order_by('lesson_number')
            days_data.append({
                'day_num': day_num,
                'day_name': day_name,
                'lessons': lessons,
                'is_rest_day': False,
            })
        days_data.append({
            'day_num': 7,
            'day_name': 'Yakshanba',
            'lessons': [],
            'is_rest_day': True,
        })

    return render(request, 'admin_panel/timetable.html', {
        'classrooms': classrooms,
        'selected_class': selected_class,
        'days_data': days_data,
        'subjects': subjects,
        'teachers': teachers,
        'today_weekday': timezone.now().isoweekday(),
        'days_choices': Schedule.DAYS_OF_WEEK,
        'lesson_numbers': range(1, 7),
    })



