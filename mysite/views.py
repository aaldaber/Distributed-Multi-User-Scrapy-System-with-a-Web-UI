from django.http import HttpResponse, Http404
from django.shortcuts import render
import datetime
from django.http import HttpResponseRedirect
from django.core.mail import send_mail
from django.contrib.auth.views import login
from registration.backends.simple import views


class MyRegistrationView(views.RegistrationView):
    def get_success_url(self, user):
        return "/project"

def custom_login(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect('/project')
    else:
        return login(request)

def custom_register(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect('/project')
    else:
        register = MyRegistrationView.as_view()
        return register(request)