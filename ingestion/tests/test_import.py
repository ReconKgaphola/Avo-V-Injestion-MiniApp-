import pytest
from django.core.management import call_command
from ingestion.models import RawSessionRow, ConsolidatedSession
import tempfile
import os

@pytest.mark.django_db
class TestImportCommand:
    
    def test_idempotent_import(self):
        """Test that importing the same file twice leaves DB unchanged"""
        csv_content = """session_code,organisation,programme,facilitator,session_date,attendees,source_file
AVO-001,Org A,Program X,Fred,2024-01-01,25,test.csv
AVO-002,Org B,Program Y,Jane,2024-01-02,30,test.csv"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            # First import
            call_command('import_sessions', temp_path)
            
            # Second import (should be idempotent)
            call_command('import_sessions', temp_path)
            
            # Check counts - should only have 2 rows, not 4
            assert RawSessionRow.objects.count() == 2
            assert ConsolidatedSession.objects.count() == 2
            
        finally:
            os.unlink(temp_path)
    
    def test_consolidation_rules(self):
        """Test consolidation with conflicting data"""
        csv_content = """session_code,organisation,programme,facilitator,session_date,attendees,source_file
AVO-001,Org A,Program X,Fred,2024-01-01,25,file1.csv
AVO-001,Org A,Program X,Jane,2024-01-02,30,file2.csv"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            call_command('import_sessions', temp_path)
            
            session = ConsolidatedSession.objects.get(session_code='AVO-001')
            assert session.session_date.strftime('%Y-%m-%d') == '2024-01-02'  # Latest date
            assert session.attendees == 30  # Max attendees
            assert session.raw_sources.count() == 2  # Both sources linked
            
        finally:
            os.unlink(temp_path)