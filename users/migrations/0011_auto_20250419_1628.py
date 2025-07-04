# Generated by Django 5.2 on 2025-04-19 16:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('users', '0010_userprofile_bio'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(blank=True, max_length=100, null=True)),
                ('faculty_institute', models.CharField(blank=True, max_length=100, null=True)),
                ('school', models.CharField(blank=True, max_length=100, null=True)),
                ('keywords', models.TextField(blank=True, null=True)),
                ('position', models.CharField(blank=True, max_length=100, null=True)),
                ('google_scholar_link', models.URLField(blank=True, null=True)),
                ('bio', models.TextField(blank=True, null=True)),
                ('is_profile_completed', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to='auth.user')),
            ],
        ),
        migrations.CreateModel(
            name='Paper',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=500)),
                ('authors', models.JSONField(default=list)),
                ('conference', models.CharField(blank=True, max_length=255, null=True)),
                ('year', models.IntegerField(blank=True, null=True)),
                ('field', models.CharField(blank=True, max_length=255, null=True)),
                ('keywords', models.JSONField(default=list)),
                ('abstract', models.TextField(blank=True, null=True)),
                ('doi', models.CharField(blank=True, max_length=255, null=True)),
                ('bibtex', models.TextField(blank=True, null=True)),
                ('sourceCode', models.URLField(blank=True, max_length=500, null=True)),
                ('is_interesting', models.BooleanField(default=False)),
                ('is_downloaded', models.BooleanField(default=False)),
                ('is_uploaded', models.BooleanField(default=True)),
                ('file', models.FileField(upload_to='papers/')),
                ('file_name', models.CharField(blank=True, max_length=255, null=True)),
                ('file_size', models.IntegerField(blank=True, null=True)),
                ('added_date', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='papers', to='auth.user')),
            ],
        ),
        migrations.CreateModel(
            name='Publication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=500)),
                ('authors', models.TextField()),
                ('journal', models.CharField(max_length=255)),
                ('year', models.IntegerField()),
                ('url', models.URLField(max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='publications', to='auth.user')),
            ],
            options={
                'db_table': 'users_publication',
            },
        ),
    ]
