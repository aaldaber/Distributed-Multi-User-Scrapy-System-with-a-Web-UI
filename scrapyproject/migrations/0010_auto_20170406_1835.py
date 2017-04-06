# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scrapyproject', '0009_auto_20170215_0657'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='mongopass',
            name='user',
        ),
        migrations.DeleteModel(
            name='MongoPass',
        ),
    ]
