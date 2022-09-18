from http import HTTPStatus

from django import forms
from django.urls import reverse
from django.core.paginator import Page
from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.cache import cache

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

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
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
        first_state = self.authorized_client.get(reverse('posts:index'))
        post_1 = Post.objects.get(pk=1)
        post_1.text = 'Измененный текст'
        post_1.save()
        second_state = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(first_state.content, second_state.content)
        cache.clear()
        third_state = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(first_state.content, third_state.content)

    def test_user_can_follow(self):
        """
        Авторизованный пользователь может подписываться
        на других пользователей и удалять их из подписок
        """
        follower = User.objects.create_user(username='follower')
        following = User.objects.create_user(username='following')
        Follow.objects.create(
            user=follower,
            author=following
        )
        before_follow = Follow.objects.all().count()
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                args=(following,))
        )

        self.assertEqual(Follow.objects.all().count(), before_follow + 1)

        self.authorized_client.get(
            reverse('posts:profile_unfollow', args=(following,))
        )

        self.assertEqual(Follow.objects.all().count(), before_follow)

    def test_post_for_follower(self):
        """
        Новая запись пользователя появляется в ленте тех,
        кто на него подписан
        """
        author = User.objects.create_user(username='Author')
        post_for_following = Post.objects.create(
            author=author,
            text='Текст с большим количеством букв',
            group=self.group,
        )
        self.authorized_client.get(
            reverse('posts:profile_follow', kwargs={'username': author})
        )
        follower_index_url = reverse('posts:follow_index')
        response = self.authorized_client.get(follower_index_url)
        object = response.context['page_obj'][0].text

        self.assertEqual(object, post_for_following.text)

        self.authorized_client.get(
            reverse('posts:profile_unfollow', kwargs={'username': author})
        )
        response = self.authorized_client.get(follower_index_url)
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
                    f'На странице {page} показывается \
                    {settings.POST_PER_PAGE} постов'
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
