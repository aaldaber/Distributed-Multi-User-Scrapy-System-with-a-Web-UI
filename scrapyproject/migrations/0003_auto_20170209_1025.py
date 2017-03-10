# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scrapyproject', '0002_auto_20170208_1738'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='link_generator',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='project',
            name='scraper_function',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='project',
            name='settings',
            field=models.TextField(blank=True),
        ),
    ]
