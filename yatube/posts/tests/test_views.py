from typing_extensions import Self
from django import forms
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from posts.models import Group, Post

User = get_user_model()

class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )
        
    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author_client = Client()
        self.author_client.force_login(PostPagesTests.user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs = {
                'slug': f'{self.group.slug}'}): 'posts/group_list.html',
            reverse('posts:profile', kwargs = {
                'username': f'{self.user.username}'}): 'posts/profile.html',
            reverse('posts:post_detail', kwargs = {
                'post_id': f'{self.post.id}'}): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs = {
                'post_id': f'{self.post.id}'}): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.author_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.guest_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        post_author_0 = first_object.author
        post_text_0 = first_object.text
        post_group_0 = first_object.group
        self.assertEqual(post_author_0.username, 'auth')
        self.assertEqual(post_text_0, 'Тестовый пост')
        self.assertEqual(post_group_0.title, 'Тестовая группа')

    def test_group_list_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = (self.guest_client.
            get(reverse('posts:group_list', kwargs = {
                'slug': f'{self.group.slug}'})))
        self.assertEqual(response.context.get(
            'group').title, 'Тестовая группа')
        self.assertEqual(response.context.get(
            'group').slug, 'Тестовый слаг')
        self.assertEqual(response.context.get(
            'group').description, 'Тестовое описание')

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = (self.authorized_client.
            get(reverse('posts:profile', kwargs = {
                'username': f'{self.user.username}'})))
        self.assertEqual(response.context.get('user').username, 'HasNoName')

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = (self.guest_client.
            get(reverse('posts:post_detail', kwargs = {
                'post_id': f'{self.post.id}'})))
        self.assertEqual(response.context.get('post').author.username, 'auth')
        self.assertEqual(response.context.get('post').text, 'Тестовый пост')
        self.assertEqual(response.context.get(
            'post').group.title, 'Тестовая группа')

    def test_create_post_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_create_post_edit_show_correct_context(self):
        """
        Шаблон create_post для редактирования
        сформирован с правильным контекстом.
        """
        response = self.author_client.get(reverse(
            'posts:post_edit', kwargs = {'post_id': f'{self.post.id}'}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_showed_on_correct_pages(self):
        """
        Проверка, что если при создании поста указать группу,
        то этот пост появляется на главной странице сайта,
        на странице выбранной группы, в профайле пользователя.
        Проверка, что этот пост не попал в группу,
        для которой не был предназначен.
        """
        page_names = [
        reverse('posts:index'),
        reverse('posts:group_list', kwargs = {
                'slug': f'{PostPagesTests.group.slug}'}),
        reverse('posts:profile', kwargs = {
                'username': f'{PostPagesTests.user.username}'})
        ]
        for page_name in page_names:
            with self.subTest(page_name=page_name):
                response = self.authorized_client.get(page_name)
                object = response.context.get('page_obj').object_list
                self.assertIn(self.post, object) 
        
        
class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Page_user')
        cls.group = Group.objects.create(
            title='Тестовая группа1',
            slug='Тестовый слаг1',
            description='Тестовое описание группы1',
        )
        cls.posts = []
        for i in range(0, 11):
            cls.posts.append(Post.objects.create(
                text=f'Тестовый текст поста{i}',
                author=cls.user,
                group=cls.group,
            ))
   
    def setUp(self):
        self.guest_client = Client()
       
    def test_first_page_contains_ten_records(self):
        """
        Проверка количества постов на 1 странице
        index, group_list, profile.
        """
        page_names = [
        reverse('posts:index'),
        reverse('posts:group_list', kwargs = {
                'slug': f'{self.group.slug}'}),
        reverse('posts:profile', kwargs = {
                'username': f'{self.user.username}'})
        ]
        for page_name in page_names:
            with self.subTest(page_name=page_name):
                response = self.guest_client.get(page_name)
                self.assertEqual(len(response.context['page_obj']), 10)   

    def test_second_page_contains_one_record(self):
        """
        Проверка количества постов на 2 странице
        index, group_list, profile.
        """
        page_names = [
        reverse('posts:index'),
        reverse('posts:group_list', kwargs = {
                'slug': f'{self.group.slug}'}),
        reverse('posts:profile', kwargs = {
                'username': f'{self.user.username}'})
        ]
        for page_name in page_names:
            with self.subTest(page_name=page_name):
                response = self.guest_client.get(reverse('posts:index') + '?page=2')
                self.assertEqual(len(response.context['page_obj']), 1)