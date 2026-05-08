# myapp/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from taggit.managers import TaggableManager

class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

class Post(models.Model):
    CATEGORY_CHOICES = [
        ('technology', 'Technology'),
        ('lifestyle', 'Lifestyle'),
        ('design', 'Design'),
        ('culture', 'Culture'),
        ('business', 'Business'),
        ('other', 'Other'),
    ]
    
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    image = models.ImageField(upload_to='blog_images/', blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='posts')
    likes = models.ManyToManyField(User, related_name='blog_posts', blank=True)
    is_published = models.BooleanField(default=False)
    newsletter_sent = models.BooleanField(default=False)
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    tags = TaggableManager()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
        
    def total_likes(self):
        return self.likes.count()


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    guest_name = models.CharField(max_length=100, blank=True)
    guest_email = models.EmailField(blank=True)
    content = models.TextField()
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=True)
 
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.author:
            return f'Comment by {self.author.username} on {self.post.title}'
        return f'Comment by {self.guest_name} (Guest) on {self.post.title}'


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(max_length=500, blank=True)
    profile_image = models.ImageField(upload_to='profile_pics/', default='profile_pics/default.jpg', blank=True)
    website = models.URLField(blank=True)
    
    # Social Links
    twitter = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    github = models.URLField(blank=True)
    
    def __str__(self):
        return f'{self.user.username} Profile'

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

@receiver(post_save, sender=Post)
def send_newsletter(sender, instance, created, **kwargs):
    if instance.is_published and not instance.newsletter_sent:
        subscribers = Subscriber.objects.all()
        recipient_list = [s.email for s in subscribers]
        
        if recipient_list:
            subject = f"New Post Published: {instance.title}"
            message = f"Hello,\n\nA new post '{instance.title}' has been published on our blog.\n\nRead it here: http://127.0.0.1:8000/post/{instance.pk}/\n\nThank you for subscribing!"
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                recipient_list,
                fail_silently=False,
            )
            
            # Update the flag so we don't send again
            instance.newsletter_sent = True
            instance.save(update_fields=['newsletter_sent'])
