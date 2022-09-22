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
    current_user = request.user
    author = get_object_or_404(User, username=username)
    post_list = author.posts.all()
    page_obj = paginate_objects(post_list, request)
    if current_user.is_authenticated:
        following_query = Follow.objects.filter(
            author=author,
            user=current_user
        )
        if following_query.exists():
            following = True
        else:
            following = False
        context = {
            'page_obj': page_obj,
            'author': author,
            'following': following,
        }
        return render(request, 'posts/profile.html', context)
    context = {
        'page_obj': page_obj,
        'author': author,
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
def post_create(request):
    form = PostForm(
        request.POST or None,
        files=request.FILES or None
    )
    if request.method == "POST":
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
    current_user = request.user
    post = get_object_or_404(Post, pk=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if current_user == post.author:
        context = {
            'is_edit': True,
            'post': post,
            'form': form,
        }
        if request.method == 'POST':
            if form.is_valid():
                form.save()
                return redirect('posts:post_detail', post_id=post_id)
        return render(request, 'posts/create_post.html', context)
    else:
        return redirect('posts:post_detail', post_id=post_id)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = post
            comment.save()
            return redirect('posts:post_detail', post_id=post_id)
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    current_user = request.user
    post_list = Post.objects.filter(
        author__following__user=current_user)
    page_obj = paginate_objects(post_list, request)
    context = {
        'user_object': current_user,
        'page_obj': page_obj,
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    current_user = request.user
    author = get_object_or_404(User, username=username)
    if author != current_user and not Follow.objects.filter(
        user=current_user, author=author
    ).exists():
        Follow.objects.create(user=current_user, author=author)
    return redirect('posts:follow_index')


@login_required
def profile_unfollow(request, username):
    current_user = request.user
    author = get_object_or_404(User, username=username)
    if Follow.objects.filter(
        user=current_user, author=author
    ).exists():
        following_query = Follow.objects.filter(
            user=current_user,
            author=author
        )
        following_query.delete()
    return redirect('posts:index')
