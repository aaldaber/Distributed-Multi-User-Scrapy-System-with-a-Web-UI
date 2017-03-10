# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scrapyproject', '0006_mongopass'),
    ]

    operations = [
        migrations.CreateModel(
            name='LinkgenDeploy',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('success', models.BooleanField()),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(to='scrapyproject.Project')),
            ],
        ),
    ]
