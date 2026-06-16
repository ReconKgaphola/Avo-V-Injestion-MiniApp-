from rest_framework import serializers
from ingestion.models import ConsolidatedSession, RawSessionRow

class RawSessionRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawSessionRow
        fields = ['session_code', 'organisation', 'programme', 
                  'facilitator', 'session_date', 'attendees', 
                  'source_file', 'import_timestamp']

class ConsolidatedSessionSerializer(serializers.ModelSerializer):
    raw_sources = RawSessionRowSerializer(many=True, read_only=True)
    
    class Meta:
        model = ConsolidatedSession
        fields = ['session_code', 'organisation', 'programme', 
                  'facilitator', 'session_date', 'attendees',
                  'created_at', 'updated_at', 'raw_sources']