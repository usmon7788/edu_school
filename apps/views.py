from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Count, Q
from django.utils import timezone
from .models import (
    User, School, Classroom, Subject, Grade, Schedule, Homework, Attendance, 
    Post, PostComment, ChatMessage, ChatContactAlias, ChatBlock, ChatConversationHide, UserSettings
)
from .forms import (
    LoginForm, RegisterForm, StudentProfileUpdateForm,
    GradeCreateForm, HomeworkCreateForm, AttendanceRecordForm,
    PostForm, PostCommentForm, UserSettingsForm
)
from django.contrib.auth.forms import PasswordChangeForm


def switch_language(request, lang_code):
    if lang_code in ['uz', 'ru', 'en']:
        request.session['lang'] = lang_code
    referer = request.META.get('HTTP_REFERER', '/')
    return redirect(referer)


def dashboard_redirect(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.role == 'teacher':
        return redirect('teacher_dashboard')
    elif request.user.role == 'student':
        return redirect('student_dashboard')
    elif request.user.role == 'admin' or request.user.is_staff:
        return redirect('admin_panel_dashboard')
    return redirect('student_dashboard')


from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Xush kelibsiz, {user.full_name}!")
            # Roliga qarab yo'naltirish
            if user.role == 'teacher':
                return redirect('teacher_dashboard')
            elif user.role == 'student':
                return redirect('student_dashboard')
            elif user.role == 'admin' or user.is_staff:
                return redirect('admin_panel_dashboard')
            return redirect('student_dashboard')
        else:
            messages.error(request, "Login yoki parol noto'g'ri!")
    else:
        form = LoginForm()

    return render(request, 'auth/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')
    messages.info(request, "Tizimga faqat maktab ma'muri (admin) tomonidan berilgan login va parol bilan kiriladi.")
    return redirect('login')


def logout_view(request):
    logout(request)
    messages.info(request, "Tizimdan muvaffaqiyatli chiqdingiz.")
    return redirect('login')


# ==========================================
# 2-SHART: O'QUVCHI ASOSIY SAYTI / KABINETI
# ==========================================

@login_required
def student_dashboard(request):
    user = request.user
    if user.role == 'teacher':
        return redirect('teacher_dashboard')
    if user.role == 'admin' and not user.classroom:
        return redirect('admin_panel_dashboard')

    classroom = user.classroom
    school = user.school or (classroom.school if classroom else None)

    # Baholar
    grades = Grade.objects.filter(student=user).select_related('subject', 'teacher')
    avg_grade = grades.aggregate(avg=Avg('grade'))['avg'] or 0.0

    # Kundalik jadvali (bugun)
    weekday = timezone.now().isoweekday()  # 1: Monday ... 7: Sunday
    today_lessons = []
    # O'quvchining sinf bosqichini aniqlash (4-dan past: shanba yo'q, 5+: shanba bor)
    grade_level = classroom.grade_level if classroom else 1
    # Shanba kuni (6) filtri: 4-sinfdan past o'quvchilar uchun shanba yo'q
    if classroom and weekday <= 6:
        if weekday == 6 and grade_level < 5:  # Shanba, 4-sinfdan past
            today_lessons = []
        else:
            today_lessons = Schedule.objects.filter(classroom=classroom, day_of_week=weekday).select_related('subject', 'teacher')

    # Hozirgi dars (joriy vaqt asosida)
    from datetime import datetime as dt
    current_time = timezone.localtime(timezone.now()).time()
    current_lesson = None
    current_lesson_end_seconds = 0
    for lesson in today_lessons:
        if lesson.start_time and lesson.end_time:
            if lesson.start_time <= current_time <= lesson.end_time:
                current_lesson = lesson
                end_dt = dt.combine(dt.today(), lesson.end_time)
                now_dt = dt.combine(dt.today(), current_time)
                current_lesson_end_seconds = max(0, int((end_dt - now_dt).total_seconds()))
                break
        elif lesson.start_time:
            # Agar end_time yo'q bo'lsa, 40 minutlik dars deb hisoblaymiz
            from datetime import timedelta
            end_time_calc = (dt.combine(dt.today(), lesson.start_time) + timedelta(minutes=40)).time()
            if lesson.start_time <= current_time <= end_time_calc:
                current_lesson = lesson
                end_dt = dt.combine(dt.today(), end_time_calc)
                now_dt = dt.combine(dt.today(), current_time)
                current_lesson_end_seconds = max(0, int((end_dt - now_dt).total_seconds()))
                break

    # Uy ishlari
    homeworks = []
    if classroom:
        homeworks = Homework.objects.filter(classroom=classroom, due_date__gte=timezone.now().date())[:5]

    # Davomat statistikasi
    attendances = Attendance.objects.filter(student=user)
    total_days = attendances.count()
    present_days = attendances.filter(status='present').count()
    absent_days = attendances.filter(status='absent').count()
    attendance_rate = int((present_days / total_days * 100)) if total_days > 0 else 100

    # Fanlar bo'yicha tahlil (Subject stats for dashboard)
    subjects_stats = []
    student_subjects = Subject.objects.filter(grade__student=user).distinct()
    for sub in student_subjects[:6]:
        sub_grades = grades.filter(subject=sub)
        sub_avg = sub_grades.aggregate(avg=Avg('grade'))['avg'] or 0.0
        subjects_stats.append({
            'subject': sub,
            'avg': round(sub_avg, 1),
            'percent': int((sub_avg / 5.0) * 100),
            'count': sub_grades.count()
        })
    subjects_stats.sort(key=lambda x: x['avg'], reverse=True)

    # Yutuqlar va medallar (Badges)
    five_count = grades.filter(grade=5).count()
    posts_count = Post.objects.filter(author=user).count()
    classmates_count = User.objects.filter(classroom=classroom, role='student').count() if classroom else 0
    unread_chat_count = ChatMessage.objects.filter(receiver=user, is_read=False).count()

    context = {
        'student': user,
        'school': school,
        'classroom': classroom,
        'avg_grade': round(avg_grade, 2),
        'recent_grades': grades[:6],
        'today_lessons': today_lessons,
        'current_lesson': current_lesson,
        'current_lesson_end_seconds': current_lesson_end_seconds,
        'homeworks': homeworks,
        'attendance_rate': attendance_rate,
        'total_days': total_days,
        'present_days': present_days,
        'absent_days': absent_days,
        'subjects_stats': subjects_stats,
        'five_count': five_count,
        'posts_count': posts_count,
        'classmates_count': classmates_count,
        'unread_chat_count': unread_chat_count,
    }
    return render(request, 'student/dashboard.html', context)


@login_required
def student_grades(request):
    user = request.user
    if user.role != 'student':
        return redirect('dashboard_redirect')

    grades = Grade.objects.filter(student=user).select_related('subject', 'teacher')
    
    # Fanlar bo'yicha guruhlash
    subjects_stats = []
    subjects = Subject.objects.filter(grade__student=user).distinct()
    for sub in subjects:
        sub_grades = grades.filter(subject=sub)
        avg = sub_grades.aggregate(avg=Avg('grade'))['avg'] or 0
        subjects_stats.append({
            'subject': sub,
            'grades': sub_grades,
            'avg': round(avg, 1),
            'count': sub_grades.count()
        })

    total_avg = grades.aggregate(avg=Avg('grade'))['avg'] or 0

    return render(request, 'student/grades.html', {
        'grades': grades,
        'subjects_stats': subjects_stats,
        'total_avg': round(total_avg, 2),
    })


@login_required
def student_timetable(request):
    user = request.user
    if user.role != 'student':
        return redirect('dashboard_redirect')

    classroom = user.classroom
    days_data = []
    # O'quvchining sinf bosqichini aniqlash
    grade_level = classroom.grade_level if classroom else 1
    
    if classroom:
        for day_num, day_name in Schedule.DAYS_OF_WEEK:
            # Shanba kuni (6): 4-sinfdan past o'quvchilar uchun ko'rsatmaslik
            if day_num == 6 and grade_level < 5:
                continue  # Shanba kuni 4-sinfdan past uchun yo'q
            lessons = Schedule.objects.filter(classroom=classroom, day_of_week=day_num).select_related('subject', 'teacher')
            days_data.append({
                'day_num': day_num,
                'day_name': day_name,
                'lessons': lessons
            })

    return render(request, 'student/timetable.html', {
        'classroom': classroom,
        'days_data': days_data,
        'today_weekday': timezone.now().isoweekday(),
        'grade_level': grade_level,
    })


@login_required
def student_homework(request):
    user = request.user
    if user.role != 'student':
        return redirect('dashboard_redirect')

    classroom = user.classroom
    homeworks = []
    if classroom:
        homeworks = Homework.objects.filter(classroom=classroom).select_related('subject', 'teacher')

    return render(request, 'student/homework.html', {
        'classroom': classroom,
        'homeworks': homeworks,
        'today': timezone.now().date(),
    })


@login_required
def student_attendance(request):
    user = request.user
    if user.role != 'student':
        return redirect('dashboard_redirect')

    attendances_qs = Attendance.objects.filter(student=user).select_related('classroom', 'subject', 'teacher').order_by('-date')
    selected_subject_id = request.GET.get('subject_id')
    if selected_subject_id and selected_subject_id.isdigit():
        attendances = attendances_qs.filter(subject_id=int(selected_subject_id))
    else:
        attendances = attendances_qs

    total = attendances.count()
    present_cnt = attendances.filter(status='present').count()
    absent_cnt = attendances.filter(status='absent').count()
    excused_cnt = attendances.filter(status='excused').count()
    late_cnt = attendances.filter(status='late').count()

    attendance_percentage = int((present_cnt / total * 100)) if total > 0 else 100

    # Fanlar bo'yicha statistika (tezkor xotirada hisoblash)
    subjects = Subject.objects.all()
    subject_map = {}
    for att in attendances_qs:
        if att.subject:
            sid = att.subject.id
            if sid not in subject_map:
                subject_map[sid] = {'subject': att.subject, 'total': 0, 'present': 0}
            subject_map[sid]['total'] += 1
            if att.status == 'present':
                subject_map[sid]['present'] += 1

    subject_stats = []
    for s_info in subject_map.values():
        tot = s_info['total']
        pres = s_info['present']
        pct = int((pres / tot) * 100) if tot > 0 else 0
        subject_stats.append({
            'subject': s_info['subject'],
            'total': tot,
            'present': pres,
            'percentage': pct,
        })

    return render(request, 'student/attendance.html', {
        'attendances': attendances,
        'total': total,
        'present_cnt': present_cnt,
        'absent_cnt': absent_cnt,
        'excused_cnt': excused_cnt,
        'late_cnt': late_cnt,
        'attendance_percentage': attendance_percentage,
        'subjects': subjects,
        'selected_subject_id': int(selected_subject_id) if selected_subject_id and selected_subject_id.isdigit() else None,
        'subject_stats': subject_stats,
    })



# ==========================================
# 3-SHART: O'QUVCHI O'Z PROFILINI TAHRIRLASH
# ==========================================

@login_required
def profile_edit(request):
    user = request.user
    pass_form = PasswordChangeForm(user=user)

    if request.method == 'POST':
        if 'update_profile' in request.POST:
            form = StudentProfileUpdateForm(request.POST, request.FILES, instance=user)
            if form.is_valid():
                form.save()
                messages.success(request, "Profil ma'lumotlaringiz muvaffaqiyatli yangilandi!")
                return redirect('profile_edit')
            else:
                messages.error(request, "Xatolik yuz berdi. Iltimos, ma'lumotlarni tekshiring.")
        elif 'change_password' in request.POST:
            pass_form = PasswordChangeForm(user=user, data=request.POST)
            form = StudentProfileUpdateForm(instance=user)
            if pass_form.is_valid():
                user_obj = pass_form.save()
                update_session_auth_hash(request, user_obj)
                messages.success(request, "Parolingiz muvaffaqiyatli o'zgartirildi!")
                return redirect('profile_edit')
            else:
                messages.error(request, "Parolni o'zgartirishda xatolik yuz berdi.")
    else:
        form = StudentProfileUpdateForm(instance=user)

    return render(request, 'student/profile_edit.html', {
        'form': form,
        'pass_form': pass_form,
        'user_obj': user,
    })


# ==========================================
# 1-SHART: USTOZ MAXSUS SAYTI / PORTALI
# ==========================================

@login_required
def teacher_dashboard(request):
    user = request.user
    if user.role != 'teacher':
        return redirect('student_dashboard')

    # Ustozga aloqador sinflar (u rahbarlik qiladigan yoki dars jadvalida dars beradigan sinflar)
    mentored_class = getattr(user, 'mentored_class', None)
    filter_q = Q(schedules__teacher=user)
    if mentored_class:
        filter_q |= Q(pk=mentored_class.pk)
    all_classes = Classroom.objects.filter(filter_q).distinct()

    # Ustoz qo'ygan so'nggi baholar
    recent_grades = Grade.objects.filter(teacher=user).select_related('student', 'subject')[:8]
    
    # Bugungi darslar
    weekday = timezone.now().isoweekday()
    today_lessons = []
    if weekday <= 6:
        today_lessons = Schedule.objects.filter(teacher=user, day_of_week=weekday).select_related('classroom', 'subject')

    # Ustozning bergan uy vazifalari
    my_homeworks = Homework.objects.filter(teacher=user).select_related('classroom', 'subject')[:5]

    return render(request, 'teacher/dashboard.html', {
        'teacher': user,
        'mentored_class': mentored_class,
        'all_classes': all_classes,
        'recent_grades': recent_grades,
        'today_lessons': today_lessons,
        'my_homeworks': my_homeworks,
    })


@login_required
def teacher_grades(request):
    user = request.user
    if user.role != 'teacher':
        return redirect('dashboard_redirect')

    # Faqat ustozning o'ziga biriktirilgan fanlari (User.subject yoki jadvaldagi fanlar)
    teacher_subjects = []
    if user.subject:
        teacher_subjects.append(user.subject)
    scheduled_subjects = Subject.objects.filter(schedule__teacher=user).distinct()
    for s in scheduled_subjects:
        if s not in teacher_subjects:
            teacher_subjects.append(s)

    selected_subject_id = request.GET.get('subject_id') or request.POST.get('subject_id')
    teacher_subject = None
    if selected_subject_id and str(selected_subject_id).isdigit():
        found_s = Subject.objects.filter(id=int(selected_subject_id)).first()
        if found_s and found_s in teacher_subjects:
            teacher_subject = found_s
    if not teacher_subject and teacher_subjects:
        teacher_subject = teacher_subjects[0]

    # Ustoz dars beradigan yoki rahbarlik qiladigan sinflar (jadvaldagi sinflar yoki rahbar sinfi)
    allowed_classes = Classroom.objects.filter(
        Q(schedules__teacher=user) | Q(class_teacher=user)
    ).distinct()

    if not teacher_subject:
        messages.warning(request, "Sizga hali birorta fan biriktirilmagan! Baho qo'yish uchun ma'muriyat sizga fan biriktirishi lozim.")
        return render(request, 'teacher/grades.html', {
            'teacher_subject': None,
            'teacher_subjects': [],
            'students': [],
            'grades': [],
            'all_classes': [],
            'no_subject': True,
        })

    # O'quvchilar ro'yxati (faqat ustoz o'zi dars beradigan sinflardan)
    students_query = User.objects.filter(role='student', classroom__in=allowed_classes)

    # Sinf bo'yicha filtrlash
    class_id = request.GET.get('class_id')
    selected_class_id = None
    if class_id and str(class_id).isdigit():
        target_class_id = int(class_id)
        if allowed_classes.filter(id=target_class_id).exists():
            students_query = students_query.filter(classroom_id=target_class_id)
            selected_class_id = target_class_id
        else:
            class_id = None

    students = list(students_query.select_related('classroom').order_by('classroom__name', 'last_name', 'first_name'))
    all_classes = allowed_classes

    if request.method == 'POST':
        student_id = request.POST.get('student')
        grade_val  = request.POST.get('grade')
        comment    = request.POST.get('comment', '').strip()
        date_val   = request.POST.get('date') or timezone.now().date()
        sub_id     = request.POST.get('subject')

        target_subject = teacher_subject
        if sub_id and str(sub_id).isdigit():
            found_sub = Subject.objects.filter(id=int(sub_id)).first()
            if found_sub and found_sub in teacher_subjects:
                target_subject = found_sub

        if not student_id or not grade_val:
            messages.error(request, "O'quvchi va baho tanlanishi shart!")
        elif not target_subject or target_subject not in teacher_subjects:
            messages.error(request, "Siz faqat o'zingiz dars beradigan fanga baho qo'ya olasiz!")
        else:
            student = get_object_or_404(User, pk=student_id, role='student')
            if student.classroom not in allowed_classes:
                messages.error(request, "Siz faqat o'zingiz dars beradigan sinf o'quvchilariga baho qo'ya olasiz!")
                return redirect('teacher_grades')

            try:
                grade_int = int(grade_val)
                if not (1 <= grade_int <= 5):
                    raise ValueError
            except ValueError:
                messages.error(request, "Baho 1 dan 5 gacha son bo'lishi kerak!")
                return redirect('teacher_grades')

            Grade.objects.create(
                student=student,
                subject=target_subject,
                teacher=user,
                grade=grade_int,
                comment=comment,
                date=date_val
            )
            messages.success(request, f"{student.full_name} ga '{target_subject.name}' fanidan {grade_int} baho muvaffaqiyatli qo'yildi!")
            return redirect('teacher_grades')

    # Faqat shu ustoz qo'ygan baholar tarixi
    grades_filter = Q(teacher=user)
    if teacher_subject:
        grades_filter &= Q(subject=teacher_subject)
    grades = Grade.objects.filter(grades_filter).select_related('student', 'subject', 'student__classroom').order_by('-date', '-created_at')

    return render(request, 'teacher/grades.html', {
        'teacher_subject': teacher_subject,
        'teacher_subjects': teacher_subjects,
        'students': students,
        'grades': grades,
        'all_classes': all_classes,
        'selected_class_id': selected_class_id,
        'today': timezone.now().date(),
        'no_subject': False,
    })



@login_required
def teacher_attendance(request):
    user = request.user
    if user.role != 'teacher':
        return redirect('dashboard_redirect')

    selected_class_id = request.GET.get('class_id')
    selected_class = None
    students = []

    # Ustoz dars beradigan fanlar (Faqat o'z fanlari!)
    teacher_subjects = []
    if user.subject:
        teacher_subjects.append(user.subject)
    scheduled_subjects = Subject.objects.filter(schedule__teacher=user).distinct()
    for s in scheduled_subjects:
        if s not in teacher_subjects:
            teacher_subjects.append(s)

    selected_subject_id = request.GET.get('subject_id') or request.POST.get('subject_id')
    teacher_subject = None
    if selected_subject_id and str(selected_subject_id).isdigit():
        found_sub = Subject.objects.filter(id=int(selected_subject_id)).first()
        if found_sub and found_sub in teacher_subjects:
            teacher_subject = found_sub
    if not teacher_subject and teacher_subjects:
        teacher_subject = teacher_subjects[0]

    # Ustoz dars beradigan sinflar (faqat o'zining dars jadvalidagi yoki rahbarlik qiladigan sinflar)
    classes = Classroom.objects.filter(
        Q(schedules__teacher=user) | Q(class_teacher=user)
    ).distinct()

    today = timezone.now().date()
    date_str = request.GET.get('date') or request.POST.get('date') or str(today)

    # Ustozning tanlangan sana (hafta kuni) bo'yicha jadvaldagi darslari
    try:
        from datetime import datetime
        sel_date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        weekday_num = sel_date_obj.isoweekday()
    except Exception:
        weekday_num = today.isoweekday()

    teacher_schedules_today = Schedule.objects.filter(
        teacher=user,
        day_of_week=weekday_num
    ).select_related('classroom', 'subject').order_by('lesson_number')

    if selected_class_id and str(selected_class_id).isdigit():
        selected_class = classes.filter(pk=int(selected_class_id)).first()
        if not selected_class:
            messages.error(request, "Siz faqat o'zingiz dars beradigan yoki rahbarlik qiladigan sinfga davomat qila olasiz!")
            return redirect('teacher_attendance')
        students = selected_class.students.filter(role='student').order_by('last_name', 'first_name')

    if request.method == 'POST' and selected_class:
        if selected_class not in classes:
            messages.error(request, "Siz faqat o'zingiz dars beradigan sinflarga davomat qila olasiz!")
            return redirect('teacher_attendance')

        if not teacher_subject or teacher_subject not in teacher_subjects:
            messages.error(request, "Siz faqat o'zingiz dars beradigan fan bo'yicha davomat qila olasiz!")
            return redirect(f"/teacher/attendance/?class_id={selected_class.id}&date={date_str}")

        for student in students:
            status = request.POST.get(f"status_{student.id}", 'present')
            note = request.POST.get(f"note_{student.id}", '').strip()
            Attendance.objects.update_or_create(
                student=student,
                date=date_str,
                subject=teacher_subject,
                defaults={'classroom': selected_class, 'teacher': user, 'status': status, 'note': note}
            )
        messages.success(request, f"{selected_class.name} sinfi uchun '{teacher_subject.name}' fanidan {date_str} sanasidagi davomat muvaffaqiyatli saqlandi!")
        return redirect(f"/teacher/attendance/?class_id={selected_class.id}&date={date_str}&subject_id={teacher_subject.id}")

    # Mavjud davomat yozuvlarini olish
    existing_attendance = {}
    if selected_class and teacher_subject:
        records = Attendance.objects.filter(
            classroom=selected_class,
            date=date_str,
            subject=teacher_subject
        )
        for r in records:
            existing_attendance[r.student_id] = r

    # Ushbu ustoz tomonidan qo'yilgan so'nggi davomatlar
    recent_attendances = Attendance.objects.filter(
        teacher=user,
        subject=teacher_subject
    ).select_related('student', 'classroom').order_by('-date')[:15] if teacher_subject else []

    return render(request, 'teacher/attendance.html', {
        'classes': classes,
        'selected_class': selected_class,
        'students': students,
        'today': today,
        'selected_date': date_str,
        'teacher_subject': teacher_subject,
        'teacher_subjects': teacher_subjects,
        'existing_attendance': existing_attendance,
        'recent_attendances': recent_attendances,
        'teacher_schedules_today': teacher_schedules_today,
    })



@login_required
def teacher_homework(request):
    user = request.user
    if user.role != 'teacher':
        return redirect('dashboard_redirect')

    if request.method == 'POST':
        form = HomeworkCreateForm(request.POST, request.FILES)
        if form.is_valid():
            hw = form.save(commit=False)
            hw.teacher = user
            hw.save()
            messages.success(request, f"'{hw.title}' mavzusidagi uy vazifasi {hw.classroom.name} sinfiga biriktirildi!")
            return redirect('teacher_homework')
        else:
            messages.error(request, "Vazifa yaratishda xatolik yuz berdi.")
    else:
        form = HomeworkCreateForm()

    homeworks = Homework.objects.filter(teacher=user).select_related('classroom', 'subject')
    return render(request, 'teacher/homework.html', {
        'form': form,
        'homeworks': homeworks,
    })


@login_required
def teacher_timetable(request):
    user = request.user
    if user.role != 'teacher':
        return redirect('dashboard_redirect')

    days_data = []
    for day_num, day_name in Schedule.DAYS_OF_WEEK:
        lessons = Schedule.objects.filter(teacher=user, day_of_week=day_num).select_related('subject', 'classroom')
        days_data.append({
            'day_num': day_num,
            'day_name': day_name,
            'lessons': lessons
        })

    return render(request, 'teacher/timetable.html', {
        'days_data': days_data,
        'today_weekday': timezone.now().isoweekday(),
    })


# ==============================================================================
# MAKTAB LENTASI / POSTLAR TIZIMI (STUDENT & TEACHER COMMUNITY FEED)
# ==============================================================================

@login_required
def feed_view(request):
    user = request.user
    filter_type = request.GET.get('filter', 'all')
    category = request.GET.get('category', 'all')
    search_query = request.GET.get('q', '').strip()

    posts_qs = Post.objects.select_related(
        'author', 'author__school', 'author__classroom', 'author__subject'
    ).prefetch_related(
        'likes', 'comments', 'comments__author', 'comments__author__classroom'
    )

    if filter_type == 'my':
        posts_qs = posts_qs.filter(author=user)
    elif filter_type == 'class' and user.classroom:
        posts_qs = posts_qs.filter(author__classroom=user.classroom)
    elif filter_type == 'teachers':
        posts_qs = posts_qs.filter(author__role='teacher')
    elif filter_type == 'media':
        posts_qs = posts_qs.exclude(image__isnull=True).exclude(image='')

    if category != 'all':
        posts_qs = posts_qs.filter(category=category)

    if search_query:
        posts_qs = posts_qs.filter(
            Q(content__icontains=search_query) |
            Q(author__first_name__icontains=search_query) |
            Q(author__last_name__icontains=search_query) |
            Q(author__username__icontains=search_query)
        )

    # Sidebar data
    total_posts = Post.objects.count()
    my_posts_count = Post.objects.filter(author=user).count()
    recent_achievements = Post.objects.filter(category='achievement').select_related('author')[:3]
    active_students = User.objects.filter(role='student', posts__isnull=False).annotate(p_count=Count('posts')).order_by('-p_count')[:5]

    form = PostForm()
    comment_form = PostCommentForm()

    return render(request, 'feed/feed.html', {
        'posts': posts_qs,
        'form': form,
        'comment_form': comment_form,
        'filter_type': filter_type,
        'current_category': category,
        'search_query': search_query,
        'category_choices': Post.CATEGORY_CHOICES,
        'total_posts': total_posts,
        'my_posts_count': my_posts_count,
        'recent_achievements': recent_achievements,
        'active_students': active_students,
    })


@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, "Postingiz muvaffaqiyatli chop etildi! 🎉")
        else:
            messages.error(request, "Iltimos, post matnini to'ldiring!")
    return redirect('feed')


@login_required
def post_like(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    user = request.user

    if user in post.likes.all():
        post.likes.remove(user)
        liked = False
    else:
        post.likes.add(user)
        liked = True

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax') == '1':
        return JsonResponse({
            'liked': liked,
            'total_likes': post.total_likes()
        })

    return redirect(request.META.get('HTTP_REFERER', 'feed'))


@login_required
def post_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            comment = PostComment.objects.create(
                post=post,
                author=request.user,
                content=content
            )
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                avatar_url = request.user.avatar.url if request.user.avatar else ''
                role_label = request.user.get_role_display()
                classroom_name = request.user.classroom.name if request.user.classroom else ''
                return JsonResponse({
                    'status': 'success',
                    'comment_id': comment.id,
                    'author_name': request.user.full_name,
                    'author_avatar': avatar_url,
                    'author_initial': request.user.first_name[:1].upper() if request.user.first_name else request.user.username[:1].upper(),
                    'role_label': role_label,
                    'classroom_name': classroom_name,
                    'content': comment.content,
                    'created_at': "Hozirgina",
                    'total_comments': post.total_comments()
                })
            messages.success(request, "Fikringiz qo'shildi!")
        else:
            messages.error(request, "Izoh matni bo'sh bo'lishi mumkin emas.")

    return redirect(request.META.get('HTTP_REFERER', 'feed'))


@login_required
def post_delete(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    user = request.user

    if user == post.author or user.role == 'admin' or user.is_staff or user.is_superuser:
        post.delete()
        messages.success(request, "Post muvaffaqiyatli o'chirildi.")
    else:
        messages.error(request, "Sizda bu postni o'chirish huquqi yo'q!")

    return redirect('feed')


@login_required
def post_comment_delete(request, comment_id):
    comment = get_object_or_404(PostComment, id=comment_id)
    user = request.user

    if user == comment.author or user == comment.post.author or user.role == 'admin' or user.is_staff or user.is_superuser:
        comment.delete()
        messages.success(request, "Izoh o'chirildi.")
    else:
        messages.error(request, "Sizda bu izohni o'chirish huquqi yo'q!")

    return redirect(request.META.get('HTTP_REFERER', 'feed'))


# ==========================================
# CHAT TIZIMI (Ustoz va O'quvchilar uchun)
# ==========================================

@login_required
def chat_view(request, user_id=None):
    # Foydalanuvchi oxirgi faolligini yangilash
    request.user.last_seen = timezone.now()
    request.user.save(update_fields=['last_seen'])

    current_user = request.user

    # Kontakt taxalluslari (ChatContactAlias)
    aliases_map = {a.contact_id: a.custom_name for a in ChatContactAlias.objects.filter(user=current_user)}

    # Bloklanganlar ro'yxati
    blocked_by_me_ids = set(ChatBlock.objects.filter(blocker=current_user).values_list('blocked_id', flat=True))
    blocked_me_ids = set(ChatBlock.objects.filter(blocked=current_user).values_list('blocker_id', flat=True))

    # Yashirilgan / o'chirilgan suhbatlar
    hidden_map = {h.contact_id: h.cleared_at for h in ChatConversationHide.objects.filter(user=current_user)}

    # 1. Bazadagi barcha foydalanuvchilar (O'qituvchi, admin, o'quvchi - qidiruv va yangi suhbat uchun)
    all_directory_users = list(
        User.objects.exclude(id=current_user.id)
        .select_related('school', 'classroom', 'subject')
        .order_by('first_name', 'last_name', 'username')
    )
    for u in all_directory_users:
        u.chat_display_name = aliases_map.get(u.id, u.full_name)

    # 2. Foydalanuvchiga tegishli mavjud xabarlar
    user_chat_messages = ChatMessage.objects.filter(
        Q(sender=current_user) | Q(receiver=current_user)
    ).select_related('sender', 'receiver').order_by('-created_at')

    # Oxirgi xabarlar va suhbatdoshlar xaritasi
    last_messages_map = {}
    conversation_partner_ids = set()
    for msg in user_chat_messages:
        partner_id = msg.receiver_id if msg.sender_id == current_user.id else msg.sender_id
        
        # Foydalanuvchi o'zi uchun o'chirgan xabarlar
        if msg.sender_id == current_user.id and msg.deleted_by_sender:
            continue
        if msg.receiver_id == current_user.id and msg.deleted_by_receiver:
            continue

        # Agar suhbat o'chirilgan bo'lsa va undan keyin yangi xabar kelmagan bo'lsa, ro'yxatga chiqmasin
        if partner_id in hidden_map and msg.created_at <= hidden_map[partner_id]:
            continue

        conversation_partner_ids.add(partner_id)
        if partner_id not in last_messages_map:
            last_messages_map[partner_id] = msg

    # O'qilmagan xabarlar soni
    unread_counts_map = {}
    unread_qs = ChatMessage.objects.filter(receiver=current_user, is_read=False, deleted_by_receiver=False).values('sender').annotate(cnt=Count('id'))
    for item in unread_qs:
        unread_counts_map[item['sender']] = item['cnt']

    # 3. Asosiy chap panel: Suhbatdoshlar (Recent Chats)
    if user_id:
        conversation_partner_ids.add(user_id)
    elif not conversation_partner_ids and all_directory_users:
        conversation_partner_ids.add(all_directory_users[0].id)

    recent_users = User.objects.filter(id__in=conversation_partner_ids).select_related('school', 'classroom', 'subject')

    contacts_data = []
    for u in recent_users:
        l_msg = last_messages_map.get(u.id)
        u_count = unread_counts_map.get(u.id, 0)
        contacts_data.append({
            'user': u,
            'display_name': aliases_map.get(u.id, u.full_name),
            'last_message': l_msg,
            'unread_count': u_count,
            'is_online': u.is_online,
            'last_seen_display': u.get_last_seen_display(),
            'sort_time': l_msg.created_at if l_msg else (u.last_login or u.date_joined)
        })

    # Saralash: eng oxirgi xabarlar tepada
    contacts_data.sort(key=lambda x: (x['last_message'] is not None, x['sort_time']), reverse=True)

    # 4. Tanlangan suhbatdosh
    active_partner = None
    chat_messages = []
    if user_id:
        active_partner = get_object_or_404(User, id=user_id)
    elif contacts_data:
        active_partner = contacts_data[0]['user']

    is_blocked_by_me = False
    is_blocked_by_partner = False
    active_partner_display_name = ""

    if active_partner:
        active_partner_display_name = aliases_map.get(active_partner.id, active_partner.full_name)
        is_blocked_by_me = (active_partner.id in blocked_by_me_ids)
        is_blocked_by_partner = (active_partner.id in blocked_me_ids)

        msg_filter = (
            (Q(sender=current_user, receiver=active_partner, deleted_by_sender=False) |
             Q(sender=active_partner, receiver=current_user, deleted_by_receiver=False))
        )
        if active_partner.id in hidden_map:
            msg_filter &= Q(created_at__gt=hidden_map[active_partner.id])

        chat_messages = ChatMessage.objects.filter(msg_filter).select_related(
            'sender', 'receiver', 'shared_post', 'shared_post__author', 'shared_grade', 'shared_grade__subject', 'forwarded_from'
        ).order_by('created_at')

        # O'qilgan deb belgilash
        ChatMessage.objects.filter(sender=active_partner, receiver=current_user, is_read=False).update(is_read=True)
        for c in contacts_data:
            if c['user'].id == active_partner.id:
                c['unread_count'] = 0

    total_unread = sum(c['unread_count'] for c in contacts_data)

    context = {
        'contacts': contacts_data,
        'active_partner': active_partner,
        'active_partner_display_name': active_partner_display_name,
        'is_blocked_by_me': is_blocked_by_me,
        'is_blocked_by_partner': is_blocked_by_partner,
        'chat_messages': chat_messages,
        'total_unread': total_unread,
        'all_directory_users': all_directory_users,  # Yangi suhbat ochish modal oynasi uchun
    }
    return render(request, 'chat/chat.html', context)



def _serialize_chat_message(msg, current_user_id):
    shared_post_data = None
    if msg.shared_post:
        p = msg.shared_post
        img_url = ''
        if p.image and hasattr(p.image, 'name') and p.image.name:
            try:
                img_url = p.image.url
            except Exception:
                img_url = ''
        shared_post_data = {
            'id': p.id,
            'author_name': p.author.full_name,
            'content': p.content[:160],
            'image_url': img_url,
            'category_display': p.get_category_display()
        }

    shared_grade_data = None
    if msg.shared_grade:
        g = msg.shared_grade
        shared_grade_data = {
            'id': g.id,
            'subject_name': g.subject.name,
            'grade': g.grade,
            'comment': g.comment or '',
            'date': g.date.strftime("%d.%m.%Y")
        }

    video_url = ''
    if msg.is_video and msg.video_file:
        try:
            video_url = msg.video_file.url
        except Exception:
            video_url = ''

    return {
        'id': msg.id,
        'sender_id': msg.sender_id,
        'is_me': (msg.sender_id == current_user_id),
        'message': msg.message,
        'is_voice': msg.is_voice,
        'voice_url': msg.voice_file.url if msg.voice_file else '',
        'voice_duration': msg.voice_duration,
        'formatted_duration': msg.formatted_duration,
        'is_video': msg.is_video,
        'video_url': video_url,
        'attachment_url': msg.attachment.url if msg.attachment else '',
        'attachment_is_video': msg.attachment_is_video,
        'shared_post': shared_post_data,
        'shared_grade': shared_grade_data,
        'forwarded_from_name': msg.forwarded_from.full_name if msg.forwarded_from else '',
        'time': msg.formatted_time,
        'is_read': msg.is_read
    }


@login_required
def chat_send_message_api(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': "Faqat POST so'rovi qabul qilinadi"}, status=405)

    receiver_id = request.POST.get('receiver_id')
    message_text = request.POST.get('message', '').strip()
    voice_file = request.FILES.get('voice_file') or request.FILES.get('voice')
    video_file = request.FILES.get('video_file') or request.FILES.get('video')
    attachment = request.FILES.get('attachment')
    duration = int(request.POST.get('voice_duration', 0) or 0)

    if not receiver_id:
        return JsonResponse({'status': 'error', 'message': "Qabul qiluvchi ko'rsatilmadi"}, status=400)

    if not message_text and not voice_file and not video_file and not attachment:
        return JsonResponse({'status': 'error', 'message': "Xabar matni, ovoz yoki video bo'sh bo'lishi mumkin emas"}, status=400)

    receiver = get_object_or_404(User, id=receiver_id)

    if receiver.id == request.user.id:
        return JsonResponse({'status': 'error', 'message': "O'zingizga xabar yubora olmaysiz"}, status=400)

    # Blok holatini tekshirish
    if ChatBlock.objects.filter(blocker=receiver, blocked=request.user).exists():
        return JsonResponse({
            'status': 'error',
            'message': "Siz ushbu foydalanuvchi tomonidan bloklangansiz. Xabar yuborib bo'lmaydi."
        }, status=403)

    if ChatBlock.objects.filter(blocker=request.user, blocked=receiver).exists():
        return JsonResponse({
            'status': 'error',
            'message': "Siz bu foydalanuvchini bloklagansiz. Xabar yozish uchun blokdan chiqaring."
        }, status=403)

    # Yashirilgan suhbat bo'lsa, yangi xabar yuborilganda qayta ko'rinadi
    ChatConversationHide.objects.filter(user=request.user, contact=receiver).delete()

    # Faollikni yangilash
    request.user.last_seen = timezone.now()
    request.user.save(update_fields=['last_seen'])

    msg = ChatMessage.objects.create(
        sender=request.user,
        receiver=receiver,
        message=message_text,
        voice_file=voice_file,
        voice_duration=duration,
        video_file=video_file,
        attachment=attachment,
        is_voice=(voice_file is not None),
        is_video=(video_file is not None)
    )

    return JsonResponse({
        'status': 'success',
        'message': _serialize_chat_message(msg, request.user.id)
    })


@login_required
def chat_get_messages_api(request, partner_id):
    partner = get_object_or_404(User, id=partner_id)
    last_id = int(request.GET.get('last_id', 0))

    # Faollikni yangilash
    request.user.last_seen = timezone.now()
    request.user.save(update_fields=['last_seen'])

    # Yashirilgan suhbat holatini tekshirish
    hidden_entry = ChatConversationHide.objects.filter(user=request.user, contact=partner).first()
    query_filter = (
        (Q(sender=request.user, receiver=partner, deleted_by_sender=False) |
         Q(sender=partner, receiver=request.user, deleted_by_receiver=False)) &
        Q(id__gt=last_id)
    )
    if hidden_entry:
        query_filter &= Q(created_at__gt=hidden_entry.cleared_at)

    new_msgs = ChatMessage.objects.filter(query_filter).select_related(
        'sender', 'shared_post', 'shared_post__author', 'shared_grade', 'shared_grade__subject', 'forwarded_from'
    ).order_by('created_at')

    # Yangi kelgan xabarlarni o'qilgan qilish
    ChatMessage.objects.filter(sender=partner, receiver=request.user, is_read=False).update(is_read=True)

    messages_data = [_serialize_chat_message(m, request.user.id) for m in new_msgs]

    # Suhbatdosh o'chirib tashlagan xabarlar (Undan ham o'chirish)
    deleted_ids = list(ChatMessage.objects.filter(
        sender=partner,
        receiver=request.user,
        deleted_by_receiver=True
    ).values_list('id', flat=True))

    is_blocked_by_me = ChatBlock.objects.filter(blocker=request.user, blocked=partner).exists()
    is_blocked_by_partner = ChatBlock.objects.filter(blocker=partner, blocked=request.user).exists()

    return JsonResponse({
        'status': 'success',
        'partner_is_online': partner.is_online,
        'partner_last_seen': partner.get_last_seen_display(),
        'messages': messages_data,
        'deleted_ids': deleted_ids,
        'is_blocked_by_me': is_blocked_by_me,
        'is_blocked_by_partner': is_blocked_by_partner
    })


@login_required
def chat_delete_message_api(request, message_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': "Faqat POST"}, status=405)

    msg = get_object_or_404(ChatMessage, id=message_id)
    delete_for_everyone = request.POST.get('delete_for_everyone') in ['true', '1', True]

    if msg.sender_id == request.user.id:
        msg.deleted_by_sender = True
        if delete_for_everyone:
            msg.deleted_by_receiver = True
        msg.save(update_fields=['deleted_by_sender', 'deleted_by_receiver'])
    elif msg.receiver_id == request.user.id:
        msg.deleted_by_receiver = True
        msg.save(update_fields=['deleted_by_receiver'])
    else:
        return JsonResponse({'status': 'error', 'message': "Ruxsat yo'q"}, status=403)

    return JsonResponse({
        'status': 'success',
        'message_id': message_id,
        'deleted_for_everyone': delete_for_everyone
    })


@login_required
def chat_forward_message_api(request, message_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': "Faqat POST"}, status=405)

    msg = get_object_or_404(ChatMessage, id=message_id)
    receiver_ids_raw = request.POST.get('receiver_ids') or request.POST.get('receiver_id')
    comment = request.POST.get('comment', '').strip()

    if not receiver_ids_raw:
        return JsonResponse({'status': 'error', 'message': "Qabul qiluvchi tanlanmadi"}, status=400)

    if isinstance(receiver_ids_raw, str):
        id_list = [int(i.strip()) for i in receiver_ids_raw.split(',') if i.strip().isdigit()]
    else:
        id_list = [int(receiver_ids_raw)]

    if not id_list:
        return JsonResponse({'status': 'error', 'message': "Hech kim tanlanmadi"}, status=400)

    receivers = User.objects.filter(id__in=id_list)
    msg_text = msg.message
    if comment:
        msg_text = f"{msg.message}\n💬 {comment}" if msg.message else comment

    for r in receivers:
        ChatMessage.objects.create(
            sender=request.user,
            receiver=r,
            message=msg_text,
            voice_file=msg.voice_file,
            voice_duration=msg.voice_duration,
            attachment=msg.attachment,
            is_voice=msg.is_voice,
            shared_post=msg.shared_post,
            shared_grade=msg.shared_grade,
            forwarded_from=msg.sender
        )

    request.user.last_seen = timezone.now()
    request.user.save(update_fields=['last_seen'])

    return JsonResponse({
        'status': 'success',
        'message': f"Xabar {len(receivers)} ta suhbatdoshga uzatildi!"
    })


@login_required
def chat_clear_history_api(request, partner_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': "Faqat POST so'rovi qabul qilinadi"}, status=405)

    partner = get_object_or_404(User, id=partner_id)
    clear_for_everyone = request.POST.get('clear_for_everyone') in ['true', '1', True]

    # Foydalanuvchi yuborgan xabarlarni o'chirish
    sent_msgs = ChatMessage.objects.filter(sender=request.user, receiver=partner)
    sent_msgs.update(deleted_by_sender=True)
    if clear_for_everyone:
        sent_msgs.update(deleted_by_receiver=True)

    # Foydalanuvchi qabul qilgan xabarlarni o'chirish
    received_msgs = ChatMessage.objects.filter(sender=partner, receiver=request.user)
    received_msgs.update(deleted_by_receiver=True)

    return JsonResponse({
        'status': 'success',
        'message': "Suhbat tarixi muvaffaqiyatli tozalandi!"
    })


@login_required
def chat_delete_conversation_api(request, partner_id):
    """
    Suhbatni chat ro'yxatidan butunlay olib tashlash (Chatni o'chirish).
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': "Faqat POST so'rovi qabul qilinadi"}, status=405)

    partner = get_object_or_404(User, id=partner_id)
    now = timezone.now()

    # Ushbu suhbatni yashirilganlar ro'yxatiga qo'shish
    ChatConversationHide.objects.update_or_create(
        user=request.user,
        contact=partner,
        defaults={'cleared_at': now}
    )

    # Mavjud xabarlarni foydalanuvchi uchun o'chirish
    ChatMessage.objects.filter(sender=request.user, receiver=partner).update(deleted_by_sender=True)
    ChatMessage.objects.filter(sender=partner, receiver=request.user).update(deleted_by_receiver=True)

    return JsonResponse({
        'status': 'success',
        'message': f"{partner.full_name} bilan suhbat o'chirildi!"
    })


@login_required
def chat_toggle_block_api(request, partner_id):
    """
    Foydalanuvchini bloklash yoki blokdan chiqarish.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': "Faqat POST so'rovi qabul qilinadi"}, status=405)

    partner = get_object_or_404(User, id=partner_id)
    if partner == request.user:
        return JsonResponse({'status': 'error', 'message': "O'zingizni bloklay olmaysiz"}, status=400)

    block_obj = ChatBlock.objects.filter(blocker=request.user, blocked=partner).first()
    if block_obj:
        block_obj.delete()
        is_blocked = False
        msg = f"{partner.full_name} blokdan chiqarildi"
    else:
        ChatBlock.objects.create(blocker=request.user, blocked=partner)
        is_blocked = True
        msg = f"{partner.full_name} bloklandi"

    return JsonResponse({
        'status': 'success',
        'is_blocked': is_blocked,
        'message': msg
    })


@login_required
def chat_edit_partner_name_api(request, user_id):
    """
    Kontakt nomini faqat ushbu foydalanuvchi uchun chatda o'zgartirish (haqiqiy profil o'zgarmaydi).
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': "Faqat POST so'rovi qabul qilinadi"}, status=405)

    target_user = get_object_or_404(User, id=user_id)
    new_name = request.POST.get('custom_name', '').strip() or request.POST.get('first_name', '').strip()

    if new_name:
        ChatContactAlias.objects.update_or_create(
            user=request.user,
            contact=target_user,
            defaults={'custom_name': new_name}
        )
        display_name = new_name
    else:
        ChatContactAlias.objects.filter(user=request.user, contact=target_user).delete()
        display_name = target_user.full_name

    return JsonResponse({
        'status': 'success',
        'message': "Kontakt taxallusi muvaffaqiyatli saqlandi!",
        'display_name': display_name
    })


@login_required
def chat_search_users_api(request):
    """
    Bazadagi barcha foydalanuvchilarni jonli qidirish (O'qituvchi, admin, o'quvchi).
    """
    q = request.GET.get('q', '').strip()
    users_qs = User.objects.exclude(id=request.user.id).select_related('school', 'classroom', 'subject')

    if q:
        users_qs = users_qs.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(username__icontains=q) |
            Q(subject__name__icontains=q) |
            Q(classroom__name__icontains=q) |
            Q(phone__icontains=q)
        )

    users = list(users_qs[:50])
    aliases_map = {a.contact_id: a.custom_name for a in ChatContactAlias.objects.filter(user=request.user)}

    results = []
    for u in users:
        role_label = "Ma'mur"
        role_class = "secondary"
        if u.role == 'teacher':
            role_label = f"Ustoz: {u.subject.name}" if u.subject else "Ustoz"
            role_class = "warning"
        elif u.role == 'student':
            role_label = u.classroom.name if u.classroom else "O'quvchi"
            role_class = "primary"

        avatar_url = u.avatar.url if (u.avatar and hasattr(u.avatar, 'name') and u.avatar.name) else ''
        display_name = aliases_map.get(u.id, u.full_name)

        results.append({
            'id': u.id,
            'full_name': u.full_name,
            'display_name': display_name,
            'role': u.role,
            'role_label': role_label,
            'role_class': role_class,
            'avatar_url': avatar_url,
            'is_online': u.is_online,
            'initial': (u.first_name or u.username)[:1].upper(),
            'chat_url': f"/chat/{u.id}/"
        })

    return JsonResponse({'status': 'success', 'users': results})



@login_required
def chat_global_check_api(request):
    """
    Har qanday sahifada turgan foydalanuvchining:
    1. last_seen faolligini yangilaydi (Online yashil bo'lishi uchun)
    2. Yangi o'qilmagan xabarlarni qaytaradi (Tepadan bildirishnoma / notification toast chiqishi uchun)
    """
    request.user.last_seen = timezone.now()
    request.user.save(update_fields=['last_seen'])

    active_partner_id = request.GET.get('active_partner_id')

    unread_query = ChatMessage.objects.filter(receiver=request.user, is_read=False)

    if active_partner_id and active_partner_id.isdigit():
        unread_query = unread_query.exclude(sender_id=int(active_partner_id))

    unread_msgs = list(unread_query.select_related('sender', 'sender__classroom', 'sender__subject').order_by('-created_at')[:5])

    notifications = []
    for msg in unread_msgs:
        s = msg.sender
        sender_role_label = "O'quvchi"
        if s.role == 'teacher':
            subject_name = s.subject.name if s.subject else ""
            sender_role_label = f"Ustoz ({subject_name})" if subject_name else "Ustoz"
        elif s.classroom:
            sender_role_label = f"{s.classroom.name} o'quvchisi"

        avatar_url = s.avatar.url if (s.avatar and hasattr(s.avatar, 'name') and s.avatar.name) else ""
        initial = s.first_name[:1].upper() if s.first_name else s.username[:1].upper()

        text_preview = "🎙️ Ovozli xabar" if msg.is_voice else (msg.message or "Fayl biriktirildi")

        notifications.append({
            'id': msg.id,
            'sender_id': s.id,
            'sender_name': s.full_name,
            'sender_role': sender_role_label,
            'sender_avatar': avatar_url,
            'sender_initial': initial,
            'message': text_preview,
            'time': msg.formatted_time,
            'chat_url': f"/chat/{s.id}/"
        })

    total_unread = ChatMessage.objects.filter(receiver=request.user, is_read=False).count()

    return JsonResponse({
        'status': 'success',
        'total_unread': total_unread,
        'notifications': notifications
    })


@login_required
def post_share_to_chat(request, post_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': "Faqat POST so'rovi qabul qilinadi"}, status=405)
    
    post = get_object_or_404(Post, id=post_id)
    receiver_ids_raw = request.POST.get('receiver_ids') or request.POST.get('receiver_id')
    comment = request.POST.get('comment', '').strip()
    
    if not receiver_ids_raw:
        return JsonResponse({'status': 'error', 'message': "Qabul qiluvchi tanlanmadi"}, status=400)
    
    # receiver_ids vergul bilan ajratilgan yoki bitta bo'lishi mumkin
    if isinstance(receiver_ids_raw, str):
        id_list = [int(i.strip()) for i in receiver_ids_raw.split(',') if i.strip().isdigit()]
    else:
        id_list = [int(receiver_ids_raw)]
        
    if not id_list:
        return JsonResponse({'status': 'error', 'message': "Hech qanday qabul qiluvchi topilmadi"}, status=400)

    receivers = User.objects.filter(id__in=id_list)
    msg_text = comment if comment else f"Post ulashildi: {post.content[:60]}..."
    
    for r in receivers:
        ChatMessage.objects.create(
            sender=request.user,
            receiver=r,
            message=msg_text,
            shared_post=post
        )
    
    request.user.last_seen = timezone.now()
    request.user.save(update_fields=['last_seen'])
    
    success_msg = f"Post {receivers[0].full_name} ga muvaffaqiyatli ulashildi!" if len(receivers) == 1 else f"Post {len(receivers)} ta suhbatdoshga muvaffaqiyatli ulashildi!"
    
    return JsonResponse({
        'status': 'success',
        'message': success_msg,
        'count': len(receivers),
        'chat_url': f"/chat/{receivers[0].id}/" if len(receivers) == 1 else "/chat/"
    })


@login_required
def grade_share_to_chat(request, grade_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': "Faqat POST so'rovi qabul qilinadi"}, status=405)
    
    grade = get_object_or_404(Grade, id=grade_id, student=request.user)
    receiver_ids_raw = request.POST.get('receiver_ids') or request.POST.get('receiver_id')
    comment = request.POST.get('comment', '').strip()
    
    if not receiver_ids_raw:
        return JsonResponse({'status': 'error', 'message': "Qabul qiluvchi tanlanmadi"}, status=400)
    
    if isinstance(receiver_ids_raw, str):
        id_list = [int(i.strip()) for i in receiver_ids_raw.split(',') if i.strip().isdigit()]
    else:
        id_list = [int(receiver_ids_raw)]

    if not id_list:
        return JsonResponse({'status': 'error', 'message': "Hech qanday qabul qiluvchi topilmadi"}, status=400)

    receivers = User.objects.filter(id__in=id_list)
    msg_text = comment if comment else f"Men {grade.subject.name} fanidan {grade.grade} baho oldim! 🌟"
    
    for r in receivers:
        ChatMessage.objects.create(
            sender=request.user,
            receiver=r,
            message=msg_text,
            shared_grade=grade
        )
    
    request.user.last_seen = timezone.now()
    request.user.save(update_fields=['last_seen'])
    
    success_msg = f"Baho {receivers[0].full_name} ga muvaffaqiyatli ulashildi!" if len(receivers) == 1 else f"Baho {len(receivers)} ta suhbatdoshga muvaffaqiyatli ulashildi!"
    
    return JsonResponse({
        'status': 'success',
        'message': success_msg,
        'count': len(receivers),
        'chat_url': f"/chat/{receivers[0].id}/" if len(receivers) == 1 else "/chat/"
    })


@login_required
def get_share_contacts_api(request):
    """Post yoki bahoni ulashish uchun kontaktlar ro'yxatini beradi (Telegram formatida)"""
    current_user = request.user
    allowed_users_qs = User.objects.exclude(id=current_user.id).select_related('school', 'classroom', 'subject')

    if current_user.role == 'student':
        q_filter = Q()
        if current_user.classroom:
            q_filter |= Q(classroom=current_user.classroom, role='student')
        if current_user.school:
            q_filter |= Q(school=current_user.school, role='teacher')
        else:
            q_filter |= Q(role='teacher')
        allowed_users_qs = allowed_users_qs.filter(q_filter)
    elif current_user.role == 'teacher':
        if current_user.school:
            allowed_users_qs = allowed_users_qs.filter(Q(school=current_user.school) | Q(classroom__school=current_user.school))
        else:
            allowed_users_qs = allowed_users_qs.filter(Q(role='teacher') | Q(role='student'))

    contacts = []
    for u in allowed_users_qs[:50]:
        avatar_url = u.avatar.url if (u.avatar and hasattr(u.avatar, 'name') and u.avatar.name) else ""
        first_name = u.first_name if u.first_name else (u.username)
        initial = first_name[:1].upper()
        
        if u.role == 'teacher':
            role_desc = f"Ustoz • {u.subject.name}" if u.subject else "Ustoz"
        elif u.classroom:
            role_desc = f"{u.classroom.name} o'quvchisi"
        else:
            role_desc = "Foydalanuvchi"

        contacts.append({
            'id': u.id,
            'name': u.full_name,
            'first_name': first_name,
            'role': role_desc,
            'role_type': u.role,
            'avatar': avatar_url,
            'initial': initial,
            'is_online': u.is_online,
            'last_seen': u.get_last_seen_display()
        })

    # Online foydalanuvchilarni oldinga chiqarish (Telegram kabi)
    contacts.sort(key=lambda x: (x['is_online']), reverse=True)

    return JsonResponse({'status': 'success', 'contacts': contacts})





# ==========================================
# SOZLAMALAR SAHIFASI (SETTINGS)
# ==========================================

@login_required
def settings_view(request):
    user = request.user
    settings_obj, _ = UserSettings.objects.get_or_create(user=user)
    pass_form = PasswordChangeForm(user=user)
    profile_form = StudentProfileUpdateForm(instance=user)

    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'save_settings':
            theme = request.POST.get('theme', 'light')
            language = request.POST.get('language', 'uz')
            notification_sound = request.POST.get('notification_sound', 'default')
            settings_obj.theme = theme
            settings_obj.language = language
            settings_obj.notification_sound = notification_sound
            settings_obj.save()
            if language in ['uz', 'ru', 'en']:
                request.session['lang'] = language
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': 'Sozlamalar saqlandi!'})
            messages.success(request, 'Sozlamalar muvaffaqiyatli saqlandi!')
            return redirect('settings_view')
        elif action == 'change_password':
            pass_form = PasswordChangeForm(user=user, data=request.POST)
            if pass_form.is_valid():
                user_obj = pass_form.save()
                update_session_auth_hash(request, user_obj)
                messages.success(request, 'Parolingiz muvaffaqiyatli ozgartirildi!')
                return redirect('settings_view')
            else:
                messages.error(request, 'Parolni ozgartirishda xatolik yuz berdi.')
        elif action == 'update_profile':
            profile_form = StudentProfileUpdateForm(request.POST, request.FILES, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Profil muvaffaqiyatli yangilandi!')
                return redirect('settings_view')
            else:
                messages.error(request, 'Profilni yangilashda xatolik yuz berdi.')

    context = {
        'settings_obj': settings_obj,
        'pass_form': pass_form,
        'profile_form': profile_form,
        'sound_choices': UserSettings.SOUND_CHOICES,
        'theme_choices': UserSettings.THEME_CHOICES,
        'languages': [
            {'code': 'uz', 'name': "O'zbekcha", 'flag': '🇺🇿'},
            {'code': 'ru', 'name': 'Ruscha', 'flag': '🇷🇺'},
            {'code': 'en', 'name': 'English', 'flag': '🇬🇧'},
        ],
    }
    return render(request, 'settings/settings.html', context)


@login_required
def settings_api_save(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error'}, status=405)
    settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)
    theme = request.POST.get('theme')
    language = request.POST.get('language')
    notification_sound = request.POST.get('notification_sound')
    if theme and theme in dict(UserSettings.THEME_CHOICES):
        settings_obj.theme = theme
    if language and language in ['uz', 'ru', 'en']:
        settings_obj.language = language
        request.session['lang'] = language
    if notification_sound and notification_sound in dict(UserSettings.SOUND_CHOICES):
        settings_obj.notification_sound = notification_sound
    settings_obj.save()
    return JsonResponse({'status': 'success', 'theme': settings_obj.theme, 'language': settings_obj.language, 'notification_sound': settings_obj.notification_sound})


@login_required
def chat_block_status_api(request, partner_id):
    is_blocked_by_me = ChatBlock.objects.filter(blocker=request.user, blocked_id=partner_id).exists()
    is_blocked_by_partner = ChatBlock.objects.filter(blocker_id=partner_id, blocked=request.user).exists()
    return JsonResponse({'status': 'success', 'is_blocked_by_me': is_blocked_by_me, 'is_blocked_by_partner': is_blocked_by_partner})
