from rest_framework import generics
from rest_framework.views import APIView
from django.http import StreamingHttpResponse
from ingestion.models import ConsolidatedSession
from ingestion.serializers import ConsolidatedSessionSerializer
from datetime import datetime
import csv

class SessionListView(generics.ListAPIView):
    """GET /api/sessions/ - List with filtering and pagination"""
    serializer_class = ConsolidatedSessionSerializer
    queryset = ConsolidatedSession.objects.all().prefetch_related('raw_sources')
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by organisation
        organisation = self.request.query_params.get('organisation')
        if organisation:
            queryset = queryset.filter(organisation__icontains=organisation)
        
        # Filter by programme
        programme = self.request.query_params.get('programme')
        if programme:
            queryset = queryset.filter(programme__icontains=programme)
        
        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(session_date__gte=date_from)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(session_date__lte=date_to)
            except ValueError:
                pass
        
        return queryset

class SessionDetailView(generics.RetrieveAPIView):
    """GET /api/sessions/<session_code>/ - Get one session with raw rows"""
    serializer_class = ConsolidatedSessionSerializer
    lookup_field = 'session_code'
    queryset = ConsolidatedSession.objects.all().prefetch_related('raw_sources')
    
    def get_object(self):
        session_code = self.kwargs['session_code'].upper().strip()
        return self.queryset.get(session_code=session_code)

class SessionExportView(APIView):
    """GET /api/sessions/export/ - Stream all sessions as CSV"""
    
    def get(self, request):
        response = StreamingHttpResponse(
            self.generate_csv(request),
            content_type='text/csv'
        )
        response['Content-Disposition'] = 'attachment; filename="sessions_export.csv"'
        return response
    
    def generate_csv(self, request):
        """Generator that yields CSV rows one at a time (constant memory)"""
        view = SessionListView()
        view.request = request
        queryset = view.get_queryset()
        
        # Header
        header = ['session_code', 'organisation', 'programme', 
                  'facilitator', 'session_date', 'attendees']
        yield ','.join(header) + '\n'
        
        # Rows (streaming)
        for session in queryset.iterator(chunk_size=1000):
            row = [
                session.session_code,
                session.organisation,
                session.programme,
                session.facilitator,
                session.session_date.strftime('%Y-%m-%d') if session.session_date else '',
                str(session.attendees) if session.attendees is not None else ''
            ]
            # Escape fields with commas
            row = [f'"{field}"' if ',' in str(field) else str(field) for field in row]
            yield ','.join(row) + '\n'