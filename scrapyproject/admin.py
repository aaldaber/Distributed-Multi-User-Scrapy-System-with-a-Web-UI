from django.contrib import admin
from .models import Project, Item, Field, Pipeline

# Register your models here.
admin.site.register(Project)
admin.site.register(Item)
admin.site.register(Field)
admin.site.register(Pipeline)