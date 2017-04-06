from django.db import models
from django.contrib.auth.models import User


class Project(models.Model):
    project_name = models.CharField(max_length=50)
    user = models.ForeignKey(User)
    link_generator = models.TextField(blank=True)
    scraper_function = models.TextField(blank=True)
    settings_scraper = models.TextField(blank=True)
    settings_link_generator = models.TextField(blank=True)

    def __str__(self):
        return "%s by %s" % (self.project_name, self.user.username)


class Item(models.Model):
    item_name = models.CharField(max_length=50)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)

    def __str__(self):
        return self.item_name


class Field(models.Model):
    field_name = models.CharField(max_length=50)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    def __str__(self):
        return self.field_name


class Pipeline(models.Model):
    pipeline_name = models.CharField(max_length=50)
    pipeline_order = models.IntegerField()
    pipeline_function = models.TextField(blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)

    def __str__(self):
        return self.pipeline_name


class LinkgenDeploy(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    success = models.BooleanField(blank=False)
    date = models.DateTimeField(auto_now_add=True)
    version = models.IntegerField(blank=False, default=0)


class ScrapersDeploy(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    success = models.TextField(blank=True)
    date = models.DateTimeField(auto_now_add=True)
    version = models.IntegerField(blank=False, default=0)


class Dataset(models.Model):
    user = models.ForeignKey(User)
    database = models.CharField(max_length=50)