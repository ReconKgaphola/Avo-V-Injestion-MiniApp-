import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from ingestion.models import ConsolidatedSession, RawSessionRow
from datetime import date

@pytest.mark.django_db
class TestAPI:
    
    def setup_method(self):
        self.client = APIClient()
        
        # Create test data
        self.session1 = ConsolidatedSession.objects.create(
            session_code='AVO-001',
            organisation='Org A',
            programme='Program X',
            facilitator='Fred',
            session_date=date(2024, 1, 1),
            attendees=25
        )
        self.session2 = ConsolidatedSession.objects.create(
            session_code='AVO-002',
            organisation='Org B',
            programme='Program Y',
            facilitator='Jane',
            session_date=date(2024, 1, 2),
            attendees=30
        )
        
        # Add raw source
        raw1 = RawSessionRow.objects.create(
            session_code='AVO-001',
            organisation='Org A',
            programme='Program X',
            facilitator='Fred',
            session_date=date(2024, 1, 1),
            attendees=25,
            source_file='test.csv',
            row_hash='hash1'
        )
        self.session1.raw_sources.add(raw1)
    
    def test_filtering(self):
        """Test filtering by organisation and programme"""
        url = reverse('session-list')
        
        response = self.client.get(url, {'organisation': 'Org A'})
        assert response.status_code == 200
        assert response.data['count'] == 1
        assert response.data['results'][0]['session_code'] == 'AVO-001'
        
        response = self.client.get(url, {'programme': 'Program Y'})
        assert response.status_code == 200
        assert response.data['count'] == 1
        assert response.data['results'][0]['session_code'] == 'AVO-002'
    
    def test_no_n_plus_one(self):
        """Test that N+1 queries are avoided"""
        # Create more data
        for i in range(5):
            session = ConsolidatedSession.objects.create(
                session_code=f'AVO-00{i+3}',
                organisation=f'Org {i}',
                programme=f'Program {i}',
                facilitator=f'Facilitator {i}',
                session_date=date(2024, 1, i+3),
                attendees=20 + i
            )
        
        url = reverse('session-list')
        
        # Should only use 2 queries (list + prefetch)
        with self.assertNumQueries(2):
            response = self.client.get(url)
            assert response.status_code == 200
    
    def test_detail_view(self):
        """Test fetching a single session with raw rows"""
        url = reverse('session-detail', kwargs={'session_code': 'AVO-001'})
        
        with self.assertNumQueries(2):  # 1 for session, 1 for raw_sources
            response = self.client.get(url)
            assert response.status_code == 200
            assert response.data['session_code'] == 'AVO-001'
            assert len(response.data['raw_sources']) == 1
    
    def test_export(self):
        """Test export endpoint"""
        url = reverse('session-export')
        response = self.client.get(url)
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv'
        assert 'Content-Disposition' in response