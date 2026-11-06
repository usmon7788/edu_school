import tempfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from .models import ChatMessage


class ChatMessageAttachmentTests(SimpleTestCase):
    def test_video_attachments_are_recognized(self):
        for filename in ('clip.mp4', 'clip.WEBM', 'clip.mov'):
            with self.subTest(filename=filename):
                self.assertTrue(ChatMessage(attachment=filename).attachment_is_video)

    def test_non_video_attachments_are_not_recognized_as_video(self):
        for filename in ('notes.pdf', 'photo.jpg', ''):
            with self.subTest(filename=filename):
                message = ChatMessage(attachment=filename or None)
                self.assertFalse(message.attachment_is_video)


class ChatVideoUploadTests(TestCase):
    def test_uploaded_video_is_saved_as_regular_video_attachment(self):
        from .models import User

        sender = User.objects.create_user(username='video-sender', password='test-password')
        receiver = User.objects.create_user(username='video-receiver', password='test-password')
        self.client.force_login(sender)
        video = SimpleUploadedFile('lesson.mp4', b'video data', content_type='video/mp4')

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=Path(media_root)):
                response = self.client.post(
                    reverse('chat_send_message'),
                    {'receiver_id': receiver.id, 'attachment': video},
                )

                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload['status'], 'success')
                self.assertTrue(payload['message']['attachment_is_video'])
                self.assertTrue(payload['message']['attachment_url'].startswith('/media/'))
                self.assertTrue(payload['message']['attachment_url'].endswith('.mp4'))

    def test_camera_video_is_saved_as_video_message(self):
        from .models import User

        sender = User.objects.create_user(username='camera-sender', password='test-password')
        receiver = User.objects.create_user(username='camera-receiver', password='test-password')
        self.client.force_login(sender)
        video = SimpleUploadedFile('recording.webm', b'webm video data', content_type='video/webm')

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=Path(media_root)):
                response = self.client.post(
                    reverse('chat_send_message'),
                    {'receiver_id': receiver.id, 'video_file': video},
                )

                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload['status'], 'success')
                self.assertTrue(payload['message']['is_video'])
                self.assertTrue(payload['message']['video_url'].startswith('/media/'))
