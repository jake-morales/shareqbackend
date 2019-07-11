from django.db import models
from django.utils import timezone
from django.contrib.sessions.models import Session

# Create your models here.
class Queue (models.Model):
    room = models.SmallIntegerField(primary_key=True)
    access_token = models.CharField(max_length=250, default=None)
    refresh_token = models.CharField(max_length=250, default=None)
    spotify_id = models.CharField(max_length=250, default=None)

    def __str__(self):
        return "Queue %s" % self.room

class Track(models.Model):
    queue = models.ForeignKey('Queue', related_name='tracks', on_delete=models.CASCADE)
    votes = models.SmallIntegerField(default=0)
    uri = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    artist = models.CharField(max_length=100, default='')
    image = models.CharField(max_length=100)



    class Meta:
        ordering = ['-votes']

    def __str__(self):
        return "Track %s" % self.name

class ClientToken(models.Model):
    access_token = models.CharField(max_length=100, default=None)
    token_received = models.DateTimeField(auto_now=True)

    # to only allow one instance
    def save(self, *args, **kwargs):
        if ClientToken.objects.exists() and not self.pk:
        # if you'll not check for self.pk 
        # then error will also raised in update of exists model
            raise ValidationError('There is can be only one ClientToken instance')
        token_receieved = timezone.now
        return super(ClientToken, self).save(*args, **kwargs)