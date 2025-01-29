# Generated by Django 4.2.4 on 2025-01-22 12:05

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('app', '0006_certificate_workdetail_workdurationandpersonnel_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='PTWForm',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('location', models.CharField(max_length=100)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('awaiting_supervisor', 'Awaiting Supervisor Approval'), ('awaiting_manager', 'Awaiting Manager Approval'), ('approved', 'Approved'), ('disapproved', 'Disapproved')], default='pending', max_length=20)),
                ('user', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
