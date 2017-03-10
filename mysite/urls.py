"""mysite URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import include, url
from django.contrib import admin
from mysite.views import custom_login, custom_register
from django.contrib.auth.views import logout
import scrapyproject.urls as projecturls

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/login/$', custom_login, name='login'),
    url(r'^accounts/register/$', custom_register, name='registration_register'),
    url(r'^accounts/logout/$', logout, {'next_page': '/project'}, name='logout'),
    url(r'^project/', include(projecturls)),
]
