# myapp/admin.py
from django.contrib import admin
from .models import Post, Comment, Subscriber

@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at')
    search_fields = ('email',)
    ordering = ('-subscribed_at',)

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'likes_count', 'is_published', 'created_at', 'updated_at')
    list_filter = ('is_published', 'created_at')
    search_fields = ('title', 'content', 'author__username')
    actions = ['publish_posts', 'unpublish_posts']

    def likes_count(self, obj):
        return obj.likes.count()
    likes_count.short_description = 'Likes'

    def publish_posts(self, request, queryset):
        queryset.update(is_published=True)
        self.message_user(request, f'{queryset.count()} posts published.')
    publish_posts.short_description = 'Publish selected posts'

    def unpublish_posts(self, request, queryset):
        queryset.update(is_published=False)
        self.message_user(request, f'{queryset.count()} posts unpublished.')
    unpublish_posts.short_description = 'Unpublish selected posts'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('content', 'author', 'post', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'created_at')
    search_fields = ('content', 'author__username', 'post__title')
    actions = ['approve_comments', 'disapprove_comments']

    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, f'{queryset.count()} comments approved.')
    approve_comments.short_description = 'Approve selected comments'

    def disapprove_comments(self, request, queryset):
        queryset.update(is_approved=False)
        self.message_user(request, f'{queryset.count()} comments disapproved.')
    disapprove_comments.short_description = 'Disapprove selected comments'
        
