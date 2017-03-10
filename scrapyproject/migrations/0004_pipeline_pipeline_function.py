# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scrapyproject', '0003_auto_20170209_1025'),
    ]

    operations = [
        migrations.AddField(
            model_name='pipeline',
            name='pipeline_function',
            field=models.TextField(blank=True),
        ),
    ]
