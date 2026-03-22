from django.urls import path
from . import views

urlpatterns = [
    path('', views.DocumentListView.as_view(), name='document-list'),
    path('upload/', views.DocumentUploadView.as_view(), name='document-upload'),
    path('<uuid:pk>/', views.DocumentDetailView.as_view(), name='document-detail'),
]
