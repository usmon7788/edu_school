import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')
django.setup()

from apps.models import User, Post, PostComment

def populate_posts():
    student1 = User.objects.filter(username='student1').first()
    student2 = User.objects.filter(username='student2').first()
    student3 = User.objects.filter(username='student3').first()
    teacher1 = User.objects.filter(username='teacher1').first()
    teacher2 = User.objects.filter(username='teacher2').first()
    admin_user = User.objects.filter(role='admin').first()

    if not student1:
        print("Student1 topilmadi. Avval populate_demo_data.py ni ishga tushiring.")
        return

    # Post 1: Robototexnika yutug'i (student1)
    p1, cr1 = Post.objects.get_or_create(
        author=student1,
        content="Bugun shahar miqyosidagi Robototexnika va STEM olimpiadasida 9-A sinfimiz jamoasi bilan faxrli 1-o'rinni egalladik! 🏆🥇\nUstozimizga va bizni qo'llab-quvvatlagan barcha sinfdoshlarimizga katta rahmat!",
        category='achievement',
        defaults={'image': 'posts/robotics.jpg'}
    )
    if not p1.image:
        p1.image = 'posts/robotics.jpg'
        p1.save()

    # Likes
    for u in [student2, student3, teacher1, teacher2, admin_user]:
        if u:
            p1.likes.add(u)

    # Comments
    if student2 and not PostComment.objects.filter(post=p1, author=student2).exists():
        PostComment.objects.create(
            post=p1,
            author=student2,
            content="Qoyilmaqom natija Jasur! Barchangizni chin yurakdan tabriklayman! 🎉👏"
        )
    if teacher1 and not PostComment.objects.filter(post=p1, author=teacher1).exists():
        PostComment.objects.create(
            post=p1,
            author=teacher1,
            content="Barakalla bolalar! Maktabimiz nomini yuqori cho'qqilarga ko'targaningizdan faxrlanamiz. Matematika va fizika fanlarini yaxshi o'zlashtirganingiz samarasini berdi! 🌟"
        )

    # Post 2: Futbol musobaqasi (student3)
    if student3:
        p2, cr2 = Post.objects.get_or_create(
            author=student3,
            content="Maktablararo futbol chempionatida final uchrashuvida 3:1 hisobida g'alaba qozonib chempion bo'ldik! ⚽🏆 Bizning jamoa eng zo'ri!",
            category='event',
            defaults={'image': 'posts/football.jpg'}
        )
        if not p2.image:
            p2.image = 'posts/football.jpg'
            p2.save()
        for u in [student1, student2, teacher2]:
            if u:
                p2.likes.add(u)
        if student1 and not PostComment.objects.filter(post=p2, author=student1).exists():
            PostComment.objects.create(
                post=p2,
                author=student1,
                content="O'yin ajoyib bo'ldi, ayniqsa oxirgi daqiqalardagi gol super chiqdi! 🔥"
            )

    # Post 3: Savol / Fikr (student2)
    if student2:
        p3, cr3 = Post.objects.get_or_create(
            author=student2,
            content="Ertangi fizika darsidagi 'Optika va yorug'lik sinishi' mavzusiga doir qo'shimcha kitoblar yoki qiziqarli video darsliklar kimda bor? Maslahat berib yuboringlar iltimos 😊📚",
            category='question'
        )
        for u in [student1, teacher1]:
            if u:
                p3.likes.add(u)
        if teacher1 and not PostComment.objects.filter(post=p3, author=teacher1).exists():
            PostComment.objects.create(
                post=p3,
                author=teacher1,
                content="Madina, ertaga laboratoriya xonasida amaliy tajriba ham o'tkazamiz. Sinf kutubxonasida 'Yosh fizik' ensiklopediyasi bor, shuni o'qib kelsangiz juda foydali bo'ladi."
            )

    # Post 4: Ustoz post (teacher1)
    if teacher1:
        p4, cr4 = Post.objects.get_or_create(
            author=teacher1,
            content="Hurmatli o'quvchilar! Kelgusi haftadan boshlab matematika to'garagimiz darsdan so'ng har chorshanba kuni soat 15:00 da 204-xonada bo'lib o'tadi. Olimpiadaga tayyorgarlik ko'rishni xohlovchilar marhamat! 📐✏️",
            category='news'
        )
        for u in [student1, student2, student3]:
            if u:
                p4.likes.add(u)

    print("Namunaviy postlar va izohlar muvaffaqiyatli yaratildi!")

if __name__ == '__main__':
    populate_posts()
