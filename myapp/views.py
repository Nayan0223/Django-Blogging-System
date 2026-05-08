from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.db import IntegrityError
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from taggit.models import Tag
from .models import Post, Comment, Category, Subscriber, UserProfile
from .forms import PostForm, CommentForm, GuestCommentForm, AdminUserCreationForm, UserProfileForm



def home(request):
    """Display all published posts"""
    post_list = Post.objects.filter(is_published=True).order_by('-created_at')
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(post_list, 10) # 10 posts per page
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)

    # Get all categories with post counts for sidebar
    categories = Category.objects.annotate(count=Count('posts', filter=Q(posts__is_published=True)))
    
    return render(request, 'blog/home.html', {
        'posts': posts,
        'categories': categories,
        'page_obj': posts
    })


def post_detail(request, pk):
    """View individual post with comments"""
    post = get_object_or_404(Post, pk=pk)
    
    # Increment views count
    from django.db.models import F
    Post.objects.filter(pk=pk).update(views_count=F('views_count') + 1)
    # Reload the object to get updated views_count
    post.refresh_from_db()
    
    # Only fetch top-level comments (parent=None)
    comments = post.comments.filter(is_approved=True, parent=None).order_by('-created_at')

    if request.method == 'POST':
        if request.user.is_authenticated:
            form = CommentForm(request.POST)
            if form.is_valid():
                comment = form.save(commit=False)
                comment.post = post
                comment.author = request.user
                
                # Check for parent comment (Reply)
                parent_id = request.POST.get('parent_id')
                if parent_id:
                    parent_comment = Comment.objects.get(id=parent_id)
                    # Optional: Check if parent belongs to same post to prevent misuse
                    if parent_comment.post == post:
                         comment.parent = parent_comment

                comment.save()
                messages.success(request, 'Your comment has been posted successfully!')
                return redirect('post_detail', pk=post.pk)
        else:
            form = GuestCommentForm(request.POST)
            if form.is_valid():
                comment = form.save(commit=False)
                comment.post = post
                comment.author = None  # Explicitly set author to None for guests
                
                # Check for parent comment (Reply)
                parent_id = request.POST.get('parent_id')
                if parent_id:
                     try:
                        parent_comment = Comment.objects.get(id=parent_id)
                        if parent_comment.post == post:
                            comment.parent = parent_comment
                     except Comment.DoesNotExist:
                        pass
                        
                comment.save()
                messages.success(request, 'Your comment has been posted successfully!')
                return redirect('post_detail', pk=post.pk)
    else:
        if request.user.is_authenticated:
            form = CommentForm()
        else:
            form = GuestCommentForm()

    return render(request, 'blog/post_detail.html', {
        'post': post,
        'comments': comments,
        'form': form
    })




@login_required
def create_post(request):
    """Create a new blog post"""
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, 'Post created successfully!')
            return redirect('my_posts')
    else:
        form = PostForm()
    return render(request, 'dashboard/create_post.html', {'form': form})


@login_required
def edit_post(request, pk):
    """Edit own post"""
    post = get_object_or_404(Post, pk=pk)
    if post.author != request.user and not request.user.is_staff:
        messages.error(request, 'You do not have permission to edit this post.')
        return redirect('home')
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, 'Post updated successfully!')
            return redirect('post_detail', pk=pk)
    else:
        form = PostForm(instance=post)
    return render(request, 'dashboard/edit_post.html', {'form': form, 'post': post})


@login_required
def delete_post(request, pk):
    """Delete own post"""
    # try:
    #     post = Post.objects.get(pk=pk)
    # except Post.DoesNotExist:
    #     messages.error(request, 'Post does not exist or has already been deleted.')
    #     return redirect('admin_post_list')
    
    # We will stick to get_object_or_404 but we can check if we want to suppress it.
    # Actually, explicit try-except is better for user experience here.
    try:
        post = Post.objects.get(pk=pk)
    except Post.DoesNotExist:
        messages.error(request, 'The post you are trying to delete does not exist.')
        # Redirect to a safe place depending on user type
        if request.user.is_staff:
             return redirect('admin_post_list')
        return redirect('home')
    # Only allow superusers (admins) to delete posts
    if not request.user.is_superuser:
        messages.error(request, 'Only admin can delete posts.')
        return redirect('home')
    
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Post deleted successfully!')
        if request.user.is_staff:
            return redirect('admin_post_list')
        return redirect('my_posts')
    # Use a generic confirmation or keep simplified, potentially move to dashboard later
    return render(request, 'blog/delete_post.html', {'post': post})


@login_required
def publish_post(request, pk):
    """Allow author to publish their own post"""
    post = get_object_or_404(Post, pk=pk)
    
    # Check permission
    if post.author != request.user and not request.user.is_superuser:
        messages.error(request, "You are not authorized to perform this action.")
        return redirect('post_detail', pk=pk)
        
    if request.method == 'POST':
        post.is_published = True
        post.save()
        messages.success(request, f"Post '{post.title}' has been published successfully!")
        
    return redirect('post_detail', pk=pk)


@login_required
def my_posts(request):
    """View all posts by the logged-in user"""
    post_list = Post.objects.filter(author=request.user).order_by('-created_at')
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(post_list, 10)
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)
        
    return render(request, 'dashboard/my_posts.html', {'posts': posts, 'page_obj': posts})


@login_required
def dashboard(request):
    """User dashboard view"""
    # Redirect superusers to admin dashboard
    if request.user.is_superuser:
        return redirect('admin_dashboard')

    user = request.user
    my_posts = Post.objects.filter(author=user).order_by('-created_at')
    
    context = {
        'recent_posts': my_posts[:5],
        'total_posts': my_posts.count(),
        'published_posts': my_posts.filter(is_published=True).count()
    }
    return render(request, 'dashboard/dashboard.html', context)


@login_required
def edit_profile(request):
    """Edit user profile"""
    # Ensure profile exists for existing users
    UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            if request.user.is_superuser:
                return redirect('admin_dashboard')
            return redirect('dashboard')
    else:
        form = UserProfileForm(instance=request.user.profile)
    return render(request, 'dashboard/edit_profile.html', {'form': form})



@login_required
def my_comments(request):
    """View all comments by the logged-in user"""
    comment_list = Comment.objects.filter(author=request.user).order_by('-created_at')
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(comment_list, 10)
    try:
        comments = paginator.page(page)
    except PageNotAnInteger:
        comments = paginator.page(1)
    except EmptyPage:
        comments = paginator.page(paginator.num_pages)

    return render(request, 'dashboard/my_comments.html', {'comments': comments, 'page_obj': comments})


def search_posts(request):
    """Search for posts"""
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    post_list = []
    if query:
        post_list = Post.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query),
            is_published=True
        ).order_by('-created_at')
        if category:
            post_list = post_list.filter(category__slug=category)
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(post_list, 10)
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)

    return render(request, 'blog/search_results.html', {
        'posts': posts, 
        'query': query,
        'category': category,
        'page_obj': posts
    })


# Category-based views
def technology(request):
    """Display technology-related posts"""
    posts = Post.objects.filter(is_published=True, category__slug='technology').order_by('-created_at')
    featured_post = posts.first() if posts else None
    other_posts = posts[1:13] if posts.count() > 1 else posts
    return render(request, 'pages/technology.html', {
        'posts': other_posts,
        'featured_post': featured_post
    })


def lifestyle(request):
    """Display lifestyle-related posts"""
    posts = Post.objects.filter(is_published=True, category__slug='lifestyle').order_by('-created_at')
    featured_post = posts.first() if posts else None
    other_posts = posts[1:13] if posts.count() > 1 else posts
    return render(request, 'pages/lifestyle.html', {
        'posts': other_posts,
        'featured_post': featured_post
    })


def category_posts(request, category):
    """Display posts by category"""
    category_obj = get_object_or_404(Category, slug=category)
    
    posts = Post.objects.filter(is_published=True, category=category_obj).order_by('-created_at')
    featured_post = posts.first() if posts else None
    other_posts = posts[1:13] if posts.count() > 1 else posts
    
    return render(request, 'blog/category.html', {
        'posts': other_posts,
        'featured_post': featured_post,
        'category': category_obj
    })


def posts_by_tag(request, tag_slug):
    """Display posts by tag"""
    tag = get_object_or_404(Tag, slug=tag_slug)
    posts = Post.objects.filter(is_published=True, tags__in=[tag]).order_by('-created_at')
    
    # Reuse category template or create a new one. Let's use search_results or category.
    # Using category template for consistent layout
    return render(request, 'blog/category.html', {
        'posts': posts,
        'category': tag, # Passing tag as category for title display
        'is_tag': True # Flag to adjust title in template
    })

def subscribe(request):
    """Handle newsletter subscription"""
    from .forms import SubscriberForm
    if request.method == 'POST':
        form = SubscriberForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'You have successfully subscribed to our newsletter!')
        else:
            messages.error(request, 'This email is already subscribed or invalid.')
    
    # Redirect back to the page they came from, or home if unknown
    next_url = request.META.get('HTTP_REFERER', 'home')
    return redirect(next_url)


def about(request):
    """Display about page with stats"""
    from .models import Post, Comment
    from django.contrib.auth.models import User
    
    total_posts = Post.objects.filter(is_published=True).count()
    total_users = User.objects.count()
    total_comments = Comment.objects.filter(is_approved=True).count()
    
    return render(request, 'pages/about.html', {
        'total_posts': total_posts,
        'total_users': total_users,
        'total_comments': total_comments,
    })


def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to your dashboard.')
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'auth/register.html', {'form': form})



@login_required
def custom_logout(request):
    """Logout the user and redirect to home"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


def user_public_profile(request, username):
    """Display public profile of a user with their published posts"""
    author = get_object_or_404(User, username=username)
    posts = Post.objects.filter(author=author, is_published=True).order_by('-created_at')
    
    return render(request, 'blog/public_profile.html', {
        'author': author,
        'posts': posts
    })


def all_posts(request):
    """Display all published posts"""
    posts = Post.objects.filter(is_published=True).order_by('-created_at')
    
    return render(request, 'blog/all_posts.html', {
        'posts': posts
    })

def image_gallery(request):
    """Display a masonry image gallery of all published posts with cover images"""
    post_list = Post.objects.filter(is_published=True).exclude(image='').exclude(image__isnull=True).order_by('-created_at')

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(post_list, 24)  # 24 images per page
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)

    return render(request, 'blog/image_gallery.html', {
        'posts': posts,
        'page_obj': posts,
    })


@login_required
def admin_dashboard(request):
    """Custom Admin Dashboard View"""
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('home')

    # Stats
    total_users = User.objects.count()
    total_posts = Post.objects.count()
    total_comments = Comment.objects.count()
    total_subscribers = Subscriber.objects.count()
    
    # Calculate total likes across all posts
    # Since 'likes' is a ManyToMany field, we can count the relations directly
    total_likes = Post.likes.through.objects.count()
    
    # Recent Data
    latest_users = User.objects.order_by('-date_joined')[:5]
    latest_posts = Post.objects.order_by('-created_at')[:5]

    context = {
        'total_users': total_users,
        'total_posts': total_posts,
        'total_comments': total_comments,
        'total_subscribers': total_subscribers,
        'total_likes': total_likes,
        'latest_users': latest_users,
        'latest_posts': latest_posts,
        'popular_posts': Post.objects.order_by('-views_count')[:5],
        'is_admin_page': True  # For conditional template rendering
    }
    return render(request, 'custom_admin/dashboard.html', context)

@login_required
def admin_users(request):
    """Admin: User Management"""
    if not request.user.is_superuser:
        return redirect('home')
    
    search_query = request.GET.get('q', '')
    user_list = User.objects.all().order_by('-date_joined')
    
    if search_query:
        user_list = user_list.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(user_list, 10)
    try:
        users = paginator.page(page)
    except PageNotAnInteger:
        users = paginator.page(1)
    except EmptyPage:
        users = paginator.page(paginator.num_pages)
        
    return render(request, 'custom_admin/user_list.html', {'users': users, 'search_query': search_query, 'page_obj': users})

@login_required
def admin_post_list(request):
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')

    posts_list = Post.objects.select_related(
        'category',
        'author'
    ).all().order_by('-created_at')

    if search_query:
        posts_list = posts_list.filter(title__icontains=search_query)

    if status_filter == 'published':
        posts_list = posts_list.filter(is_published=True)
    elif status_filter == 'draft':
        posts_list = posts_list.filter(is_published=False)
        
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(posts_list, 10)
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)

    context = {
        'posts': posts,
        'search_query': search_query,
        'status_filter': status_filter,
        'page_obj': posts,
    }

    return render(request, 'custom_admin/post_list.html', context)
@login_required
def admin_comments(request):
    """Admin: Comment Moderation"""
    if not request.user.is_superuser:
        return redirect('home')
    
    search_query = request.GET.get('q', '')
    comment_list = Comment.objects.all().order_by('-created_at')
    
    if search_query:
        comment_list = comment_list.filter(
            Q(content__icontains=search_query) |
            Q(author__username__icontains=search_query) |
            Q(guest_name__icontains=search_query) |
            Q(guest_email__icontains=search_query)
        )

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(comment_list, 10)
    try:
        comments = paginator.page(page)
    except PageNotAnInteger:
        comments = paginator.page(1)
    except EmptyPage:
        comments = paginator.page(paginator.num_pages)
        
    return render(request, 'custom_admin/comment_list.html', {'comments': comments, 'search_query': search_query, 'page_obj': comments})

@login_required
def admin_content(request):
    """Admin: Content Management"""
    if not request.user.is_superuser:
        return redirect('home')
    # Placeholder for categories or other content
    return render(request, 'custom_admin/content.html')

@login_required
def admin_delete_user(request, pk):
    """Admin: Delete User"""
    if not request.user.is_superuser:
        return redirect('home')
    
    user_to_delete = get_object_or_404(User, pk=pk)
    if user_to_delete == request.user:
        messages.error(request, "You cannot delete yourself!")
        return redirect('admin_users')
        
    user_to_delete.delete()
    messages.success(request, f"User {user_to_delete.username} deleted successfully.")
    return redirect('admin_users')

@login_required
def admin_add_user(request):
    """Admin: Add New User"""
    if not request.user.is_superuser:
        return redirect('home')
    
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"User {user.username} created successfully.")
            return redirect('admin_users')
    else:
        form = AdminUserCreationForm()
    
    return render(request, 'custom_admin/add_user.html', {'form': form})

@login_required
def admin_edit_user(request, pk):
    """Admin: Edit User"""
    if not request.user.is_superuser:
        return redirect('home')
    
    user_to_edit = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        user_to_edit.username = request.POST.get('username')
        user_to_edit.email = request.POST.get('email')
        # Checkboxes
        user_to_edit.is_superuser = request.POST.get('is_superuser') == 'on'
        user_to_edit.is_active = request.POST.get('is_active') == 'on'
        
        try:
            user_to_edit.save()
            messages.success(request, f"User {user_to_edit.username} updated successfully.")
            return redirect('admin_users')
        except Exception as e:
            messages.error(request, f"Error updating user: {e}")
    
    return render(request, 'custom_admin/edit_user.html', {'user_obj': user_to_edit})


@login_required
def admin_change_user_password(request, pk):
    """Admin: Change a user's password"""
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('home')

    user_to_update = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not new_password:
            messages.error(request, "Password cannot be empty.")
        elif len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
        elif new_password != confirm_password:
            messages.error(request, "Passwords do not match. Please try again.")
        else:
            user_to_update.set_password(new_password)
            user_to_update.save()
            messages.success(
                request,
                f"Password for @{user_to_update.username} has been changed successfully."
            )
            return redirect('admin_users')

    return render(request, 'custom_admin/change_password.html', {'user_obj': user_to_update})


@login_required
def admin_categories(request):
    if not request.user.is_superuser:
        return redirect('home')

    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            slug = name.lower().replace(' ', '-')
            if Category.objects.filter(slug=slug).exists():
                messages.error(request, f"Category '{name}' (or similar) already exists.")
            else:
                try:
                    Category.objects.create(name=name, slug=slug)
                    messages.success(request, f"Category '{name}' created.")
                except IntegrityError:
                    messages.error(request, f"Error creating category '{name}'. It may already exist.")
            return redirect('admin_categories')

    search_query = request.GET.get('q', '')
    category_list = Category.objects.annotate(
        post_count=Count('posts')
    )

    if search_query:
        category_list = category_list.filter(
            Q(name__icontains=search_query) |
            Q(slug__icontains=search_query)
        )

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(category_list, 10)
    try:
        categories = paginator.page(page)
    except PageNotAnInteger:
        categories = paginator.page(1)
    except EmptyPage:
        categories = paginator.page(paginator.num_pages)

    return render(
        request,
        'custom_admin/category_list.html',
        {'categories': categories, 'search_query': search_query, 'page_obj': categories}
    )


@login_required
def admin_tags(request):
    """Admin: Tag Management"""
    if not request.user.is_superuser:
        return redirect('home')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            slug = name.lower().replace(' ', '-')
            if Tag.objects.filter(slug=slug).exists():
                messages.error(request, f"Tag '{name}' (or similar) already exists.")
            else:
                try:
                    Tag.objects.create(name=name, slug=slug)
                    messages.success(request, f"Tag '{name}' created.")
                except IntegrityError:
                    messages.error(request, f"Error creating tag '{name}'. It may already exist.")
            return redirect('admin_tags')

    search_query = request.GET.get('q', '')
    tag_list = Tag.objects.all()

    if search_query:
        tag_list = tag_list.filter(
            Q(name__icontains=search_query) |
            Q(slug__icontains=search_query)
        )

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(tag_list, 10)
    try:
        tags = paginator.page(page)
    except PageNotAnInteger:
        tags = paginator.page(1)
    except EmptyPage:
        tags = paginator.page(paginator.num_pages)

    return render(
        request,
        'custom_admin/tag_list.html',
        {'tags': tags, 'search_query': search_query, 'page_obj': tags}
    )


@login_required
@login_required
def admin_delete_tag(request, pk):
    """Admin: Delete Tag"""
    if not request.user.is_superuser:
        return redirect('home')
    
    tag = get_object_or_404(Tag, pk=pk)
    tag_name = tag.name
    tag.delete()
    messages.success(request, f"Tag '{tag_name}' deleted.")
    return redirect('admin_tags')


def admin_delete_category(request, pk):
    """Admin: Delete Category"""
    if not request.user.is_superuser:
        return redirect('home')
    
    category = get_object_or_404(Category, pk=pk)
    category.delete()
    messages.success(request, f"Category '{category.name}' deleted.")
    return redirect('admin_categories')


@login_required
def admin_delete_comment(request, pk):
    """Admin: Delete Comment"""
    if not request.user.is_superuser:
        return redirect('home')
    
    comment = get_object_or_404(Comment, pk=pk)
    comment.delete()
    messages.success(request, "Comment deleted successfully.")
    return redirect('admin_comments')


@login_required
def admin_approve_comment(request, pk):
    """Admin: Approve Comment"""
    if not request.user.is_superuser:
        return redirect('home')
    
    comment = get_object_or_404(Comment, pk=pk)
    comment.is_approved = True
    comment.save()
    messages.success(request, "Comment approved successfully.")
    return redirect('admin_comments')


@login_required
def admin_post_unpublish(request, pk):
    """Admin: Unpublish Post"""
    if not request.user.is_staff:
        return redirect('home')
    
    post = get_object_or_404(Post, pk=pk)
    post.is_published = False
    post.save()
    messages.success(request, f"Post '{post.title}' unpublished.")
    return redirect('post_detail', pk=pk)


@login_required
def admin_post_approve(request, pk):
    """Admin: Publish/Approve Post"""
    if not request.user.is_staff:
        return redirect('home')
    
    post = get_object_or_404(Post, pk=pk)
    post.is_published = True
    # If you want to update published_date, do it here. For now just toggle.
    # from django.utils import timezone
    # post.published_at = timezone.now()
    post.save()
    messages.success(request, f"Post '{post.title}' published.")
    return redirect('post_detail', pk=pk)

@login_required
def subscriber_list(request):
    """Admin view for newsletter subscribers"""
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('home')
        
    subscribers = Subscriber.objects.all().order_by('-subscribed_at')
    
    # Search functionality
    query = request.GET.get('q')
    if query:
        subscribers = subscribers.filter(email__icontains=query)

    return render(request, 'custom_admin/subscriber_list.html', {
        'subscribers': subscribers,
        'search_query': query
    })

@login_required
def like_post(request, pk):
    """Toggle like status for a post"""
    post = get_object_or_404(Post, pk=pk)
    if post.likes.filter(id=request.user.id).exists():
        post.likes.remove(request.user)
    else:
        post.likes.add(request.user)
    
    # Redirect to the same page
    return redirect('post_detail', pk=pk)
