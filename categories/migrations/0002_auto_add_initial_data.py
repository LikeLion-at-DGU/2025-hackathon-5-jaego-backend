from django.db import migrations

def create_categories(apps, schema_editor):
    Category = apps.get_model('categories', 'Category')
    Category.objects.bulk_create([
        Category(name='식자재'),
        Category(name='한식'),
        Category(name='중식'),
        Category(name='일식'),
        Category(name='양식'),
        Category(name='분식'),
        Category(name='카페/음료'),
        Category(name='패스트푸드'),
        Category(name='치킨'),
        Category(name='피자'),
        Category(name='베이커리'),
        Category(name='기타')
    ])

class Migration(migrations.Migration):
    dependencies = [
        ('categories', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_categories),
    ]
