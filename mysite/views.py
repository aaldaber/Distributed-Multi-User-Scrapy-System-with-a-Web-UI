from django.http import HttpResponse, Http404
from django.shortcuts import render
import datetime
from django.http import HttpResponseRedirect
from django.core.mail import send_mail
from django.contrib.auth.views import login as loginview
from registration.backends.simple import views
from django.contrib.auth import authenticate, get_user_model, login
from registration import signals
from scrapyproject.views import mongodb_user_creation, linux_user_creation
from scrapyproject.scrapy_packages import settings
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

User = get_user_model()


class MyRegistrationView(views.RegistrationView):
    def register(self, form):
        new_user = form.save()
        new_user = authenticate(
            username=getattr(new_user, User.USERNAME_FIELD),
            password=form.cleaned_data['password1']
        )

        #perform additional account creation here (MongoDB, local Unix accounts, etc.)

        mongodb_user_creation(getattr(new_user, User.USERNAME_FIELD), form.cleaned_data['password1'])

        if settings.LINUX_USER_CREATION_ENABLED:
            try:
                linux_user_creation(getattr(new_user, User.USERNAME_FIELD), form.cleaned_data['password1'])
            except:
                pass

        login(self.request, new_user)
        signals.user_registered.send(sender=self.__class__,
                                     user=new_user,
                                     request=self.request)
        return new_user

    def get_success_url(self, user):
        return "/project"


def custom_login(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect('/project')
    else:
        return loginview(request)


def custom_register(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect('/project')
    else:
        register = MyRegistrationView.as_view()
        return register(request)
