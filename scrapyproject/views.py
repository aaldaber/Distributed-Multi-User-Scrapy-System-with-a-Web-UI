from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .forms import CreateProject, DeleteProject, ItemName, FieldName, CreatePipeline, LinkGenerator, Scraper, CreateDBPass, Settings
from django.http import HttpResponseRedirect
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from .models import Project, Item, Pipeline, Field, MongoPass, LinkgenDeploy, ScrapersDeploy
from django.forms.util import ErrorList
from itertools import groupby
from django.core.urlresolvers import reverse
import os
import shutil
from string import Template
from .scrapy_packages import settings
from pymongo import MongoClient
import glob
import subprocess
import requests
import json
import datetime
import dateutil.parser
import socket
try:
    # Python 3
    from urllib.parse import urlparse
except ImportError:
    # Python 2
    from urlparse import urlparse

try:
    from urllib.parse import quote
except:
    from urllib import quote


def generate_default_settings():
    settings = """# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'unknown'

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Configure maximum concurrent requests performed by Scrapy (default: 16)
#CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See http://scrapy.readthedocs.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
#DOWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
#CONCURRENT_REQUESTS_PER_DOMAIN = 16
#CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
#}

# Enable and configure the AutoThrottle extension (disabled by default)
# See http://doc.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = 'httpcache'
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'"""
    return settings


@login_required
def main_page(request):
    projects = Project.objects.filter(user=request.user)
    userprojects = []
    for project in projects:
        singleproject = {}
        singleproject['name'] = project.project_name
        userprojects.append(singleproject)
    try:
        dbpass = MongoPass.objects.get(user=request.user)
        dbpassexists = True
    except MongoPass.DoesNotExist:
        dbpassexists = False
    return render(request, template_name="mainpage.html",
                  context={'username': request.user.username, 'projects': userprojects, 'dbpassexists': dbpassexists})


@login_required
def create_new(request):
    if request.method == 'GET':
        form = CreateProject()
        return render(request, 'createproject.html', {'username': request.user.username, 'form': form})
    if request.method == 'POST':
        if 'cancel' in request.POST:
            return HttpResponseRedirect(reverse("mainpage"))
        elif 'submit' in request.POST:
            form = CreateProject(request.POST)
            if form.is_valid():
                allprojects =[]
                userprojects = Project.objects.filter(user=request.user)
                for project in userprojects:
                    allprojects.append(project.project_name)
                if form.cleaned_data['projectname'] in allprojects:
                    errors = form._errors.setdefault("projectname", ErrorList())
                    errors.append('Project named %s already exists. Please choose another name' % form.cleaned_data['projectname'])
                    return render(request, 'createproject.html', {'username': request.user.username, 'form': form})
                else:
                    project = Project()
                    project.project_name = form.cleaned_data['projectname']
                    project.user = request.user
                    project.settings_scraper = generate_default_settings()
                    project.settings_link_generator = generate_default_settings()
                    project.scraper_function = '''def parse(self, response):\n    pass'''
                    project.link_generator = '''start_urls = [""]\ndef parse(self, response):\n    pass'''
                    project.save()

                    # project data will be saved in username_projectname database, so we need to add the user
                    # and the password for that database
                    # if mongodb password hasn't been set by the user, set the password as the name of the user

                    mongodbname = request.user.username + "_" + project.project_name
                    try:
                        dbpass = MongoPass.objects.get(user=request.user)
                        mongopass = dbpass.password
                    except MongoPass.DoesNotExist:
                        mongopass = request.user.username
                    mongouri = "mongodb://" + settings.MONGODB_USER + ":" + quote(settings.MONGODB_PASSWORD) + "@" + settings.MONGODB_URI + "/admin"
                    connection = MongoClient(mongouri)
                    connection[mongodbname].add_user(request.user.username, mongopass,
                                                     roles=[{'role': 'dbOwner', 'db': mongodbname}])
                    connection.close()
                    return HttpResponseRedirect(reverse("manageproject", args=(project.project_name,)))

            else:
                return render(request, 'createproject.html', {'username': request.user.username, 'form': form})
        else:
            return HttpResponseNotFound('Nothing is here.')


@login_required
def manage_project(request, projectname):
    try:
        project = Project.objects.get(user=request.user, project_name=projectname)
    except Project.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    projectdata = {}
    projectdata['settings_scraper'] = project.settings_scraper
    projectdata['settings_link_generator'] = project.settings_link_generator
    projectdata['items'] = []
    projectdata['pipelines'] = []

    if len(project.link_generator) == 0:
        projectdata['link_generator'] = False
    else:
        projectdata['link_generator'] = True

    if len(project.scraper_function) == 0:
        projectdata['scraper_function'] = False
    else:
        projectdata['scraper_function'] = True

    items = Item.objects.filter(project=project)
    pipelines = Pipeline.objects.filter(project=project)

    for item in items:
        projectdata['items'].append(item)

    for pipeline in pipelines:
        projectdata['pipelines'].append(pipeline)

    return render(request, 'manageproject.html',
                  {'username': request.user.username, 'project': project.project_name, 'projectdata': projectdata})


@login_required
def delete_project(request, projectname):
    try:
        project = Project.objects.get(user=request.user, project_name=projectname)
    except Project.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    if request.method == 'GET':
        form = DeleteProject()
        return render(request, 'deleteproject.html', {'username': request.user.username, 'form': form, 'projectname': projectname})
    if request.method == 'POST':
        if 'cancel' in request.POST:
            return HttpResponseRedirect(reverse("mainpage"))
        elif 'submit' in request.POST:
            project.delete()
            return HttpResponseRedirect(reverse("mainpage"))
        else:
            return HttpResponseNotFound('Nothing is here.')


@login_required
def create_item(request, projectname):
    try:
        project = Project.objects.get(user=request.user, project_name=projectname)
    except Project.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    if request.method == 'GET':
        form1 = ItemName()
        form2 = FieldName()
        return render(request, 'additem.html',
                      {'username': request.user.username, 'form1': form1, 'form2': form2, 'project': project.project_name})
    if request.method == 'POST':
        if 'submit' in request.POST:
            form1 = ItemName(request.POST)
            form2 = FieldName(request.POST, extra=request.POST.get('extra_field_count'))
            if form1.is_valid() and form2.is_valid():
                item = Item.objects.filter(project=project, item_name=form1.cleaned_data['itemname'])
                if len(item):
                    errors = form1._errors.setdefault("itemname", ErrorList())
                    errors.append(
                        'Item named %s already exists. Please choose another name' % form1.cleaned_data['itemname'])
                    return render(request, 'additem.html',
                                  {'username': request.user.username, 'form1': form1,
                                   'form2': form2, 'project': project.project_name})
                allfields =[]
                valuetofield = {}
                for field in form2.fields:
                    if form2.cleaned_data[field]:
                        if field != 'extra_field_count':
                            valuetofield[form2.cleaned_data[field]] = field
                            allfields.append(form2.cleaned_data[field])
                duplicates = [list(j) for i, j in groupby(allfields)]
                for duplicate in duplicates:
                    if len(duplicate) > 1:
                            errors = form2._errors.setdefault(valuetofield[duplicate[0]], ErrorList())
                            errors.append('Duplicate fields are not allowed.')
                            return render(request, 'additem.html',
                                          {'username': request.user.username, 'form1': form1,
                                           'form2': form2, 'project': project.project_name})

                item = Item()
                item.item_name = form1.cleaned_data['itemname']
                item.project = project
                item.save()
                for field in allfields:
                    onefield = Field()
                    onefield.item = item
                    onefield.field_name = field
                    onefield.save()
                return HttpResponseRedirect(reverse("listitems", args=(project.project_name,)))
            else:
                return render(request, 'additem.html',
                              {'username': request.user.username, 'form1': form1,
                               'form2': form2, 'project': project.project_name})
        elif 'cancel' in request.POST:
            return HttpResponseRedirect(reverse("listitems", args=(project.project_name,)))
        else:
            form1 = ItemName(request.POST)
            form2 = FieldName(request.POST, extra=request.POST.get('extra_field_count'))
            return render(request, 'additem.html',
                          {'username': request.user.username, 'form1': form1,
                           'form2': form2, 'project': project.project_name})


@login_required
def itemslist(request, projectname):
    try:
        project = Project.objects.get(user=request.user, project_name=projectname)
    except Project.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    itemtracker = 0

    items = Item.objects.filter(project=project)
    itemdata = []
    for item in items:
        itemdata.append([])
        itemdata[itemtracker].append(item.item_name)
        fields = Field.objects.filter(item=item)
        if fields:
            itemdata[itemtracker].append([])
        for field in fields:
            itemdata[itemtracker][1].append(field.field_name)
        itemtracker += 1
    return render(request, 'itemslist.html',
                  {'username': request.user.username, 'project': project.project_name, 'items': itemdata})


@login_required
def deleteitem(request, projectname, itemname):
    try:
        project = Project.objects.get(user=request.user, project_name=projectname)
    except Project.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    try:
        item = Item.objects.get(project=project, item_name=itemname)
    except Item.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    if request.method == 'GET':
        # using the form that was used for deleting the project
        form = DeleteProject()
        return render(request, 'deleteitem.html',
                      {'username': request.user.username, 'form': form, 'projectname': projectname, 'itemname': itemname})
    elif request.method == 'POST':
        if 'cancel' in request.POST:
            return HttpResponseRedirect(reverse("listitems", args=(projectname,)))
        elif 'submit' in request.POST:
            item.delete()
            return HttpResponseRedirect(reverse("listitems", args=(projectname,)))


@login_required
def edititem(request, projectname, itemname):
    try:
        project = Project.objects.get(user=request.user, project_name=projectname)
    except Project.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    try:
        item = Item.objects.get(project=project, item_name=itemname)
    except Item.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    if request.method == 'GET':

        fields = Field.objects.filter(item=item)
        fieldcounter = 0
        fieldlist = []
        fielddata = {}

        for field in fields:
            fieldlist.append(field.field_name)
            fieldcounter += 1

        if fieldcounter == 1:
            fielddata['fieldname'] = fieldlist[0]
            fielddata['extra_field_count'] = 0
        elif fieldcounter > 1:
            fielddata['fieldname'] = fieldlist[0]
            fielddata['extra_field_count'] = fieldcounter - 1
            for i in range(1,fieldcounter):
                fielddata['field_%d' % (i+1)] = fieldlist[i]

        form1 = ItemName({'itemname': itemname})
        form2 = FieldName(initial=fielddata, extra=fielddata['extra_field_count'])

        return render(request, 'edititem.html',
                      {'username': request.user.username, 'form1': form1, 'form2': form2, 'project': project.project_name})

    elif request.method == 'POST':
        if 'submit' in request.POST:
            form1 = ItemName(request.POST)
            form2 = FieldName(request.POST, extra=request.POST.get('extra_field_count'))
            if form1.is_valid() and form2.is_valid():
                newitemname = Item.objects.filter(project=project, item_name=form1.cleaned_data['itemname'])
                if len(newitemname):
                    for oneitem in newitemname:
                        if oneitem.item_name != item.item_name:
                            errors = form1._errors.setdefault('itemname', ErrorList())
                            errors.append('Item named %s already exists. Please choose another name' % form1.cleaned_data['itemname'])
                            return render(request, 'edititem.html',
                                          {'username': request.user.username, 'form1': form1,
                                           'form2': form2, 'project': project.project_name})


                allfields = []
                valuetofield = {}
                for field in form2.fields:
                    if form2.cleaned_data[field]:
                        if field != 'extra_field_count':
                            valuetofield[form2.cleaned_data[field]] = field
                            allfields.append(form2.cleaned_data[field])
                duplicates = [list(j) for i, j in groupby(allfields)]
                for duplicate in duplicates:
                    if len(duplicate) > 1:
                        errors = form2._errors.setdefault(valuetofield[duplicate[0]], ErrorList())
                        errors.append('Duplicate fields are not allowed.')
                        return render(request, 'edititem.html',
                                      {'username': request.user.username, 'form1': form1,
                                       'form2': form2, 'project': project.project_name})

                deletefield = Field.objects.filter(item=item)
                for field in deletefield:
                    field.delete()

                item.item_name = form1.cleaned_data['itemname']
                item.save()
                for field in allfields:
                    onefield = Field()
                    onefield.item = item
                    onefield.field_name = field
                    onefield.save()
                return HttpResponseRedirect(reverse("listitems", args=(project.project_name,)))
        elif 'cancel' in request.POST:
            return HttpResponseRedirect(reverse("listitems", args=(project.project_name,)))
        else:
            form1 = ItemName(request.POST)
            form2 = FieldName(request.POST, extra=request.POST.get('extra_field_count'))
            return render(request, 'edititem.html',
                          {'username': request.user.username, 'form1': form1,
                           'form2': form2, 'project': project.project_name})


@login_required
def addpipeline(request, projectname):
    try:
        project = Project.objects.get(user=request.user, project_name=projectname)
    except Project.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    defined_items = {}
    items = Item.objects.filter(project=project)
    for item in items:
        defined_items[item.item_name] = []
        fields = Field.objects.filter(item=item)
        for field in fields:
            defined_items[item.item_name].append(field.field_name)

    if request.method == 'GET':
        initial_code = '''def process_item(self, item, spider):\n    return item
'''
        form = CreatePipeline(initial={'pipelinefunction': initial_code})
        return render(request, "addpipeline.html",
                      {'username': request.user.username, 'form': form, 'project': project.project_name, 'items': defined_items})
    elif request.method == 'POST':
        if 'cancel' in request.POST:
            return HttpResponseRedirect(reverse("listpipelines", args=(project.project_name,)))
        if 'submit' in request.POST:
            form = CreatePipeline(request.POST)
            if form.is_valid():
                names = []
                orders =[]
                pipelines = Pipeline.objects.filter(project=project)
                for pipeline in pipelines:
                    names.append(pipeline.pipeline_name)
                    orders.append(pipeline.pipeline_order)
                if form.cleaned_data['pipelinename'] in names:
                    errors = form._errors.setdefault('pipelinename', ErrorList())
                    errors.append(
                        'Pipeline named %s already exists. Please choose another name' % form.cleaned_data['pipelinename'])
                    return render(request, "addpipeline.html",
                                  {'username': request.user.username, 'form': form, 'project': project.project_name, 'items': defined_items})
                if int(form.cleaned_data['pipelineorder']) in orders:
                    errors = form._errors.setdefault('pipelineorder', ErrorList())
                    errors.append(
                        'Pipeline order %s already exists for another pipeline function. Enter a different order' % form.cleaned_data['pipelineorder'])
                    return render(request, "addpipeline.html",
                                  {'username': request.user.username, 'form': form, 'project': project.project_name, 'items': defined_items})
                pipeline = Pipeline()
                pipeline.pipeline_name = form.cleaned_data['pipelinename']
                pipeline.pipeline_order = form.cleaned_data['pipelineorder']
                pipeline.pipeline_function = form.cleaned_data['pipelinefunction']
                pipeline.project = project
                pipeline.save()
                return HttpResponseRedirect(reverse("listpipelines", args=(project.project_name,)))
            else:
                return render(request, "addpipeline.html",
                              {'username': request.user.username, 'form': form, 'project': project.project_name, 'items': defined_items})


@login_required
def pipelinelist(request, projectname):
    try:
        project = Project.objects.get(user=request.user, project_name=projectname)
    except Project.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    itemtracker = 0

    pipelines = Pipeline.objects.filter(project=project)
    pipelinedata = []
    for pipeline in pipelines:
        pipelinedata.append([])
        pipelinedata[itemtracker].append(pipeline.pipeline_name)
        pipelinedata[itemtracker].append(pipeline.pipeline_order)
        itemtracker += 1
    return render(request, 'pipelinelist.html', {'username': request.user.username, 'project': project.project_name, 'items': pipelinedata})


@login_required
def editpipeline(request, projectname, pipelinename):
    try:
        project = Project.objects.get(user=request.user, project_name=projectname)
    except Project.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    try:
        pipeline = Pipeline.objects.get(project=project, pipeline_name=pipelinename)
    except Pipeline.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    defined_items = {}
    items = Item.objects.filter(project=project)
    for item in items:
        defined_items[item.item_name] = []
        fields = Field.objects.filter(item=item)
        for field in fields:
            defined_items[item.item_name].append(field.field_name)

    if request.method == 'GET':
        form = CreatePipeline(initial={'pipelinename': pipeline.pipeline_name,
                                       'pipelineorder': pipeline.pipeline_order,
                                       'pipelinefunction': pipeline.pipeline_function})
        return render(request, "editpipeline.html",
                      {'username': request.user.username, 'form': form, 'project': project.project_name, 'items': defined_items})
    elif request.method == 'POST':
        if 'cancel' in request.POST:
            return HttpResponseRedirect(reverse("listpipelines", args=(project.project_name,)))
        if 'submit' in request.POST:
            form = CreatePipeline(request.POST)
            if form.is_valid():
                newpipelinename = Pipeline.objects.filter(project=project, pipeline_name=form.cleaned_data['pipelinename'])
                if len(newpipelinename):
                    for oneitem in newpipelinename:
                        if oneitem.pipeline_name != pipeline.pipeline_name:
                            errors = form._errors.setdefault('pipelinename', ErrorList())
                            errors.append(
                                'Pipeline named %s already exists. Please choose another name' % form.cleaned_data[
                                    'pipelinename'])
                            return render(request, 'editpipeline.html',
                                          {'username': request.user.username, 'form': form, 'project': project.project_name, 'items': defined_items})
                newpipelineorder = Pipeline.objects.filter(project=project,
                                                           pipeline_order=form.cleaned_data['pipelineorder'])
                if len(newpipelineorder):
                    for oneitem in newpipelineorder:
                        if oneitem.pipeline_order != pipeline.pipeline_order:
                            errors = form._errors.setdefault('pipelineorder', ErrorList())
                            errors.append(
                                'Pipeline order %s already exists for another pipeline function. Enter a different order' % form.cleaned_data['pipelineorder'])
                            return render(request, 'editpipeline.html',
                                          {'username': request.user.username, 'form': form, 'project': project.project_name, 'items': defined_items})
                pipeline.pipeline_name = form.cleaned_data['pipelinename']
                pipeline.pipeline_order = form.cleaned_data['pipelineorder']
                pipeline.pipeline_function = form.cleaned_data['pipelinefunction']
                pipeline.save()
                return HttpResponseRedirect(reverse("listpipelines", args=(project.project_name,)))
            else:
                return render(request, "editpipeline.html",
                              {'username': request.user.username, 'form': form, 'project': project.project_name, 'items': defined_items})


@login_required
def deletepipeline(request, projectname, pipelinename):
    try:
        project = Project.objects.get(user=request.user, project_name=projectname)
    except Project.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    try:
        pipeline = Pipeline.objects.get(project=project, pipeline_name=pipelinename)
    except Pipeline.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    if request.method == 'GET':
        form = DeleteProject()
        return render(request, 'deletepipeline.html',
                      {'username': request.user.username,
                       'form': form, 'projectname': project.project_name, 'pipelinename': pipeline.pipeline_name})
    elif request.method == 'POST':
        if 'cancel' in request.POST:
            return HttpResponseRedirect(reverse("listpipelines", args=(project.project_name,)))
        elif 'submit' in request.POST:
            pipeline.delete()
            return HttpResponseRedirect(reverse("listpipelines", args=(project.project_name,)))


@login_required
def linkgenerator(request, projectname):
    try:
        project = Project.objects.get(user=request.user, project_name=projectname)
    except Project.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    spiderclassnamelabel = "class " + request.user.username.title() + project.project_name.title() + "Spider:"

    if request.method == 'GET':
        form = LinkGenerator(initial={'function': project.link_generator})
        form.fields['function'].label = spiderclassnamelabel
        return render(request,
                      'addlinkgenerator.html', {'username': request.user.username,
                                                'form': form, 'project': project.project_name})
    elif request.method == 'POST':
        if 'cancel' in request.POST:
            return HttpResponseRedirect(reverse("manageproject", args=(project.project_name,)))
        if 'submit' in request.POST:
            form = LinkGenerator(request.POST)
            form.fields['function'].label = spiderclassnamelabel
            if form.is_valid():
                project.link_generator = form.cleaned_data['function']
                project.save()
                return HttpResponseRedirect(reverse("manageproject", args=(project.project_name,)))
            else:
                return render(request, 'addlinkgenerator.html',
                              {'username': request.user.username, 'form': form, 'project': project.project_name})


@login_required
def scraper(request, projectname):
    try:
        project = Project.objects.get(user=request.user, project_name=projectname)
    except Project.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    spiderclassnamelabel = "class " + request.user.username.title() + project.project_name.title() + "Spider:"

    if request.method == 'GET':
        form = Scraper(initial={'function': project.scraper_function})
        form.fields['function'].label = spiderclassnamelabel
        return render(request, 'addscraper.html', {'username': request.user.username, 'form': form, 'project': project.project_name})
    elif request.method == 'POST':
        if 'cancel' in request.POST:
            return HttpResponseRedirect(reverse("manageproject", args=(projectname,)))
        if 'submit' in request.POST:
            form = Scraper(request.POST)
            form.fields['function'].label = spiderclassnamelabel
            if form.is_valid():
                project.scraper_function = form.cleaned_data['function']
                project.save()
                return HttpResponseRedirect(reverse("manageproject", args=(projectname,)))
            else:
                return render(request, 'addscraper.html',
                              {'username': request.user.username, 'form': form, 'project': project.project_name})


def create_folder_tree(tree):
    d = os.path.abspath(tree)
    if not os.path.exists(d):
        os.makedirs(d)
    else:
        shutil.rmtree(d)
        os.makedirs(d)


@login_required
def create_db_pass(request):
    if request.method == 'GET':
        try:
            dbpass = MongoPass.objects.get(user=request.user)
            password = dbpass.password
        except MongoPass.DoesNotExist:
            password = ''
        form = CreateDBPass(initial={'password': password})
        return render(request, 'createdbpass.html', {'username': request.user.username, 'form': form})
    elif request.method == 'POST':
        if 'cancel' in request.POST:
            return HttpResponseRedirect(reverse("mainpage"))
        elif 'submit' in request.POST:
            try:
                dbpass = MongoPass.objects.get(user=request.user)
            except MongoPass.DoesNotExist:
                dbpass = MongoPass()
                dbpass.user = request.user
            form = CreateDBPass(request.POST)
            if form.is_valid():
                dbpass.password = form.cleaned_data['password']
                dbpass.save()
                projects = Project.objects.filter(user=request.user)
                mongouri = "mongodb://" + settings.MONGODB_USER + ":" + quote(settings.MONGODB_PASSWORD) + "@" + settings.MONGODB_URI + "/admin"
                connection = MongoClient(mongouri)
                for project in projects:
                    mongodbname = request.user.username + "_" + project.project_name
                    connection[mongodbname].add_user(request.user.username, dbpass.password,
                                                 roles=[{'role': 'dbOwner', 'db': mongodbname}])
                connection.close()
                return HttpResponseRedirect(reverse("mainpage"))
            else:
                return render(request, 'createdbpass.html', {'username': request.user.username, 'form': form})


@login_required
def deploy(request, projectname):
    try:
        project = Project.objects.get(user=request.user, project_name=projectname)
    except Project.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    projectitems = Item.objects.filter(project=project)
    projectlinkgenfunction = project.link_generator
    projectscraperfunction = project.scraper_function

    if not projectitems or not projectlinkgenfunction or not projectscraperfunction:
        return HttpResponseNotFound('Not all required project parts are present for deployment. Please review your project and deploy again.')

    basepath = os.path.dirname(os.path.abspath(__file__))

    #we are giving a project and its folders a unique name on disk, so that no name conflicts occur when deploying the projects
    projectnameonfile = request.user.username + '_' + projectname

    #removing the project folder, if exists
    create_folder_tree(basepath + "/projects/%s/%s" % (request.user.username, projectname))

    #Create project folder structure
    folder1 = basepath + "/projects/%s/%s/%s/%s/%s" % (request.user.username, projectname, 'scraper', projectnameonfile, 'spiders')
    folder2 = basepath + "/projects/%s/%s/%s/%s/%s" % (request.user.username, projectname, 'linkgenerator', projectnameonfile, 'spiders')

    #Link generator folders
    linkgenouterfolder = basepath + "/projects/%s/%s/%s" % (request.user.username, projectname, 'linkgenerator')
    linkgenprojectfolder = basepath + "/projects/%s/%s/%s/%s" % (request.user.username, projectname, 'linkgenerator', projectnameonfile)
    linkgenspiderfolder = basepath + "/projects/%s/%s/%s/%s/%s" % (request.user.username, projectname, 'linkgenerator', projectnameonfile, 'spiders')

    #Scraper folders
    scraperouterfolder = basepath + "/projects/%s/%s/%s" % (request.user.username, projectname, 'scraper')
    scraperprojectfolder = basepath + "/projects/%s/%s/%s/%s" % (request.user.username, projectname, 'scraper', projectnameonfile)
    scraperspiderfolder = basepath + "/projects/%s/%s/%s/%s/%s" % (request.user.username, projectname, 'scraper', projectnameonfile, 'spiders')

    #Link generator files
    linkgencfgfile = linkgenouterfolder + "/scrapy.cfg"
    linkgensettingsfile = linkgenprojectfolder + "/settings.py"
    linkgenspiderfile = linkgenspiderfolder + "/%s_%s.py" % (request.user.username, projectname)

    #Scraper files
    scrapercfgfile = scraperouterfolder + "/scrapy.cfg"
    scrapersettingsfile = scraperprojectfolder + "/settings.py"
    scraperspiderfile = scraperspiderfolder + "/%s_%s.py" % (request.user.username, projectname)
    scraperitemsfile = scraperprojectfolder + "/items.py"
    scraperpipelinefile = scraperprojectfolder + "/pipelines.py"

    #Create needed folders
    create_folder_tree(folder1)
    create_folder_tree(folder2)

    #putting __init.py__ files in linkgenerator
    shutil.copy(basepath + '/scrapy_packages/__init__.py', linkgenprojectfolder)
    shutil.copy(basepath + '/scrapy_packages/__init__.py', linkgenspiderfolder)

    #putting rabbitmq folder alongside project
    shutil.copytree(basepath + '/scrapy_packages/rabbitmq', linkgenprojectfolder + '/rabbitmq')

    #creating a cfg for link generator

    scrapycfg = '''[settings]\n
default = %s.settings

[deploy:linkgenerator]
url = %s

project = %s
''' % (projectnameonfile, settings.LINK_GENERATOR, projectnameonfile)

    with open(linkgencfgfile, 'w') as f:
        f.write(scrapycfg)

    #creating a settings.py file for link generator
    with open(basepath + '/scrapy_templates/settings.py.tmpl', 'r') as f:
        settingspy = Template(f.read()).substitute(project_name=projectnameonfile)

    settingspy += '\n' + project.settings_link_generator

    settingspy += '\nSCHEDULER = "%s"' % (projectnameonfile + settings.SCHEDULER)
    settingspy += '\nSCHEDULER_PERSIST = %s' % settings.SCHEDULER_PERSIST
    settingspy += '\nRABBITMQ_HOST = "%s"' % settings.RABBITMQ_HOST
    settingspy += '\nRABBITMQ_PORT = %s' % settings.RABBITMQ_PORT
    settingspy += '\nRABBITMQ_USERNAME = "%s"' % settings.RABBITMQ_USERNAME
    settingspy += '\nRABBITMQ_PASSWORD = "%s"' % settings.RABBITMQ_PASSWORD

    with open(linkgensettingsfile, 'w') as f:
        f.write(settingspy)

    #creating a spider file for link generator
    with open(basepath + '/scrapy_templates/linkgenspider.py.tmpl', 'r') as f:
        spider = Template(f.read()).substitute(spider_name=request.user.username + "_" + projectname, SpiderClassName=request.user.username.title() + projectname.title() + "Spider")
    spider += '\n'
    linkgenlines = project.link_generator.splitlines()
    for lines in linkgenlines:
        spider += '    ' + lines + '\n'
    with open(linkgenspiderfile, 'w') as f:
        f.write(spider)

    # putting __init.py__ files in scraper
    shutil.copy(basepath + '/scrapy_packages/__init__.py', scraperprojectfolder)
    shutil.copy(basepath + '/scrapy_packages/__init__.py', scraperspiderfolder)

    # putting rabbitmq folder alongside project
    shutil.copytree(basepath + '/scrapy_packages/rabbitmq', scraperprojectfolder + '/rabbitmq')
    # putting mongodb folder alongside project
    shutil.copytree(basepath + '/scrapy_packages/mongodb', scraperprojectfolder + '/mongodb')
    # creating a cfg for scraper

    scrapycfg = '''[settings]\n
default = %s.settings\n\n''' % (projectnameonfile)

    workercount = 1
    for worker in settings.SCRAPERS:
        scrapycfg += '[deploy:worker%d]\nurl = %s\n' % (workercount, worker)
        workercount += 1

    scrapycfg += '\nproject = %s' % (projectnameonfile)

    with open(scrapercfgfile, 'w') as f:
        f.write(scrapycfg)

    # creating a spider file for scraper
    with open(basepath + '/scrapy_templates/scraperspider.py.tmpl', 'r') as f:
        spider = Template(f.read()).substitute(spider_name=request.user.username + "_" + projectname,
                                               SpiderClassName=request.user.username.title() + projectname.title() + "Spider",
                                               project_name=projectnameonfile)
    spider += '\n'
    scraperlines = project.scraper_function.splitlines()
    for lines in scraperlines:
        spider += '    ' + lines + '\n'
    with open(scraperspiderfile, 'w') as f:
        f.write(spider)

    #creating items file for scraper
    items = Item.objects.filter(project=project)
    itemsfile = 'import scrapy\n'
    fieldtemplate = '    %s = scrapy.Field()\n'
    for item in items:
        itemsfile += 'class %s(scrapy.Item):\n' % item.item_name
        fields = Field.objects.filter(item=item)
        for field in fields:
            itemsfile += fieldtemplate % field.field_name
        itemsfile += fieldtemplate % 'ack_signal'
        itemsfile += '\n'

    with open(scraperitemsfile, 'w') as f:
        f.write(itemsfile)

    #creating pipelines file for scraper
    pipelinesfile = ''
    pipelinedict = {}
    pipelines = Pipeline.objects.filter(project=project)
    for pipeline in pipelines:
        pipelinedict[pipeline.pipeline_name] = pipeline.pipeline_order
        pipelinesfile += 'class %s(object):\n' % pipeline.pipeline_name
        pipfunctionlines = pipeline.pipeline_function.splitlines()
        for lines in pipfunctionlines:
            pipelinesfile += '    ' + lines + '\n'

    with open(scraperpipelinefile, 'w') as f:
        f.write(pipelinesfile)

    # creating a settings.py file for scraper

    with open(basepath + '/scrapy_templates/settings.py.tmpl', 'r') as f:
        settingspy = Template(f.read()).substitute(project_name=projectnameonfile)

    settingspy += '\n' + project.settings_scraper

    settingspy += '\nSCHEDULER = "%s"' % (projectnameonfile + settings.SCHEDULER)
    settingspy += '\nSCHEDULER_PERSIST = %s' % settings.SCHEDULER_PERSIST
    settingspy += '\nRABBITMQ_HOST = "%s"' % settings.RABBITMQ_HOST
    settingspy += '\nRABBITMQ_PORT = %s' % settings.RABBITMQ_PORT
    settingspy += '\nRABBITMQ_USERNAME = "%s"' % settings.RABBITMQ_USERNAME
    settingspy += '\nRABBITMQ_PASSWORD = "%s"' % settings.RABBITMQ_PASSWORD
    settingspy += '\nMONGODB_URI = "%s"' % settings.MONGODB_URI
    settingspy += '\nMONGODB_SHARDED = %s' % settings.MONGODB_SHARDED
    settingspy += '\nMONGODB_BUFFER_DATA = %s' % settings.MONGODB_BUFFER_DATA
    settingspy += '\nMONGODB_USER = "%s"' % settings.MONGODB_USER
    settingspy += '\nMONGODB_PASSWORD = "%s"' % settings.MONGODB_PASSWORD
    settingspy += '\nITEM_PIPELINES = { "%s.mongodb.scrapy_mongodb.MongoDBPipeline": 999, \n' % projectnameonfile
    for key in pipelinedict:
        settingspy += '"%s.pipelines.%s": %s, \n' % (projectnameonfile, key, pipelinedict[key])
    settingspy += '}'

    with open(scrapersettingsfile, 'w') as f:
        f.write(settingspy)

    #putting setup.py files in appropriate folders
    with open(basepath + '/scrapy_templates/setup.py', 'r') as f:
        setuppy = Template(f.read()).substitute(projectname=projectnameonfile)

    with open(linkgenouterfolder + '/setup.py', 'w') as f:
        f.write(setuppy)

    with open(scraperouterfolder + '/setup.py', 'w') as f:
        f.write(setuppy)

    class cd:
        """Context manager for changing the current working directory"""

        def __init__(self, newPath):
            self.newPath = os.path.expanduser(newPath)

        def __enter__(self):
            self.savedPath = os.getcwd()
            os.chdir(self.newPath)

        def __exit__(self, etype, value, traceback):
            os.chdir(self.savedPath)

    with cd(linkgenouterfolder):
        os.system("python setup.py bdist_egg")

    with cd(scraperouterfolder):
        os.system("python setup.py bdist_egg")

    linkgeneggfile = glob.glob(linkgenouterfolder + "/dist/*.egg")
    scrapereggfile = glob.glob(scraperouterfolder + "/dist/*.egg")

    linkgenlastdeploy = LinkgenDeploy.objects.filter(project=project).order_by('-version')[:1]
    if linkgenlastdeploy:
        linkgenlastdeploy = linkgenlastdeploy[0].version
    else:
        linkgenlastdeploy = 0

    scraperslastdeploy = ScrapersDeploy.objects.filter(project=project).order_by('-version')[:1]
    if scraperslastdeploy:
        scraperslastdeploy = scraperslastdeploy[0].version
    else:
        scraperslastdeploy = 0

    try:
        with open(linkgeneggfile[0], 'rb') as f:
            files = {'egg': f}
            payload = {'project': '%s' % (projectnameonfile), 'version': (linkgenlastdeploy + 1)}
            r = requests.post('%s/addversion.json' % settings.LINK_GENERATOR, data=payload, files=files, timeout=(3, None))
            result = r.json()
            deploylinkgen = LinkgenDeploy()
            deploylinkgen.project = project
            deploylinkgen.version = linkgenlastdeploy + 1
            if result["status"] != "ok":
                deploylinkgen.success = False

            else:
                deploylinkgen.success = True
            deploylinkgen.save()
    except:
        deploylinkgen = LinkgenDeploy()
        deploylinkgen.project = project
        deploylinkgen.version = linkgenlastdeploy + 1
        deploylinkgen.success = False
        deploylinkgen.save()


    with open(scrapereggfile[0], 'rb') as f:
        eggfile = f.read()


    files = {'egg' : eggfile}
    payload = {'project': '%s' % (projectnameonfile), 'version': (scraperslastdeploy + 1)}
    deployscraper = ScrapersDeploy()
    deployscraper.project = project
    deployscraper.version = scraperslastdeploy + 1
    deployedscraperslist = []
    scrapercounter = 1
    for onescraper in settings.SCRAPERS:
        try:
            r = requests.post('%s/addversion.json' % onescraper, data=payload, files=files, timeout=(3, None))
            result = r.json()
            if result['status'] == 'ok':
                deployedscraperslist.append("worker%s" %scrapercounter)
        except:
            pass
        scrapercounter += 1
    deployscraper.success = json.dumps(deployedscraperslist)
    deployscraper.save()

    return HttpResponseRedirect(reverse('deploystatus', args=(projectname,)))


@login_required
def deployment_status(request, projectname):
    try:
        project = Project.objects.get(user=request.user, project_name=projectname)
    except Project.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    workers = []

    counter = 1

    workers.append({'name': 'linkgenerator', 'status': 'Loading...', 'version': 'Loading...'})
    for worker in settings.SCRAPERS:
        workers.append({'name': 'worker%s' % counter, 'status': 'Loading...', 'version': 'Loading...'})
        counter += 1
    return render(request, "deployment_status.html", {'project': projectname, 'username': request.user.username, 'workers': workers})


@login_required
def get_project_status_from_all_workers(request, projectname):
    uniqueprojectname = request.user.username + '_' + projectname
    try:
        project = Project.objects.get(user=request.user, project_name=projectname)
    except Project.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    counter = 1

    if request.method == 'POST':
        allworkers = []

        workerstatus = {}
        workerstatus['name'] = 'linkgenerator'
        try:
            r = requests.get('%s/listprojects.json' % settings.LINK_GENERATOR,timeout=(3, None))
            result = r.json()
            if uniqueprojectname in result['projects']:
                workerstatus['status'] = 'ready'
                try:
                    q = requests.get('%s/listversions.json' % settings.LINK_GENERATOR, params={'project': uniqueprojectname},timeout=(3, None))
                    qresult = q.json()
                    version = qresult['versions'][-1]
                    workerstatus['version'] = version
                except:
                    workerstatus['version'] = 'unknown'
                try:
                    s = requests.get('%s/listjobs.json' % settings.LINK_GENERATOR, params={'project': uniqueprojectname}, timeout=(3, None))
                    sresult = s.json()
                    if sresult['finished']:
                        workerstatus['status'] = 'finished'
                    if sresult['pending']:
                        workerstatus['status'] = 'pending'
                    if sresult['running']:
                        workerstatus['status'] = 'running'
                except:
                    workerstatus['status'] = 'unknown'
            else:
                workerstatus['status'] = 'not delpoyed'
                workerstatus['version'] = 'unknown'

        except:
            workerstatus['status'] = 'unreachable'
            workerstatus['version'] = 'unknown'

        allworkers.append(workerstatus)

        for worker in settings.SCRAPERS:
            workerstatus = {}
            workerstatus['name'] = 'worker%s' % counter
            try:
                r = requests.get('%s/listprojects.json' % worker, timeout=(3, None))
                result = r.json()
                if uniqueprojectname in result['projects']:
                    workerstatus['status'] = 'ready'
                    try:
                        q = requests.get('%s/listversions.json' % worker,
                                         params={'project': uniqueprojectname}, timeout=(3, None))
                        qresult = q.json()
                        version = qresult['versions'][-1]
                        workerstatus['version'] = version
                    except:
                        workerstatus['version'] = 'unknown'
                    try:
                        s = requests.get('%s/listjobs.json' % worker,
                                         params={'project': uniqueprojectname}, timeout=(3, None))
                        sresult = s.json()
                        if sresult['finished']:
                            workerstatus['status'] = 'finished'
                        if sresult['pending']:
                            workerstatus['status'] = 'pending'
                        if sresult['running']:
                            workerstatus['status'] = 'running'
                    except:
                        workerstatus['status'] = 'unknown'
                else:
                    workerstatus['status'] = 'not delpoyed'
                    workerstatus['version'] = 'unknown'

            except:
                workerstatus['status'] = 'unreachable'
                workerstatus['version'] = 'unknown'

            allworkers.append(workerstatus)
            counter += 1

        return JsonResponse(allworkers, safe=False)


@login_required
def start_project(request, projectname, worker):
    uniqueprojectname = request.user.username + '_' + projectname
    try:
        project = Project.objects.get(user=request.user, project_name=projectname)
    except Project.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    if request.method == 'POST':
        if 'linkgenerator' in worker:
            linkgenaddress = settings.LINK_GENERATOR
            try:
                r = requests.post('%s/schedule.json' % linkgenaddress, data={'project': uniqueprojectname, 'spider': uniqueprojectname}, timeout=(3, None))
            except:
                pass
        elif 'worker' in worker:
            workernumber = ''.join(x for x in worker if x.isdigit())
            workernumber = int(workernumber)
            workeraddress = settings.SCRAPERS[workernumber - 1]
            try:
                r = requests.post('%s/schedule.json' % workeraddress, data={'project': uniqueprojectname, 'spider': uniqueprojectname}, timeout=(3, None))
            except:
                pass

        return HttpResponse('sent start signal')


@login_required
def stop_project(request, projectname, worker):
    uniqueprojectname = request.user.username + '_' + projectname
    try:
        project = Project.objects.get(user=request.user, project_name=projectname)
    except Project.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    if request.method == 'POST':
        if 'linkgenerator' in worker:
            linkgenaddress = settings.LINK_GENERATOR
            try:
                r = requests.get('%s/listjobs.json' % linkgenaddress,
                                 params={'project': uniqueprojectname}, timeout=(3, None))
                result = r.json()
                jobid = result['running'][0]['id']
                s = requests.post('%s/cancel.json' % linkgenaddress, params={'project': uniqueprojectname, 'job': jobid}, timeout=(3, None))
            except:
                pass
        elif 'worker' in worker:
            workernumber = ''.join(x for x in worker if x.isdigit())
            workernumber = int(workernumber)
            workeraddress = settings.SCRAPERS[workernumber - 1]
            try:
                r = requests.get('%s/listjobs.json' % workeraddress,
                                 params={'project': uniqueprojectname}, timeout=(3, None))
                result = r.json()
                jobid = result['running'][0]['id']
                s = requests.post('%s/cancel.json' % workeraddress, params={'project': uniqueprojectname, 'job': jobid}, timeout=(3, None))
            except:
                pass
        return HttpResponse('sent stop signal')


@login_required
def see_log_file(request, projectname, worker):
    uniqueprojectname = request.user.username + '_' + projectname
    try:
        project = Project.objects.get(user=request.user, project_name=projectname)
    except Project.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    if request.method == 'GET':
        if 'linkgenerator' in worker:
            linkgenaddress = settings.LINK_GENERATOR
            try:
                r = requests.get('%s/listjobs.json' % linkgenaddress,
                                 params={'project': uniqueprojectname}, timeout=(3, None))
                result = r.json()
                jobid = result['finished'][-1]['id']
                log = requests.get('%s/logs/%s/%s/%s.log' % (linkgenaddress, uniqueprojectname, uniqueprojectname, jobid))
            except:
                return HttpResponse('could not retrieve the log file')
        elif 'worker' in worker:
            workernumber = ''.join(x for x in worker if x.isdigit())
            workernumber = int(workernumber)
            workeraddress = settings.SCRAPERS[workernumber - 1]
            try:
                r = requests.get('%s/listjobs.json' % workeraddress,
                                 params={'project': uniqueprojectname}, timeout=(3, None))
                result = r.json()
                jobid = result['finished'][-1]['id']
                log = requests.get('%s/logs/%s/%s/%s.log' % (workeraddress, uniqueprojectname, uniqueprojectname, jobid))
            except:
                return HttpResponse('could not retrieve the log file')

        return HttpResponse(log.text, content_type='text/plain')


@login_required
def gather_status_for_all_projects(request):

    projectsdict = {}
    workers = []

    for worker in settings.SCRAPERS:
        workers.append(worker)
    workers.append(settings.LINK_GENERATOR)

    projects = Project.objects.filter(user=request.user)

    for project in projects:
        projectsdict[project.project_name] = []
        project_items = Item.objects.filter(project=project)
        for item in project_items:
            projectsdict[project.project_name].append(item.item_name)

    if request.method == 'POST':

        if projectsdict:
            allprojectdata = {}

            for key in projectsdict:
                workerstatus = {}

                earliest_start_time = None
                earliest_finish_time = None
                latest_start_time = None
                latest_finish_time = None

                uniqueprojectname = request.user.username + '_' + key

                for worker in workers:
                    try:
                        log = requests.get('%s/logs/%s/%s/stats.log' % (worker, uniqueprojectname, uniqueprojectname), timeout=(3, None))

                        if log.status_code == 200:

                            result = json.loads(log.text.replace("'", '"'))

                            if result.get('project_stopped', 0):
                                workerstatus['finished'] = workerstatus.get('finished', 0) + 1
                            else:
                                workerstatus['running'] = workerstatus.get('running', 0) + 1
                            if result.get('log_count/ERROR', 0):
                                workerstatus['errors'] = workerstatus.get('errors', 0) + result.get('log_count/ERROR', 0)

                            for item in projectsdict[key]:
                                if result.get(item, 0):
                                    workerstatus['item-%s' % item] = workerstatus.get('item-%s' % item, 0) + result.get(item, 0)

                            if result.get('start_time', False):
                                start_time = dateutil.parser.parse(result['start_time'])

                                if earliest_start_time is None:
                                    earliest_start_time = start_time
                                else:
                                    if start_time < earliest_start_time:
                                        earliest_start_time = start_time
                                if latest_start_time is None:
                                    latest_start_time = start_time
                                else:
                                    if start_time > latest_start_time:
                                        latest_start_time = start_time

                            if result.get('finish_time', False):
                                finish_time = dateutil.parser.parse(result['finish_time'])

                                if earliest_finish_time is None:
                                    earliest_finish_time = finish_time
                                else:
                                    if finish_time < earliest_finish_time:
                                        earliest_finish_time = finish_time
                                if latest_finish_time is None:
                                    latest_finish_time = finish_time
                                else:
                                    if finish_time > latest_finish_time:
                                        latest_finish_time = finish_time

                        elif log.status_code == 404:
                            workerstatus['hasntlaunched'] = workerstatus.get('hasntlaunched', 0) + 1

                        else:
                            workerstatus['unknown'] = workerstatus.get('unknown', 0) + 1

                    except:
                        workerstatus['unknown'] = workerstatus.get('unknown', 0) + 1

                if earliest_start_time is not None:
                    workerstatus['earliest_start_time'] = earliest_start_time.strftime("%B %d, %Y %H:%M:%S")
                if earliest_finish_time is not None:
                    workerstatus['earliest_finish_time'] = earliest_finish_time.strftime("%B %d, %Y %H:%M:%S")
                if latest_start_time is not None:
                    workerstatus['latest_start_time'] = latest_start_time.strftime("%B %d, %Y %H:%M:%S")
                if latest_finish_time is not None:
                    workerstatus['latest_finish_time'] = latest_finish_time.strftime("%B %d, %Y %H:%M:%S")
                allprojectdata[key] = workerstatus

            return JsonResponse(allprojectdata, safe=True)
        return HttpResponse('{}')


@login_required
def editsettings(request, settingtype, projectname):

    try:
        project = Project.objects.get(user=request.user, project_name=projectname)
    except Project.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    if request.method == 'GET':
        if settingtype == 'linkgenerator':
            settingtext = project.settings_link_generator
            form = Settings(initial={'settings': settingtext})
            return render(request, "editsettings.html", {'username': request.user.username, 'project': projectname, 'form': form, 'settingtype': settingtype})
        if settingtype == 'scraper':
            settingtext = project.settings_scraper
            form = Settings(initial={'settings': settingtext})
            return render(request, "editsettings.html", {'username': request.user.username, 'project': projectname, 'form': form, 'settingtype': settingtype})

    if request.method == 'POST':
        if 'cancel' in request.POST:
            return HttpResponseRedirect(reverse("manageproject", args=(projectname,)))
        if 'submit' in request.POST:
            form = Settings(request.POST)
            if form.is_valid():
                if settingtype == "linkgenerator":
                    project.settings_link_generator = form.cleaned_data['settings']
                    project.save()
                if settingtype == "scraper":
                    project.settings_scraper = form.cleaned_data['settings']
                    project.save()
                return HttpResponseRedirect(reverse("manageproject", args=(projectname,)))
            else:
                return render(request, "editsettings.html",
                              {'username': request.user.username, 'project': projectname, 'form': form,
                               'settingtype': settingtype})


@login_required
def start_project_on_all(request, projectname):

    uniqueprojectname = request.user.username + '_' + projectname

    try:
        project = Project.objects.get(user=request.user, project_name=projectname)
    except Project.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    workers = []
    workers.append(settings.LINK_GENERATOR)
    for worker in settings.SCRAPERS:
        workers.append(worker)

    if request.method == 'POST':
        for worker in workers:
            try:
                r = requests.post('%s/schedule.json' % worker, data={'project': uniqueprojectname, 'spider': uniqueprojectname}, timeout=(3, None))
            except:
                pass
        return HttpResponse('sent start signal')


@login_required
def stop_project_on_all(request, projectname):
    uniqueprojectname = request.user.username + '_' + projectname
    try:
        project = Project.objects.get(user=request.user, project_name=projectname)
    except Project.DoesNotExist:
        return HttpResponseNotFound('Nothing is here.')

    workers = []
    workers.append(settings.LINK_GENERATOR)
    for worker in settings.SCRAPERS:
        workers.append(worker)

    if request.method == 'POST':
        for worker in workers:
            try:
                r = requests.get('%s/listjobs.json' % worker,
                                 params={'project': uniqueprojectname}, timeout=(3, None))
                result = r.json()
                jobid = result['running'][0]['id']
                s = requests.post('%s/cancel.json' % worker, params={'project': uniqueprojectname, 'job': jobid}, timeout=(3, None))
            except:
                pass
        return HttpResponse('sent stop signal')


@login_required
def get_global_system_status(request):

    status = {}

    workers = []
    for worker in settings.SCRAPERS:
        workers.append(worker)

    worker_count = 0
    for worker in workers:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            host = urlparse(worker).hostname
            port = int(urlparse(worker).port)
            result = sock.connect_ex((host, port))
            if result == 0:
                worker_count += 1
        except:
            pass
        finally:
            sock.close()

    status['scrapers'] = worker_count

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        host = urlparse(settings.LINK_GENERATOR).hostname
        port = int(urlparse(settings.LINK_GENERATOR).port)
        result = sock.connect_ex((host, port))
        if result == 0:
            status['linkgenerator'] = True
        else:
            status['linkgenerator'] = False
    except:
        status['linkgenerator'] = False
    finally:
        sock.close()

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((settings.RABBITMQ_HOST, settings.RABBITMQ_PORT))
        if result == 0:
            status['queue'] = True
        else:
            status['queue'] = False
    except:
        status['queue'] = False
    finally:
        sock.close()

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        host = urlparse("http://" + settings.MONGODB_URI).hostname
        port = int(urlparse("http://" + settings.MONGODB_URI).port)
        result = sock.connect_ex((host, port))
        if result == 0:
            status['database'] = True
        else:
            status['database'] = False
    except:
        status['database'] = False
    finally:
        sock.close()

    status['databaseaddress'] = settings.MONGODB_PUBLIC_ADDRESS

    return JsonResponse(status, safe=False)