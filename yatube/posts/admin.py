from django.contrib import admin

from .models import Follow, Post, Group, Comment


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('pk', 'text', 'pub_date', 'author', 'group')
    list_editable = ('group',)
    search_fields = ('text',)
    list_filter = ('pub_date',)
    empty_value_display = '-пусто-'


@admin.register(Group)
class GroupAdmin (admin.ModelAdmin):
    list_display = (
        'pk',
        'title',
        'slug',
        'description'
    )
    search_fields = ('title', 'description',)
    list_filter = ('description',)
    empty_value_display = ('-пусто-')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'post',
        'author',
        'text',
        'created'
    )
    search_fields = ('text', 'post', 'author',)
    list_filter = ('post',)
    empty_value_display = ('-пусто-')


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'author',
        'user'
    )
    search_fields = ('author', 'user',)
    list_filter = ('author',)
    empty_value_display = ('-пусто-')
