from http import HTTPStatus
from urllib import response

from django import forms
from django.urls import reverse
from django.core.paginator import Page
from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile

from ..models import Follow, Group, Post

User = get_user_model()


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Somebody')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Текстовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
        )
        cls.post_create = reverse('posts:post_create')
        cls.index_page = reverse('posts:index')
        cls.group_posts = reverse(
            'posts:group_posts',
            kwargs={'slug': cls.group.slug}
        )
        cls.profile = reverse(
            'posts:profile',
            kwargs={'username': cls.user.username}
        )
        cls.post_detail = reverse(
            'posts:post_detail',
            args=(cls.post.id,)
        )
        cls.post_edit = reverse(
            'posts:post_edit',
            args=(cls.post.id,)
        )
        cls.profile_follow = 'posts:profile_follow'
        cls.profile_unfollow = 'posts:profile_unfollow'

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client_not_follower = Client()
        self.authorized_client_not_follower.force_login(self.user)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            self.index_page: 'posts/index.html',
            self.group_posts: 'posts/group_list.html',
            self.profile: 'posts/profile.html',
            self.post_detail: 'posts/post_detail.html',
            self.post_create: 'posts/create_post.html',
            self.post_edit: 'posts/create_post.html',
        }

        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_create_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        test_pages = (
            self.post_create,
            self.post_edit,
        )

        for page in test_pages:
            response = self.authorized_client.get(page)
            form_fields = {
                'group': forms.fields.ChoiceField,
                'text': forms.fields.CharField,
            }

            for key, expected in form_fields.items():
                with self.subTest(key=key):
                    form_fields = response.context.get('form').fields.get(key)
                    self.assertIsInstance(form_fields, expected)

    def test_index_page_correct_context(self):
        """
        Шаблон index_page сформирован с правильным контекстом
        """
        response = self.authorized_client.get(self.index_page)
        post = response.context['page_obj'][0]

        self.checking_context(post)

    def test_profile_page_correct_context(self):
        """
        Шаблон profile сформирован с правильным контекстом
        """
        response = self.authorized_client.get(self.profile)

        author = response.context['author']
        post = response.context['page_obj'][0]

        self.checking_context(post)
        self.assertEqual(author.username, self.user.username)

    def test_group_page_correct_context(self):
        """
        Шаблон group_posts сформирован с правильным контекстом
        """
        response = self.authorized_client.get(self.group_posts)
        post = response.context['page_obj'][0]
        group = response.context['group']

        self.checking_context(post)
        self.assertEqual(group.slug, self.group.slug)

    def test_post_detail_shows_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом"""
        response = self.client.get(self.post_detail)

        post = response.context.get('post')

        self.checking_context(post)

    def checking_context(self, post):
        """Проверка атрибутов поста."""
        self.assertEqual(post.id, self.post.id)
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.group, self.post.group)
        self.assertEqual(post.image, self.post.image)

    def test_post_group_on_pages(self):
        """
        Если при создании поста указать группу, то этот пост появляется:
        на главной странице сайта
        на странице выбранной группы
        """
        response_index = self.authorized_client.get(self.index_page)
        response_group = self.authorized_client.get(self.group_posts)

        self.assertIn(self.post, response_index.context['page_obj'])
        self.assertIn(self.post, response_group.context['page_obj'])

    def test_post_not_in_other_groups(self):
        """
        Проверяет не попадает ли пост с указанной
        группой в другие группы
        """
        group_with_post = Group.objects.create(
            title='test_group_1',
            slug='test_slug_1',
            description='test_description_1',
        )
        group_without_post = Group.objects.create(
            title='test_group_2',
            slug='test_slug_2',
            description='test_description_2',
        )
        post_test = Post.objects.create(
            author=self.user,
            text='Тестовый текст с кучей букв',
            group=group_with_post,
        )

        response_with_post = self.authorized_client.get(
            reverse(
                'posts:group_posts',
                kwargs={'slug': f'{group_with_post.slug}'}
            )
        )
        response_without_post = self.authorized_client.get(
            reverse(
                'posts:group_posts',
                kwargs={'slug': f'{group_without_post.slug}'}
            )
        )
        context_with_post = response_with_post.context['page_obj']
        context_without_post = response_without_post.context['page_obj']

        self.assertIn(post_test, context_with_post)
        self.assertNotIn(post_test, context_without_post)

    def test_cache_index(self):
        """
        Проверка что на главной странице список записей хранится
        в кеше и обновляется раз в 20 секунд
        """
        response_before_cache = self.authorized_client.get(self.index_page)
        
        post_cached = Post.objects.get(pk=1)
        post_cached.text = 'Измененный текст'
        post_cached.save()

        response_cached = self.authorized_client.get(self.index_page)

        self.assertEqual(
            response_before_cache.content,
            response_cached.content
        )
        self.assertNotIn(
            post_cached.text,
            response_cached.content.decode()
        )

        cache.clear()

        response_clear_cache = self.authorized_client.get(self.index_page)

        self.assertIn(
            post_cached.text,
            response_clear_cache.content.decode()
        )
        self.assertNotEqual(
            response_before_cache.content,
            response_clear_cache.content
        )
    
    def test_image_in_context(self):
        """
        Шаблоны index, profile, group_list, post_detail сформированы
        с правильным контекстом при выводе поста с картинкой
        """
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
            content_type='posts/small.gif'
        )
        test_pages = [
            self.index_page,
            self.group_posts,
            self.profile
        ]
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            self.post_create,
            data=form_data,
            follow=True
        )

        for page in test_pages:
            with self.subTest(page=page):
                response = self.authorized_client.get(page)
                context = response.context['page_obj']
                self.assertEqual(form_data['image'].open().read(), context[0].image.read())

    def test_user_can_follow(self):
        """
        Авторизованный пользователь может подписываться
        на других пользователей
        """
        follower = User.objects.create(username='follower')
        following = User.objects.create(username='following')
        before_follow = Follow.objects.all().count()
        Follow.objects.create(
            user=follower,
            author=following,
        )

        self.assertEqual(Follow.objects.all().count(), before_follow + 1)
        self.assertTrue(
            Follow.objects.filter(
                user=follower,
                author=following,
                ).exists()
        )

    def test_user_can_unfollow(self):
        """
        Авторизованный пользователь может удалять
        других пользователей из подписок
        """
        follower = User.objects.create(username='follower')
        following = User.objects.create(username='following')
        self.authorized_client.get(
            reverse(
                self.profile_follow,
                args=(following,))
        )
        before_unfollow = Follow.objects.all().count()
        self.authorized_client.get(
            reverse(self.profile_unfollow, args=(following,))
        )

        self.assertEqual(Follow.objects.all().count(), before_unfollow - 1)
        self.assertFalse(
            Follow.objects.filter(
                user=follower,
                author=following,
                ).exists()
        )

    def test_post_for_follower(self):
        """
        Новая запись пользователя появляется в ленте тех,
        кто на него подписан
        """
        author = User.objects.create(username='Author')
        user_follower = Follow.objects.create(
            user = User.objects.create(
                username='user_follower'
                ),
            author=author
        )
        self.authorized_client.force_login(user_follower.user)
        user_not_follower = User.objects.create(username='not_follower')
        self.authorized_client_not_follower.force_login(user_not_follower)
        post_for_following = Post.objects.create(
            author=author,
            text='Текст с большим количеством букв',
            group=self.group,
        )
        self.authorized_client.get(
            reverse(self.profile_follow, kwargs={'username': author})
        )
        follower_index_url = reverse('posts:follow_index')
        response = self.authorized_client.get(follower_index_url)
        objects = response.context['page_obj']

        self.assertIn(post_for_following, objects)

        response = self.authorized_client_not_follower.get(follower_index_url)
        objects_count = len(response.context['page_obj'])

        self.assertEqual(objects_count, 0)


class TestingPaginator(TestCase):
    """Проверка паджинатора и наличия класса Page в контексте шаблона"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
        )
        cls.POSTS_FOR_PAGINATOR_TESTING = settings.POST_PER_PAGE + 3
        cls.user = User.objects.create_user(username='Somebody')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.posts_for_test = []
        for test_num in range(1, cls.POSTS_FOR_PAGINATOR_TESTING):
            cls.posts_for_test.append(Post(
                author=cls.user,
                text=f'Test{test_num}',
                group=cls.group))
        Post.objects.bulk_create(cls.posts_for_test)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_pages_contain_ten_records_and_class_page(self):
        """Проверка работы паджинатора и использования
        класса Page в контексте"""
        posts_on_second_page = len(
            self.posts_for_test) - settings.POST_PER_PAGE

        pages = (
            reverse('posts:index'),
            reverse(
                'posts:group_posts',
                kwargs={'slug': f'{self.group.slug}'}
            ),
            reverse(
                'posts:profile',
                kwargs={'username': f'{self.user.username}'}
            ),
        )

        for page in pages:
            with self.subTest(page=page):
                first_page = self.authorized_client.get(page)
                second_page = self.authorized_client.get(page + '?page=2')
                context_first_page = first_page.context['page_obj']
                context_second_page = second_page.context['page_obj']
                self.assertEqual(
                    len(context_first_page),
                    settings.POST_PER_PAGE,
                    f'На странице {page} показывается'
                    f'{settings.POST_PER_PAGE} постов'
                )
                self.assertEqual(
                    len(context_second_page),
                    posts_on_second_page,
                    f'На второй странице {page} '
                    f'должно быть {posts_on_second_page}'
                )
                self.assertIsInstance(
                    context_first_page,
                    Page,
                    f'На станице {page} нет класса Page в контексте'
                )
