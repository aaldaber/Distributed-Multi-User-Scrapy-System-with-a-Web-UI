# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scrapyproject', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Field',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('field_name', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('item_name', models.CharField(max_length=50)),
                ('project', models.ForeignKey(to='scrapyproject.Project')),
            ],
        ),
        migrations.CreateModel(
            name='Pipeline',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('pipeline_name', models.CharField(max_length=50)),
                ('pipeline_order', models.IntegerField()),
                ('project', models.ForeignKey(to='scrapyproject.Project')),
            ],
        ),
        migrations.AddField(
            model_name='field',
            name='item',
            field=models.ForeignKey(to='scrapyproject.Item'),
        ),
    ]
