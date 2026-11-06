from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_redirect, name='dashboard_redirect'),
    path('switch-lang/<str:lang_code>/', views.switch_language, name='switch_language'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # O'quvchi sahifalari
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('student/grades/', views.student_grades, name='student_grades'),
    path('student/timetable/', views.student_timetable, name='student_timetable'),
    path('student/homework/', views.student_homework, name='student_homework'),
    path('student/attendance/', views.student_attendance, name='student_attendance'),
    path('student/profile/edit/', views.profile_edit, name='profile_edit'),

    # Ustoz sahifalari (Ustoz uchun alohida sayt/portal)
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/grades/', views.teacher_grades, name='teacher_grades'),
    path('teacher/attendance/', views.teacher_attendance, name='teacher_attendance'),
    path('teacher/homework/', views.teacher_homework, name='teacher_homework'),
    path('teacher/timetable/', views.teacher_timetable, name='teacher_timetable'),

    # Maktab Lentasi / Postlar tizimi (Feed)
    path('feed/', views.feed_view, name='feed'),
    path('feed/create/', views.post_create, name='post_create'),
    path('feed/post/<int:post_id>/like/', views.post_like, name='post_like'),
    path('feed/post/<int:post_id>/comment/', views.post_comment, name='post_comment'),
    path('feed/post/<int:post_id>/delete/', views.post_delete, name='post_delete'),
    path('feed/comment/<int:comment_id>/delete/', views.post_comment_delete, name='post_comment_delete'),

    # Chat tizimi (Ustoz va O'quvchilar muloqoti)
    path('chat/', views.chat_view, name='chat'),
    path('chat/<int:user_id>/', views.chat_view, name='chat_with_user'),
    path('chat/api/send/', views.chat_send_message_api, name='chat_send_message'),
    path('chat/api/messages/<int:partner_id>/', views.chat_get_messages_api, name='chat_get_messages'),
    path('chat/api/global-check/', views.chat_global_check_api, name='chat_global_check'),
    path('chat/api/share-contacts/', views.get_share_contacts_api, name='get_share_contacts_api'),

    # Post va baholarni chatga ulashish (Share to chat)
    path('feed/post/<int:post_id>/share/', views.post_share_to_chat, name='post_share_to_chat'),
    path('student/grades/<int:grade_id>/share/', views.grade_share_to_chat, name='grade_share_to_chat'),
    path('chat/api/message/<int:message_id>/delete/', views.chat_delete_message_api, name='chat_delete_message'),
    path('chat/api/message/<int:message_id>/forward/', views.chat_forward_message_api, name='chat_forward_message'),
    path('chat/api/conversation/<int:partner_id>/clear/', views.chat_clear_history_api, name='chat_clear_history'),
    path('chat/api/conversation/<int:partner_id>/delete/', views.chat_delete_conversation_api, name='chat_delete_conversation'),
    path('chat/api/user/<int:user_id>/edit-name/', views.chat_edit_partner_name_api, name='chat_edit_partner_name'),
    path('chat/api/user/<int:partner_id>/toggle-block/', views.chat_toggle_block_api, name='chat_toggle_block'),
    path('chat/api/user/<int:partner_id>/block-status/', views.chat_block_status_api, name='chat_block_status'),
    path('chat/api/search-users/', views.chat_search_users_api, name='chat_search_users'),

    # Sozlamalar
    path('settings/', views.settings_view, name='settings_view'),
    path('settings/api/save/', views.settings_api_save, name='settings_api_save'),
]


