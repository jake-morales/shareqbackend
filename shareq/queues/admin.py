from django.contrib import admin
from django.contrib.sessions.models import Session

# Register your models here.
from .models import Queue, Track, ClientToken

admin.site.register(Queue)
admin.site.register(Track)
admin.site.register(ClientToken)
admin.site.register(Session)