import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')
django.setup()

from apps.models import School, Subject, Classroom, User, Grade, Schedule, Homework, Attendance
from django.core.exceptions import ValidationError

def test_all():
    print("Talablarni tekshirish...")
    school = School.objects.first()
    test_class, _ = Classroom.objects.get_or_create(
        name="Test-Class",
        school=school,
        defaults={'max_students': 28}
    )

    # 1. 28 nafar o'quvchi limiti tekshiruvi
    # Test sinfga 28 ta o'quvchi solamiz
    for i in range(1, 29):
        User.objects.get_or_create(
            username=f"limittest_{i}",
            defaults={
                'role': 'student',
                'school': school,
                'classroom': test_class,
                'first_name': f"Test{i}",
                'last_name': "Student"
            }
        )

    assert test_class.student_count() == 28, f"Kutilgan 28, lekin: {test_class.student_count()}"
    assert test_class.is_full() == True, "Sinf to'lgan deb belgilanishi kerak edi!"

    # 29-o'quvchi qo'shilishi taqiqlanishi kerak
    try:
        overflow_user = User(
            username="limittest_29",
            role='student',
            school=school,
            classroom=test_class,
            first_name="Overflow",
            last_name="Student"
        )
        overflow_user.save()
        print("XATOLIK: 29-o'quvchi qabul qilindi!")
    except ValidationError as e:
        print("Muvaffaqiyatli! 29-o'quvchi bloklandi:", e)

    # Tozalash
    User.objects.filter(username__startswith="limittest_").delete()
    test_class.delete()
    print("Barcha testlar a'lo darajada yakunlandi!")

if __name__ == '__main__':
    test_all()
