# Generated by Django 2.1.3 on 2018-12-19 16:21

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0030_auto_20181218_1739'),
    ]

    operations = [
        migrations.CreateModel(
            name='InfoGerais',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField()),
                ('value', django.contrib.postgres.fields.jsonb.JSONField()),
            ],
        ),
    ]
