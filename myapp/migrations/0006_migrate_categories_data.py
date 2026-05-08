from django.db import migrations
from django.utils.text import slugify

def migrate_categories(apps, schema_editor):
    Post = apps.get_model('myapp', 'Post')
    Category = apps.get_model('myapp', 'Category')

    for post in Post.objects.all():
        if post.category_old:
            category_name = post.category_old.capitalize() # e.g. 'technology' -> 'Technology'
            slug = slugify(category_name)
            
            # Get or create the category
            category, created = Category.objects.get_or_create(
                slug=slug,
                defaults={'name': category_name}
            )
            
            post.category = category
            post.save()

def reverse_migrate_categories(apps, schema_editor):
    Post = apps.get_model('myapp', 'Post')
    for post in Post.objects.all():
        if post.category:
            post.category_old = post.category.slug
            post.save()

class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0005_post_category'),
    ]

    operations = [
        migrations.RunPython(migrate_categories, reverse_migrate_categories),
    ]
