from http import HTTPStatus
import shutil
import tempfile

from django.urls import reverse
from django.test import Client, TestCase, override_settings
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from ..forms import PostForm, Comment
from ..models import Post, Group

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()


    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Валидная форма создает новый пост."""
        post_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый текст',
            'author': self.user,
            'image': uploaded,
        }

        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        self.assertRedirects(
            response,
            reverse('posts:profile', args=(PostFormTests.post.author,))
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый текст',
                author=self.user,
                image='posts/small.gif'
            ).exists()
        )

    def test_post_edit(self):
        """Валидная форма редактирует пост."""
        post_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст второй',
            'author': self.user,
            'group': self.group.id,
        }

        response = self.authorized_client.post(
            reverse('posts:post_edit', args=(PostFormTests.post.id,)),
            data=form_data,
            follow=True
        )
        redirect_url = reverse(
            'posts:post_detail',
            args=(PostFormTests.post.id,)
        )

        self.assertRedirects(response, redirect_url)
        self.assertEqual(Post.objects.count(), post_count)
        self.assertTrue(
            Post.objects.filter(
                author=self.user,
                text='Тестовый текст второй',
                group=self.group,
            ).exists()
        )

    def test_comments(self):
        """Авторизированный пользователь может комментировать посты"""

        post_to_comment = self.post
        current_user = User.objects.create(username="Authorized_user")
        self.authorized_client.force_login(current_user)
        comments_count = Comment.objects.filter(
            post_id=post_to_comment.id
        ).count()
        form_data = {
            'post': post_to_comment,
            'author': current_user,
            'text': 'test_comment',
        }
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment',
                args=(post_to_comment.id,)),
                data=form_data,
                follow=True
        )
        comments_after_adding = Post.objects.filter(
            id=post_to_comment.id
        )
        redirect_url = reverse(
            'posts:post_detail',
            args=(PostFormTests.post.id,)
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(
            Comment.objects.filter(
                author=current_user,
                text='test_comment',
                ).exists()
        )
        self.assertEqual(comments_after_adding.count(), comments_count + 1)
        self.assertRedirects(response, redirect_url)
