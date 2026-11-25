from django.test import TestCase
from django.urls import reverse

from apps.models import Classroom, Schedule, School, Subject, User


class AdminScheduleAndAutoPopulationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='test_admin',
            email='admin@example.com',
            password='admin-password',
        )
        self.school = School.objects.create(
            number=99,
            name="Test Maktabi",
            address="Toshkent",
        )
        self.math = Subject.objects.create(name="Matematika", code="MATH")
        self.eng = Subject.objects.create(name="Ingliz tili", code="ENG")
        self.phys = Subject.objects.create(name="Fizika", code="PHYS")
        self.uzb = Subject.objects.create(name="Ona tili va adabiyot", code="UZB")

    def test_creating_classroom_generates_full_mon_sat_schedule_and_sunday_off(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse('create_classroom'),
            {
                'name': '7-A',
                'grade_level': '7',
                'school_id': self.school.id,
                'max_students': '28',
            },
        )
        self.assertEqual(resp.status_code, 302)
        classroom = Classroom.objects.get(name='7-A', school=self.school)

        days = set(Schedule.objects.filter(classroom=classroom).values_list('day_of_week', flat=True))
        self.assertEqual(days, {1, 2, 3, 4, 5, 6})
        self.assertFalse(Schedule.objects.filter(classroom=classroom, day_of_week=7).exists())

    def test_new_student_and_teacher_have_full_timetable_and_sunday_rest_day(self):
        self.client.force_login(self.admin)

        # 1. Create classroom (auto-generates Mon-Sat schedule)
        self.client.post(
            reverse('create_classroom'),
            {
                'name': '8-B',
                'grade_level': '8',
                'school_id': self.school.id,
                'max_students': '28',
            },
        )
        classroom = Classroom.objects.get(name='8-B', school=self.school)

        # 2. Create teacher
        t_resp = self.client.post(
            reverse('create_teacher'),
            {
                'first_name': 'Olim',
                'last_name': 'Saidov',
                'username': 'olim_math',
                'subject_id': self.math.id,
                'school_id': self.school.id,
            },
        )
        self.assertEqual(t_resp.status_code, 200)
        teacher = User.objects.get(username='olim_math')
        self.assertTrue(Schedule.objects.filter(teacher=teacher).exists())

        # 3. Create student
        s_resp = self.client.post(
            reverse('create_student'),
            {
                'first_name': 'Ali',
                'last_name': 'Valiyev',
                'username': 'ali_valiyev',
                'classroom_id': classroom.id,
                'school_id': self.school.id,
            },
        )
        self.assertEqual(s_resp.status_code, 200)
        student = User.objects.get(username='ali_valiyev')

        # 4. Admin timetable view works and shows Yakshanba rest day
        admin_tt = self.client.get(reverse('admin_timetable') + f'?class_id={classroom.id}')
        self.assertEqual(admin_tt.status_code, 200)
        self.assertContains(admin_tt, 'Dam olish kuni')

        # Attempting to add lesson on Sunday (7) is rejected
        sunday_resp = self.client.post(
            reverse('admin_timetable'),
            {
                'action': 'add_lesson',
                'class_id': classroom.id,
                'day_of_week': '7',
                'lesson_number': '1',
                'subject_id': self.math.id,
            },
            follow=True,
        )
        self.assertEqual(sunday_resp.status_code, 200)
        self.assertFalse(Schedule.objects.filter(classroom=classroom, day_of_week=7).exists())

        # All other admin timetable POST actions redirect cleanly without NoReverseMatch
        for post_data in [
            {'action': 'auto_generate', 'class_id': classroom.id},
            {'action': 'auto_generate_all', 'class_id': classroom.id},
            {'action': 'add_subject', 'class_id': classroom.id, 'subject_name': 'Chizmachilik', 'subject_code': 'DRAW'},
            {'action': 'add_lesson', 'class_id': classroom.id, 'day_of_week': '1', 'lesson_number': '6', 'subject_id': self.math.id, 'teacher_id': teacher.id, 'room_number': '205'},
        ]:
            resp = self.client.post(reverse('admin_timetable'), post_data, follow=True)
            self.assertEqual(resp.status_code, 200)

        # 5. Student timetable & dashboard work with full schedule and Sunday rest day
        self.client.force_login(student)
        st_tt = self.client.get(reverse('student_timetable'))
        self.assertEqual(st_tt.status_code, 200)
        self.assertEqual(len(st_tt.context['days_data']), 7)
        self.assertTrue(st_tt.context['days_data'][-1]['is_rest_day'])
        for day in st_tt.context['days_data'][:-1]:
            self.assertGreater(day['lessons'].count(), 0)
        st_dash = self.client.get(reverse('student_dashboard'))
        self.assertEqual(st_dash.status_code, 200)

        # 6. Teacher timetable & dashboard work and show Sunday rest day
        self.client.force_login(teacher)
        tch_tt = self.client.get(reverse('teacher_timetable'))
        self.assertEqual(tch_tt.status_code, 200)
        self.assertEqual(len(tch_tt.context['days_data']), 7)
        self.assertTrue(tch_tt.context['days_data'][-1]['is_rest_day'])
        tch_dash = self.client.get(reverse('teacher_dashboard'))
        self.assertEqual(tch_dash.status_code, 200)
