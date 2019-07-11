from django.urls import path
from queues.views import callback, next, getSearchToken, queueExists, isAdmin

urlpatterns = [
    path('callback/', callback ),
    path('next/<int:room>/', next),
    path('token/', getSearchToken),
    path('exists/<int:room>/', queueExists),
    path('admin/<int:room>/', isAdmin),
]
