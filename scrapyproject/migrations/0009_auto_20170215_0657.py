# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scrapyproject', '0008_scrapersdeploy'),
    ]

    operations = [
        migrations.AddField(
            model_name='linkgendeploy',
            name='version',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='scrapersdeploy',
            name='version',
            field=models.IntegerField(default=0),
        ),
    ]
