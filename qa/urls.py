from django.urls import path
from . import views

urlpatterns = [
    path('ask/', views.AskView.as_view(), name='qa-ask'),
    path('history/', views.QuestionHistoryView.as_view(), name='qa-history'),
]
