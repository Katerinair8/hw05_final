# Generated by Django 2.2.16 on 2022-09-15 08:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0007_post_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='group',
            name='slug',
            field=models.SlugField(max_length=100, unique=True, verbose_name='slug'),
        ),
    ]