# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scrapyproject', '0004_pipeline_pipeline_function'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='project',
            name='settings',
        ),
        migrations.AddField(
            model_name='project',
            name='settings_link_generator',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='project',
            name='settings_scraper',
            field=models.TextField(blank=True),
        ),
    ]
