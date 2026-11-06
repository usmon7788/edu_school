from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Q
from apps.models import User, School, Classroom, Subject, Grade, Schedule, Homework, Attendance
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
    schools = School.objects.all()
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
        'class_stats': class_stats,
        'teachers': teachers,
        'schools': schools,
    }
    return render(request, 'admin_panel/dashboard.html', context)


# ── Ustoz yaratish ──────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_admin_or_staff)
def create_teacher(request):
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
            if subject_id:
                teacher.subject_id = subject_id
            teacher.save()
            new_credentials = {
                'full_name': teacher.full_name,
                'username': username,
                'password': password,
                'role': "Ustoz",
                'subject': teacher.subject.name if teacher.subject else "—",
            }
            messages.success(request, f"Ustoz {teacher.full_name} muvaffaqiyatli yaratildi! Login: {username} | Parol: {password}")

    return render(request, 'admin_panel/create_teacher.html', {
        'schools': schools,
        'subjects': subjects,
        'new_credentials': new_credentials,
    })


# ── O'quvchi yaratish ───────────────────────────────────────────────────────
@login_required
@user_passes_test(is_admin_or_staff)
def create_student(request):
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
            messages.success(request, f"'{classroom.name}' sinfi muvaffaqiyatli yaratildi! Kurator: {curator.full_name if curator else 'Tanlanmagan'}")
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
                    classroom=classroom, school=classroom.school, phone=phone
                )
                messages.success(request, f"O'quvchi {student.full_name} qo'shildi! Login: {username} | Parol: {password}")

        elif action_type == 'assign_existing':
            student_id = request.POST.get('student_id')
            if student_id:
                student = get_object_or_404(User, pk=student_id, role='student')
                student.classroom = classroom
                student.school = classroom.school
                student.save()
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


