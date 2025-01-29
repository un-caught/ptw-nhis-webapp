# Generated by Django 4.2.4 on 2025-01-22 14:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0009_alter_ptwform_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='ptwform',
            name='equipment_tools_materials',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='ptwform',
            name='risk_assessment_done',
            field=models.CharField(choices=[('yes', 'Yes'), ('no', 'No')], max_length=3, null=True),
        ),
        migrations.AddField(
            model_name='ptwform',
            name='work_description',
            field=models.TextField(null=True),
        ),
    ]
