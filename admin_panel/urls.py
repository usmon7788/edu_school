from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_panel_dashboard, name='admin_panel_dashboard'),
    path('create-teacher/', views.create_teacher, name='create_teacher'),
    path('create-student/', views.create_student, name='create_student'),
    path('create-classroom/', views.create_classroom, name='create_classroom'),
    path('classroom/<int:class_id>/', views.classroom_manage, name='classroom_manage'),
    path('classroom/<int:class_id>/add-student/', views.add_student_to_class, name='add_student_to_class'),
    path('classroom/<int:class_id>/remove-student/<int:student_id>/', views.remove_student_from_class, name='remove_student_from_class'),
    path('classroom/<int:class_id>/change-teacher/', views.change_class_teacher, name='change_class_teacher'),
    path('teacher/<int:teacher_id>/delete/', views.delete_teacher, name='delete_teacher'),
    path('teacher/<int:teacher_id>/reset-password/', views.reset_teacher_password, name='reset_teacher_password'),
    path('student/<int:student_id>/delete/', views.delete_student, name='delete_student'),
]

