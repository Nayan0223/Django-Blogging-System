from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Public routes
    path('', views.home, name='home'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('search/', views.search_posts, name='search_posts'),
    path('technology/', views.technology, name='technology'),
    path('lifestyle/', views.lifestyle, name='lifestyle'),
    path('category/<str:category>/', views.category_posts, name='category_posts'),
    path('tag/<slug:tag_slug>/', views.posts_by_tag, name='posts_by_tag'),
    path('subscribe/', views.subscribe, name='subscribe'),
    path('about/', views.about, name='about'),
    path('author/<str:username>/', views.user_public_profile, name='user_public_profile'),
    path('posts/', views.all_posts, name='all_posts'),
    path('gallery/', views.image_gallery, name='image_gallery'),
    
    # Authentication
    path('login/', auth_views.LoginView.as_view(
        template_name='auth/login.html'
    ), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('register/', views.register, name='register'),
    
    # User routes (require login)
    path('dashboard/', views.dashboard, name='dashboard'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('create-post/', views.create_post, name='create_post'),
    path('my-posts/', views.my_posts, name='my_posts'),
    path('my-comments/', views.my_comments, name='my_comments'),
    path('post/<int:pk>/edit/', views.edit_post, name='edit_post'),
    path('post/<int:pk>/delete/', views.delete_post, name='delete_post'),
    path('post/<int:pk>/like/', views.like_post, name='like_post'),
    path('post/<int:pk>/publish/', views.publish_post, name='publish_post'),
    
    # Custom Admin
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/users/', views.admin_users, name='admin_users'),
    path('admin-dashboard/posts/', views.admin_post_list,name='admin_post_list'),
    path('admin-dashboard/tags/', views.admin_tags, name='admin_tags'),
    path('admin-dashboard/comments/', views.admin_comments, name='admin_comments'),
    path('admin-dashboard/subscribers/', views.subscriber_list, name='subscriber_list'),
    path('admin-dashboard/content/', views.admin_content, name='admin_content'),
    
    # Admin Actions
    path('admin-dashboard/users/<int:pk>/delete/', views.admin_delete_user, name='admin_delete_user'),
    path('admin-dashboard/users/add/', views.admin_add_user, name='admin_add_user'),
    path('admin-dashboard/users/<int:pk>/edit/', views.admin_edit_user, name='admin_edit_user'),
    path('admin-dashboard/users/<int:pk>/change-password/', views.admin_change_user_password, name='admin_change_user_password'),
    path('admin-dashboard/categories/', views.admin_categories, name='admin_categories'),
    path('admin-dashboard/tags/<int:pk>/delete/', views.admin_delete_tag, name='admin_delete_tag'),
    path('admin-dashboard/categories/<int:pk>/delete/', views.admin_delete_category, name='admin_delete_category'),
    path('admin-dashboard/comments/<int:pk>/delete/', views.admin_delete_comment, name='admin_delete_comment'),
    path('admin-dashboard/comments/<int:pk>/approve/', views.admin_approve_comment, name='admin_approve_comment'),
    path('admin-dashboard/posts/<int:pk>/unpublish/', views.admin_post_unpublish, name='admin_post_unpublish'),
    path('admin-dashboard/posts/<int:pk>/approve/', views.admin_post_approve, name='admin_post_approve'),
    
    # Note: Admin routes are now in blogging_system/urls.py (before Django admin)
]

