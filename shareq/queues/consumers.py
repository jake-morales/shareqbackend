from channels.generic.websocket import JsonWebsocketConsumer
from asgiref.sync import async_to_sync
import json

from django.forms.models import model_to_dict
from django.db.models import F
from django.db import close_old_connections

from .models import Queue, Track

class QueueConsumer(JsonWebsocketConsumer):

    def connect(self):
        #self.queue_number = self.scope['url_route']['kwargs']['queue']
        self.queue_group_name = 'queue_'

        
        '''
        self.scope["session"]["test"] = "test1"
        print (self.scope["session"]["test"])
        self.scope["session"].save()
        '''
        self.accept()
    
    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.queue_group_name,
            self.channel_name
        )

    def receive_json(self, content):
        command = content['command']
        payload = content['payload'] 
        
        if command == 'join_room':
            self.queue_number = str(payload)
            self.queue_group_name = 'queue_%s' % self.queue_number
            async_to_sync(self.channel_layer.group_add)(
                        self.queue_group_name,
                        self.channel_name
                    )
        elif command == "fetchSongs":
            print("fetching songs")        
            songs = list(Track.objects.filter(queue=payload).values('id', 'name', 'votes', 'artist', 'image')) #may need to add image link or more
            self.send_json({
                'command': 'fetch', 
                'songs': songs})
        elif command == "new_song":
            print ("new song")
            print(payload)
            try:
                song = Track.objects.create(queue_id=payload['queue'], name=payload['name'], uri=payload['uri'], artist=payload['artist'], image=payload['image'])
            except Exception as e:
                print(e)
            async_to_sync(self.channel_layer.group_send)(
                self.queue_group_name,
                {
                    'type':'new_song',
                    'songID': song.id,
                    'songName': song.name,
                    'songArtist': song.artist,
                    'songImage': song.image,
                    'songVotes': song.votes
                }
            ) 
        elif command == "delete_song":
            print ("deleting song")
            print(payload)
            try:
                Track.objects.filter(id=payload['id']).delete()
            except Exception as e:
                print(e)
            async_to_sync(self.channel_layer.group_send)(
                self.queue_group_name,
                {
                    'type':'delete_song',
                    'songID': payload['id']
                }

            )        
        elif command == "upvote":
            try:
                Track.objects.filter(id=payload).update(votes=F('votes')+1)
                song = Track.objects.get(id=payload)
            except Exception as e:
                print(e)
            print("upvoted", payload, sep=" ")
            async_to_sync(self.channel_layer.group_send)(
            self.queue_group_name,
            {
                'type':'update',
                'songID': song.id,
                'votes': song.votes
            }
        )
        elif command == "downvote":
            try:
                Track.objects.filter(id=payload).update(votes=F('votes')-1)
                song = Track.objects.get(id=payload)
            except Exception as e:
                print(e)
            print("downvoted", payload, sep=" ")
            async_to_sync(self.channel_layer.group_send)(
            self.queue_group_name,
            {
                'type':'update',
                'songID': song.id,
                'votes': song.votes
            }
        )
        else:
            print("error")
            self.send_json({'command':'error'})

    def new_song(self, event):
        self.send_json({
            'command': 'new_song',
            'payload': {
                 'id': event['songID'],
                'name': event['songName'],
                'artist': event['songArtist'],
                'image': event['songImage'],
                'votes': event['songVotes']}
        })
    
    def delete_song(self, event):
        self.send_json({
            'command': 'delete_song',
            'payload': event['songID']
        })

    def fetch(self, event):
        self.send_json({
            'command': 'fetch',
            'payload': event['songs']
        })

    def update(self, event):
        self.send_json({
            'command': 'update',
            'payload': {
                'songID': event['songID'],
                'votes': event['votes']
            }
        })