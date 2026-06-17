from django.urls import path
from ingestion import views

urlpatterns = [
    path('sessions/', views.SessionListView.as_view(), name='session-list'),
    # Export MUST come before the detail view (which has a variable)
    path('sessions/export/', views.SessionExportView.as_view(), name='session-export'),
    path('sessions/<str:session_code>/', views.SessionDetailView.as_view(), name='session-detail'),
]