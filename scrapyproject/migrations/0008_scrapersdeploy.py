# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scrapyproject', '0007_linkgendeploy'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScrapersDeploy',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('success', models.TextField(blank=True)),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(to='scrapyproject.Project')),
            ],
        ),
    ]
