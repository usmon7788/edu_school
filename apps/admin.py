from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import ValidationError
from django import forms
from .models import User, School, Classroom, Subject, Grade, Schedule, Homework, Attendance, Post, PostComment, ChatMessage

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Maktab ma'lumotlari", {
            'fields': ('role', 'avatar', 'phone', 'birth_date', 'address', 'school', 'classroom', 'subject', 'bio')
        }),
    )
    list_display = ('username', 'full_name', 'role', 'classroom', 'school', 'is_staff')
    list_filter = ('role', 'school', 'classroom', 'is_staff')
    search_fields = ('username', 'first_name', 'last_name', 'phone')


class ClassroomAdminForm(forms.ModelForm):
    class Meta:
        model = Classroom
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        max_students = cleaned_data.get('max_students') or 28
        if self.instance and self.instance.pk:
            current_students = self.instance.students.filter(role='student').count()
            if current_students > max_students:
                raise ValidationError(f"Sinfda hozirda {current_students} ta o'quvchi bor. Maksimal sig'imni {current_students} dan kam qilib bo'lmaydi!")
        return cleaned_data


class ClassroomAdmin(admin.ModelAdmin):
    form = ClassroomAdminForm
    list_display = ('name', 'school', 'class_teacher', 'student_capacity_display', 'is_full_display')
    list_filter = ('school', 'grade_level')
    search_fields = ('name',)

    def student_capacity_display(self, obj):
        count = obj.student_count()
        return f"{count} / {obj.max_students} o'quvchi"
    student_capacity_display.short_description = "O'quvchilar soni (Limit: 28)"

    def is_full_display(self, obj):
        return "To'lgan" if obj.is_full() else f"Bo'sh joy: {obj.available_seats()}"
    is_full_display.short_description = "Holat"


admin.site.register(User, CustomUserAdmin)
admin.site.register(School)
admin.site.register(Classroom, ClassroomAdmin)
admin.site.register(Subject)
admin.site.register(Grade)
admin.site.register(Schedule)
admin.site.register(Homework)
admin.site.register(Attendance)


class PostCommentInline(admin.TabularInline):
    model = PostComment
    extra = 0


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('author', 'category', 'created_at', 'total_likes', 'total_comments')
    list_filter = ('category', 'created_at')
    search_fields = ('content', 'author__username', 'author__first_name', 'author__last_name')
    inlines = [PostCommentInline]


@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'created_at')
    search_fields = ('content', 'author__username')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'message_snippet', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('sender__username', 'receiver__username', 'message')

    def message_snippet(self, obj):
        return obj.message[:40]
    message_snippet.short_description = "Xabar"


