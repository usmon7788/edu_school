from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ValidationError
from django.utils import timezone

class School(models.Model):
    name = models.CharField(max_length=200, verbose_name="Maktab nomi")
    number = models.PositiveIntegerField(unique=True, verbose_name="Maktab raqami")
    address = models.CharField(max_length=255, verbose_name="Manzili")
    phone = models.CharField(max_length=30, blank=True, verbose_name="Telefon")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.number}-sonli {self.name}"

    class Meta:
        verbose_name = "Maktab"
        verbose_name_plural = "Maktablar"


class Subject(models.Model):
    name = models.CharField(max_length=100, verbose_name="Fan nomi")
    code = models.CharField(max_length=20, blank=True, verbose_name="Kod")
    icon = models.CharField(max_length=50, default="fa-book", verbose_name="Ikonka (FontAwesome)")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Fan"
        verbose_name_plural = "Fanlar"


class Classroom(models.Model):
    name = models.CharField(max_length=50, verbose_name="Sinf nomi (masalan: 9-A)")
    grade_level = models.PositiveSmallIntegerField(default=1, verbose_name="Sinf bosqichi (1-11)")
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='classrooms', verbose_name="Maktab")
    class_teacher = models.OneToOneField(
        'User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='mentored_class',
        limit_choices_to={'role': 'teacher'},
        verbose_name="Sinf rahbari"
    )
    max_students = models.PositiveIntegerField(default=28, verbose_name="Maksimal o'quvchilar soni")

    def __str__(self):
        return f"{self.name} ({self.school.number}-maktab)"

    def student_count(self):
        return self.students.filter(role='student').count()

    def is_full(self):
        return self.student_count() >= self.max_students

    def available_seats(self):
        return max(0, self.max_students - self.student_count())

    class Meta:
        verbose_name = "Sinf"
        verbose_name_plural = "Sinflar"
        unique_together = ('name', 'school')


class CustomUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('role') != 'admin':
            extra_fields['role'] = 'admin'
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    ROLE_CHOICES = (
        ('student', "O'quvchi"),
        ('teacher', "Ustoz"),
        ('admin', "Maktab Ma'muri"),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student', verbose_name="Rol")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Profil rasmi")
    phone = models.CharField(max_length=30, blank=True, verbose_name="Telefon raqami")
    birth_date = models.DateField(null=True, blank=True, verbose_name="Tug'ilgan sana")
    address = models.CharField(max_length=255, blank=True, verbose_name="Yashash manzili")
    
    # Maktab va sinf aloqalari
    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True, blank=True, related_name='users', verbose_name="Maktab")
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, blank=True, related_name='students', verbose_name="Sinf")
    
    # Faqat ustozlar uchun
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, related_name='teachers', verbose_name="Dars beradigan fani")
    bio = models.TextField(blank=True, verbose_name="Qisqacha ma'lumot")
    last_seen = models.DateTimeField(null=True, blank=True, verbose_name="Oxirgi faollik")
    initial_password = models.CharField(max_length=128, blank=True, null=True, verbose_name="Boshlang'ich parol (Admin ko'rishi uchun)")

    objects = CustomUserManager()

    def clean(self):
        super().clean()
        # Superuser yoki xodim bo'lsa rolni avtomatik admin qilish
        if (self.is_superuser or self.is_staff) and self.role != 'admin':
            self.role = 'admin'
        # Bitta sinfda maksimal 28 nafar o'quvchi cheklovi
        if self.role == 'student' and self.classroom:
            current_count = User.objects.filter(classroom=self.classroom, role='student').exclude(pk=self.pk).count()
            max_limit = self.classroom.max_students or 28
            if current_count >= max_limit:
                raise ValidationError({
                    'classroom': f"'{self.classroom.name}' sinfi to'lgan! Bitta sinfda ko'pi bilan {max_limit} nafar o'quvchi bo'lishi mumkin (Hozirda {current_count} nafar)."
                })

    def save(self, *args, **kwargs):
        if (self.is_superuser or self.is_staff) and self.role != 'admin':
            self.role = 'admin'
        self.clean()
        super().save(*args, **kwargs)

    @property
    def get_avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        return '/static/images/default-avatar.png'

    @property
    def full_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name if name else self.username

    @property
    def is_online(self):
        if self.last_seen:
            return (timezone.now() - self.last_seen).total_seconds() < 90
        return False

    def get_last_seen_display(self):
        if not self.last_seen:
            return "Noma'lum"
        if self.is_online:
            return "Online"
        diff = (timezone.now() - self.last_seen).total_seconds()
        if diff < 60:
            return "Hozirgina"
        elif diff < 3600:
            minutes = max(1, int(diff // 60))
            return f"{minutes} daqiqa oldin"
        elif diff < 86400:
            hours = int(diff // 3600)
            return f"{hours} soat oldin"
        else:
            return self.last_seen.strftime("%d.%m.%Y %H:%M")

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"


class Grade(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='grades', limit_choices_to={'role': 'student'}, verbose_name="O'quvchi")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name="Fan")
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_grades', limit_choices_to={'role': 'teacher'}, verbose_name="Ustoz")
    grade = models.PositiveSmallIntegerField(verbose_name="Baho (1-5)")
    comment = models.CharField(max_length=255, blank=True, verbose_name="Izoh / Mavzu")
    date = models.DateField(default=timezone.now, verbose_name="Sana")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.full_name} - {self.subject.name}: {self.grade}"

    class Meta:
        verbose_name = "Baho"
        verbose_name_plural = "Baholar"
        ordering = ['-date', '-created_at']


class Schedule(models.Model):
    DAYS_OF_WEEK = (
        (1, "Dushanba"),
        (2, "Seshanba"),
        (3, "Chorshanba"),
        (4, "Payshanba"),
        (5, "Juma"),
        (6, "Shanba"),
    )

    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='schedules', verbose_name="Sinf")
    day_of_week = models.PositiveSmallIntegerField(choices=DAYS_OF_WEEK, verbose_name="Hafta kuni")
    lesson_number = models.PositiveSmallIntegerField(verbose_name="Dars soati (1-7)")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name="Fan")
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'role': 'teacher'}, verbose_name="Ustoz")
    room_number = models.CharField(max_length=20, blank=True, verbose_name="Xona raqami")
    start_time = models.TimeField(null=True, blank=True, verbose_name="Boshlanish vaqti")
    end_time = models.TimeField(null=True, blank=True, verbose_name="Tugash vaqti")

    def __str__(self):
        return f"{self.classroom.name} - {self.get_day_of_week_display()} {self.lesson_number}-dars ({self.subject.name})"

    class Meta:
        verbose_name = "Dars jadvali"
        verbose_name_plural = "Dars jadvallari"
        unique_together = ('classroom', 'day_of_week', 'lesson_number')
        ordering = ['day_of_week', 'lesson_number']


class Homework(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='homeworks', verbose_name="Sinf")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name="Fan")
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'teacher'}, verbose_name="Ustoz")
    title = models.CharField(max_length=255, verbose_name="Mavzu / Vazifa nomi")
    description = models.TextField(verbose_name="Uy vazifasi tavsifi")
    file = models.FileField(upload_to='homeworks/', null=True, blank=True, verbose_name="Biriktirilgan fayl / rasm")
    due_date = models.DateField(verbose_name="Topshirish muddati")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject.name} - {self.title} ({self.classroom.name})"

    class Meta:
        verbose_name = "Uy vazifasi"
        verbose_name_plural = "Uy vazifalari"
        ordering = ['-due_date', '-created_at']


class Attendance(models.Model):
    STATUS_CHOICES = (
        ('present', "Keldi"),
        ('absent', "Kelmadi"),
        ('excused', "Sababli"),
        ('late', "Kechikdi"),
    )

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendances', limit_choices_to={'role': 'student'}, verbose_name="O'quvchi")
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, verbose_name="Sinf")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True, related_name='attendances', verbose_name="Fan")
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='recorded_attendances', limit_choices_to={'role': 'teacher'}, verbose_name="Ustoz")
    date = models.DateField(default=timezone.now, verbose_name="Sana")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present', verbose_name="Holat")
    note = models.CharField(max_length=255, blank=True, verbose_name="Sabab / Izoh")

    def __str__(self):
        sub_name = self.subject.name if self.subject else "Umumiy"
        return f"{self.student.full_name} - {sub_name} ({self.date}): {self.get_status_display()}"

    class Meta:
        verbose_name = "Davomat"
        verbose_name_plural = "Davomatlar"
        unique_together = ('student', 'date', 'subject')
        ordering = ['-date']


class Post(models.Model):
    CATEGORY_CHOICES = (
        ('general', "Umumiy fikrlar 💬"),
        ('achievement', "Yutuqlar va G'alabalar 🏆"),
        ('question', "Savol va Yordam 💡"),
        ('news', "Maktab Yangiliklari 📢"),
        ('creative', "Ijodiyot va San'at 🎨"),
        ('event', "Tadbirlar va Musobaqalar 🎉"),
    )

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts', verbose_name="Muallif")
    content = models.TextField(verbose_name="Post matni")
    image = models.ImageField(upload_to='posts/', null=True, blank=True, verbose_name="Rasm")
    video = models.FileField(upload_to='posts/videos/', null=True, blank=True, verbose_name="Video")
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='general', verbose_name="Kategoriya")
    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True, verbose_name="Yoqtirishlar")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqti")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="O'zgartirilgan vaqti")

    def __str__(self):
        return f"{self.author.full_name}: {self.content[:35]}..."

    def total_likes(self):
        return self.likes.count()

    def total_comments(self):
        return self.comments.count()

    class Meta:
        verbose_name = "Post"
        verbose_name_plural = "Postlar"
        ordering = ['-created_at']


class PostComment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', verbose_name="Post")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_comments', verbose_name="Muallif")
    content = models.TextField(verbose_name="Izoh matni")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yozilgan vaqti")

    def __str__(self):
        return f"{self.author.full_name}: {self.content[:30]}..."

    class Meta:
        verbose_name = "Post izohi"
        verbose_name_plural = "Post izohlari"
        ordering = ['created_at']


class ChatMessage(models.Model):
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sent_chat_messages', 
        verbose_name="Yuboruvchi"
    )
    receiver = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='received_chat_messages', 
        verbose_name="Qabul qiluvchi"
    )
    message = models.TextField(blank=True, default='', verbose_name="Xabar matni")
    voice_file = models.FileField(upload_to='chat_voices/', null=True, blank=True, verbose_name="Ovozli xabar")
    voice_duration = models.PositiveIntegerField(default=0, verbose_name="Ovoz davomiyligi (soniya)")
    video_file = models.FileField(upload_to='chat_videos/', null=True, blank=True, verbose_name="Dumaloq video xabar")
    attachment = models.FileField(upload_to='chat_attachments/', null=True, blank=True, verbose_name="Biriktirilgan fayl")
    is_voice = models.BooleanField(default=False, verbose_name="Ovozli xabarmi")
    is_video = models.BooleanField(default=False, verbose_name="Dumaloq video xabarmi")
    shared_post = models.ForeignKey('Post', on_delete=models.SET_NULL, null=True, blank=True, related_name='shared_in_chats', verbose_name="Ulashilgan post")
    shared_grade = models.ForeignKey('Grade', on_delete=models.SET_NULL, null=True, blank=True, related_name='shared_in_chats', verbose_name="Ulashilgan baho")
    forwarded_from = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='forwarded_messages', verbose_name="Uzatilgan muallif")
    deleted_by_sender = models.BooleanField(default=False, verbose_name="Yuboruvchi uchun o'chirilgan")
    deleted_by_receiver = models.BooleanField(default=False, verbose_name="Qabul qiluvchi uchun o'chirilgan")
    is_read = models.BooleanField(default=False, verbose_name="O'qilgan")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yuborilgan vaqti")

    def __str__(self):
        if self.is_voice:
            return f"{self.sender.username} -> {self.receiver.username} [Ovozli xabar: {self.voice_duration}s]"
        return f"{self.sender.username} -> {self.receiver.username}: {self.message[:25]}"

    @property
    def formatted_time(self):
        return self.created_at.strftime("%H:%M")

    @property
    def formatted_duration(self):
        minutes = self.voice_duration // 60
        seconds = self.voice_duration % 60
        return f"{minutes:02d}:{seconds:02d}"

    @property
    def attachment_is_video(self):
        if not self.attachment:
            return False
        extension = self.attachment.name.rsplit('.', 1)[-1].lower()
        return extension in {'3g2', '3gp', 'avi', 'm2ts', 'm2v', 'm4v', 'mkv', 'mov', 'mp4', 'mpeg', 'mpg', 'mts', 'ogv', 'webm'}

    class Meta:
        verbose_name = "Chat xabari"
        verbose_name_plural = "Chat xabarlari"
        ordering = ['created_at']


class ChatContactAlias(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_aliases', verbose_name="Foydalanuvchi")
    contact = models.ForeignKey(User, on_delete=models.CASCADE, related_name='aliased_in_chats', verbose_name="Kontakt")
    custom_name = models.CharField(max_length=150, verbose_name="Chatdagi taxallus/ism")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Chat kontakt taxallusi"
        verbose_name_plural = "Chat kontakt taxalluslari"
        unique_together = ('user', 'contact')

    def __str__(self):
        return f"{self.user.username} -> {self.contact.username}: {self.custom_name}"


class ChatBlock(models.Model):
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_users', verbose_name="Bloklagan shaxs")
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_by_users', verbose_name="Bloklangan shaxs")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Chat bloklash"
        verbose_name_plural = "Chat bloklashlar"
        unique_together = ('blocker', 'blocked')

    def __str__(self):
        return f"{self.blocker.username} blokladi: {self.blocked.username}"


class ChatConversationHide(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hidden_chat_conversations', verbose_name="Foydalanuvchi")
    contact = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hidden_by_partners', verbose_name="Yashirilgan kontakt")
    cleared_at = models.DateTimeField(auto_now=True, verbose_name="Tozalangan vaqt")

    class Meta:
        verbose_name = "Yashirilgan/o'chirilgan suhbat"
        verbose_name_plural = "Yashirilgan/o'chirilgan suhbatlar"
        unique_together = ('user', 'contact')

    def __str__(self):
        return f"{self.user.username} suhbatni o'chirdi: {self.contact.username}"


class UserSettings(models.Model):
    """Foydalanuvchi sozlamalari (notification sound, theme, etc.)"""
    THEME_CHOICES = (
        ('light', 'Yorug\' (Light)'),
        ('dark', 'Qorong\' (Dark)'),
        ('moonlight', 'Oylik (Moonlight)'),
    )
    SOUND_CHOICES = [
        ('default', 'Default (Ding)'),
        ('chime', 'Chime (Qo\'ng\'iroq)'),
        ('pop', 'Pop'),
        ('whistle', 'Whistle (Hushtak)'),
        ('bell', 'Bell (Qo\'ng\'iroq 2)'),
        ('notification', 'Notification'),
        ('soft', 'Soft (Yumshoq)'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings', verbose_name='Foydalanuvchi')
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default='light', verbose_name='Tema')
    language = models.CharField(max_length=10, default='uz', verbose_name='Til')
    notification_sound = models.CharField(max_length=30, choices=SOUND_CHOICES, default='default', verbose_name='Habar ovozi')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - Sozlamalar"

    class Meta:
        verbose_name = "Foydalanuvchi Sozlamalari"
        verbose_name_plural = "Foydalanuvchilar Sozlamalari"
