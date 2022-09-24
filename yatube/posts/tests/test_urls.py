from http import HTTPStatus

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.cache import cache

from posts.models import Post, Group

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.author = User.objects.create_user(username='author')
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.index = '/'
        cls.group_posts = f'/group/{cls.group.slug}/'
        cls.profile = f'/profile/{cls.user}/'
        cls.post_by_id = f'/posts/{cls.post.id}/'
        cls.post_create = '/create/'
        cls.post_edit = f'/posts/{cls.post.id}/edit/'
        cls.login = '/auth/login/'

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(self.author)
        cache.clear()

    def test_response(self):
        """Тестирует возвращается ли код ответа 200 при
        обращении к эндпоинтам для любого типа пользователя"""
        url_names = {
            'index': self.index,
            'group_posts': self.group_posts,
            'profile': self.profile,
            'post_by_id': self.post_by_id,
        }

        for adress in url_names.values():
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_response_authorized(self):
        """Возвращает статус-код обращения авторизованным
        пользователем к эндпоинтам для создания или редактирования
        поста"""
        url_names = {
            'create': self.post_create,
            'post_edit': self.post_edit,
        }

        for adress in url_names.values():
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress)

                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_redirect_anonymous(self):
        """Тестирует статус-код редиректа для неавторизованного
        пользователя при обращени к эндпоинтам создания или
        редактирования поста"""
        url_names = {
            'create': self.post_create,
            'post_edit': self.post_edit,
        }

        for adress in url_names.values():
            with self.subTest(adress=adress):
                response = self.guest_client.get(adress)

                self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_unexisting_page(self):
        """Тестирует статус-код возвращаемый при обращении
        по несуществующему эндпоинту"""
        response = self.guest_client.get('/unexisting_page/')

        self.assertTemplateUsed(response, 'core/404.html')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_create_redirect_anonymous_to_login(self):
        """Тестирует редирект неавторизованного пользователя на
        страницу логина при попытке создания поста"""
        login_url = self.login
        post_create_url = self.post_create
        target_url = f'{login_url}?next={post_create_url}'

        response = self.guest_client.get(self.post_create, follow=True)

        self.assertRedirects(response, target_url)

    def test_edit_redirect_anonymous_to_login(self):
        """Тестирует редирект неавторизованного пользователя на
        страницу логина при попытке редактирования поста"""
        login_url = self.login
        post_edit_url = self.post_edit
        target_url = f'{login_url}?next={post_edit_url}'

        response = self.guest_client.get(
            self.post_edit,
            follow=True
        )

        self.assertRedirects(response, target_url)

    def test_urls_correct_template(self):
        """Тестирует использование корректных шаблонов
        для рендеринге страниц"""
        templates_url_names = {
            self.index: 'posts/index.html',
            self.group_posts: 'posts/group_list.html',
            self.profile: 'posts/profile.html',
            self.post_by_id: 'posts/post_detail.html',
            self.post_edit: 'posts/create_post.html',
            self.post_create: 'posts/create_post.html',
        }

        for adress, template in templates_url_names.items():
            with self.subTest(address=adress):
                response = self.authorized_client.get(adress)

                self.assertTemplateUsed(response, template)

    def test_not_author_edit_post(self):
        """Проверяет, что не автор поста не может редактировать пост"""
        post_detail = self.post_by_id

        response = self.authorized_client_author.get(
            self.post_edit,
            follow=True
        )

        self.assertRedirects(response, post_detail)
