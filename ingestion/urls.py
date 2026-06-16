from django.urls import path
from ingestion import views

urlpatterns = [
    path('sessions/', views.SessionListView.as_view(), name='session-list'),
    path('sessions/<str:session_code>/', views.SessionDetailView.as_view(), name='session-detail'),
    path('sessions/export/', views.SessionExportView.as_view(), name='session-export'),
]