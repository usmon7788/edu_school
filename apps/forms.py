from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import User, School, Classroom, Subject, Grade, Homework, Attendance, Post, PostComment, UserSettings

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Login / Foydalanuvchi nomi',
            'required': True,
            'autocomplete': 'off',
            'autocapitalize': 'none',
            'spellcheck': 'false',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Parol',
            'required': True,
            'autocomplete': 'new-password',
        })
    )



class RegisterForm(forms.ModelForm):
    role = forms.ChoiceField(
        choices=[('student', "O'quvchi (Student)"), ('teacher', "Ustoz (Teacher)")],
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'roleSelect'}),
        label="Siz kimsiz?"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Yangi parol yarating'}),
        label="Parol"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Parolni tasdiqlang'}),
        label="Parolni tasdiqlash"
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'role', 'school', 'classroom', 'subject', 'phone']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Login'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ism'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Familiya'}),
            'school': forms.Select(attrs={'class': 'form-select', 'id': 'schoolSelect'}),
            'classroom': forms.Select(attrs={'class': 'form-select', 'id': 'classroomSelect'}),
            'subject': forms.Select(attrs={'class': 'form-select', 'id': 'subjectSelect'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+998 90 123 45 67'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        role = cleaned_data.get('role')
        classroom = cleaned_data.get('classroom')
        school = cleaned_data.get('school')

        if password and confirm_password and password != confirm_password:
            raise ValidationError({'confirm_password': "Kiritilgan parollar bir-biriga mos kelmadi!"})

        # O'quvchi uchun sinf majburiy va 28 kishilik limit tekshiruvi
        if role == 'student':
            if not classroom:
                raise ValidationError({'classroom': "O'quvchi uchun sinf tanlanishi shart!"})
            if classroom.student_count() >= classroom.max_students:
                raise ValidationError({'classroom': f"'{classroom.name}' sinfi to'lgan (Maksimal {classroom.max_students} nafar o'quvchi). Boshqa sinfni tanlang!"})

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class StudentProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'avatar', 'phone', 'birth_date', 'address', 'bio']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+998 90 123 45 67'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class GradeCreateForm(forms.ModelForm):
    class Meta:
        model = Grade
        fields = ['student', 'subject', 'grade', 'comment', 'date']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'grade': forms.Select(choices=[(5, '5 - A\'lo'), (4, '4 - Yaxshi'), (3, '3 - Qoniqarli'), (2, '2 - Qoniqarsiz')], attrs={'class': 'form-select'}),
            'comment': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mavzu yoki sabab'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class HomeworkCreateForm(forms.ModelForm):
    class Meta:
        model = Homework
        fields = ['classroom', 'subject', 'title', 'description', 'file', 'due_date']
        widgets = {
            'classroom': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mavzu / Vazifa nomi'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Vazifa shartlari...'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class AttendanceRecordForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['student', 'classroom', 'status', 'note', 'date']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'classroom': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'note': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Izoh (masalan: kasallik)'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['content', 'image', 'category']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control composer-textarea',
                'rows': 3,
                'placeholder': "Bugun qanday yangilik bor? O'z fikringiz, yutug'ingiz yoki savolingiz bilan o'rtoqlashing...",
                'id': 'postContentInput'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select composer-select',
                'id': 'postCategorySelect'
            }),
            'image': forms.FileInput(attrs={
                'class': 'd-none',
                'id': 'postImageInput',
                'accept': 'image/*'
            }),
            'video': forms.FileInput(attrs={
                'class': 'd-none',
                'id': 'postVideoInput',
                'accept': 'video/*'
            })
        }

    class Meta:
        model = Post
        fields = ['content', 'image', 'video', 'category']


class PostCommentForm(forms.ModelForm):
    class Meta:
        model = PostComment
        fields = ['content']
        widgets = {
            'content': forms.TextInput(attrs={
                'class': 'form-control comment-input-field',
                'placeholder': "Fikr bildiring...",
                'autocomplete': 'off'
            })
        }


class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = UserSettings
        fields = ['theme', 'language', 'notification_sound']
        widgets = {
            'theme': forms.Select(attrs={'class': 'form-select'}),
            'language': forms.Select(attrs={'class': 'form-select'}),
            'notification_sound': forms.Select(attrs={'class': 'form-select'}),
        }
