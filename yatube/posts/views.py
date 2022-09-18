from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page

from .forms import PostForm, CommentForm
from .models import Post, Group, User, Follow
from .utils import paginate_objects


@cache_page(20, key_prefix='index_page')
def index(request):
    posts = Post.objects.all()
    page_obj = paginate_objects(posts, request)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    page_obj = paginate_objects(posts, request)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    user = request.user
    author = get_object_or_404(User, username=username)
    post_list = author.posts.all()
    following_object = Follow.objects.filter(author=author)
    page_obj = paginate_objects(post_list, request)
    if user == author or following_object.exists():
        following = True
    else:
        following = False
    context = {
        'page_obj': page_obj,
        'author': author,
        'following': following,
        'user': user,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm()
    comments = post.comments.all()
    context = {
        'post': post,
        'form': form,
        'comments': comments,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request, method='POST'):
    form = PostForm(
        request.POST or None,
        files=request.FILES or None
    )
    if request.method == method:
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('posts:profile', username=post.author)
    context = {
        'form': form,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def post_edit(request, post_id: int):
    post = get_object_or_404(Post, pk=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if request.user == post.author:
        if request.method == 'POST':
            if form.is_valid():
                form.save()
                return redirect('posts:post_detail', post_id=post_id)
    else:
        return redirect('posts:post_detail', post_id=post_id)
    context = {
        'is_edit': True,
        'post': post,
        'form': form,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    context = {
        'form': form,
    }
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
        return redirect('posts:post_detail', post_id=post_id)
    return redirect('posts:post_detail', context)


@login_required
def follow_index(request):
    user = request.user
    post_list = Post.objects.filter(
        author__following__user=request.user)
    page_obj = paginate_objects(post_list, request)
    context = {
        'username': user,
        'page_obj': page_obj,
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    user = request.user
    author = get_object_or_404(User, username=username)
    if author != user and not Follow.objects.filter(
        user=user, author=author
    ).exists():
        Follow.objects.create(user=user, author=author)
    return redirect('posts:follow_index')


@login_required
def profile_unfollow(request, username):
    user = request.user
    author = get_object_or_404(User, username=username)
    if author != user and author is not Follow.objects.filter(
        user=request.user, author=author
    ).exists():
        following = Follow.objects.filter(user=user, author=author)
        following.delete()
    return redirect('posts:index')
