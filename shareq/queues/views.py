from django.shortcuts import render, redirect, get_object_or_404

from django.http import HttpResponse
from .models import Queue, Track, ClientToken

import requests
import json

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from datetime import timedelta, datetime
from django.utils import timezone

from django.forms.models import model_to_dict

from django.conf import settings


CLIENT_ID = '70cd90d291d44815bd60a118b76b89ef'
CLIENT_SECRET = '11c5f5e0121848ab80939f7232c54fdd'

frontendIP = 'https://shareq.app'

def callback(request):
    if (request.GET.get('error') == 'access_denied'):
        return redirect('https://shareq.app/create/?m=AuthorizationFailed')
    
    if Queue.objects.filter(room=request.GET.get('state')).exists():
        return redirect('https://shareq.app/create/?m=Queue%20already%20exists')

    # Get access/refresh tokens
    body_params={'grant_type': 'authorization_code',
                    'code': request.GET.get('code'),
                    'redirect_uri': 'https://shareq.herokuapp.com/api/callback/'}
    url = 'https://accounts.spotify.com/api/token'
    try:
        response = requests.post(url, data=body_params, auth=(CLIENT_ID, CLIENT_SECRET))
    except:
        return redirect('https://shareq.app/create/?m=BadRequestTo_api_token')
    if(response.status_code != 200):
        return redirect('https://shareq.app/create/?m=StatusCodeIsNot200')
    token_info = response.json()
    access_token = token_info['access_token']
    refresh_token = token_info['refresh_token']

    # Get Spotify Info
    headers={'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + str(access_token)}
    url = 'https://api.spotify.com/v1/me'
    try:
        response2 = requests.get(url, headers=headers)
    except:
        return redirect('https://shareq.app/create/?m=BadRequestToV1me')
    if(response2.status_code != 200):
        return redirect('https://shareq.app/create/?m=BadRequestToV1me')
    userInfo = response2.json() #convert into dictionary
    if(userInfo['product'] != "premium"):
        return redirect('https://shareq.app/create/?m=User%20needs%20Spotify%20Premium')

    # Create Queue
    roomNum = request.GET.get('state')
    request.session['admin'] = str(roomNum)
    try:
        Queue.objects.create(
            room=roomNum,
            access_token=access_token,
            refresh_token=refresh_token,
            spotify_id=userInfo['id'],
        )
    except Exception as e:
        return HttpResponse('Failed to create Queue...' + str(e))
    return redirect('https://shareq.app/queue/' + roomNum)

def next(request, room):
    #can change to "if queue is None or doesn't exist" : then reply not exist
    try:
        queue = Queue.objects.get(room=room)
    except:
        return HttpResponse("Queue does not exist" )

    #check if authorized
    if not request.session['admin']:
        return HttpResponse("You're not an admin")
    elif request.session['admin'] != str(queue.room):
        return HttpResponse("Unauthorized request")

    nextSong = Track.objects.filter(queue=room).first()
    if nextSong is None:
        return HttpResponse("Queue %s is empty." % room)
    
    url = 'https://api.spotify.com/v1/me/player/play'
    headers = { 'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + str(queue.access_token)}
    body = json.dumps( {"uris":[nextSong.uri]})
    response = requests.put(url, data=body, headers=headers)
    if response.status_code == 401:
        print("access token expired. Getting new one.")
        body_params={'grant_type': 'refresh_token',
                    'refresh_token': queue.refresh_token}
        response = requests.post("https://accounts.spotify.com/api/token", data=body_params, auth=(CLIENT_ID, CLIENT_SECRET))
        response_info = response.json()
        queue.accessToken = response_info['access_token']
        headers = { 'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + str(queue.accessToken)}
        response = requests.put(url, data=body, headers=headers)
    if response.status_code == 204:
        nextSong.delete()
    else:
        return HttpResponse("Failed to play next song. Response code: " + str(response.status_code) + str(response.text))
    
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)("queue_%s" % room,
        {
            "type": "delete_song",
            "payload": nextSong.id
        })
    return HttpResponse("Playing next song...")

def getSearchToken(request):
    instance = ClientToken.objects.all().first()
    
    #if no access token object created
    if not instance:
        body_params={'grant_type': 'client_credentials'}
        response = requests.post("https://accounts.spotify.com/api/token", data=body_params, auth=(CLIENT_ID, CLIENT_SECRET))
        if response.status_code != 200:
            return HttpResponse("failed to get token")
        res = response.json()
        ClientToken.objects.create(access_token=res['access_token'])
        return HttpResponse(json.dumps({'token': res['access_token']}))
    
    # if token expired
    if instance.token_received + timezone.timedelta(hours=1) < timezone.now(): # + timedelta(hours=-1):
        body_params={'grant_type': 'client_credentials'}
        response = requests.post("https://accounts.spotify.com/api/token", data=body_params, auth=(CLIENT_ID, CLIENT_SECRET))
        if response.status_code != 200:
            return HttpResponse("Failed to get token after expired token")
        res = response.json()
        instance.access_token = res['access_token']
        instance.save()
        return HttpResponse(json.dumps({'token':res['access_token']}))
    
    #otherwise
    return HttpResponse(json.dumps({'token':instance.access_token}))

def queueExists(request, room):
    if Queue.objects.filter(room=room).exists():
        return HttpResponse(content='exists', status=200)
    return HttpResponse(status=404)

def isAdmin(request, room):
    if request.session['admin'] == str(room):
        return HttpResponse('admin')
    else:
        return HttpResponse('not admin')

    


