from ingestion.models import ConsolidatedSession, RawSessionRow

class ConsolidationService:
    """
    Consolidation rules:
    1. String fields: prefer non-empty, longer values
    2. Attendees: take the maximum (most inclusive)
    3. Session date: prefer the latest
    """
    
    def create_from_raw(self, raw_data):
        consolidated = ConsolidatedSession(
            session_code=raw_data['session_code'],
            organisation=raw_data['organisation'] or 'Unknown',
            programme=raw_data['programme'] or 'Unknown',
            facilitator=raw_data['facilitator'] or 'Unknown',
            session_date=raw_data['session_date'],
            attendees=raw_data['attendees'] or 0
        )
        consolidated.save()
        
        raw_row = self._get_raw_row(raw_data)
        if raw_row:
            consolidated.raw_sources.add(raw_row)
        return consolidated
    
    def update_existing(self, consolidated, raw_data):
        updated = False
        
        # Organisation: prefer non-empty, longer value
        if raw_data['organisation'] and raw_data['organisation'] != 'Unknown':
            if not consolidated.organisation or consolidated.organisation == 'Unknown':
                consolidated.organisation = raw_data['organisation']
                updated = True
            elif len(raw_data['organisation']) > len(consolidated.organisation):
                consolidated.organisation = raw_data['organisation']
                updated = True
        
        # Programme: prefer non-empty, longer value
        if raw_data['programme'] and raw_data['programme'] != 'Unknown':
            if not consolidated.programme or consolidated.programme == 'Unknown':
                consolidated.programme = raw_data['programme']
                updated = True
            elif len(raw_data['programme']) > len(consolidated.programme):
                consolidated.programme = raw_data['programme']
                updated = True
        
        # Facilitator: prefer non-empty, longer value
        if raw_data['facilitator'] and raw_data['facilitator'] != 'Unknown':
            if not consolidated.facilitator or consolidated.facilitator == 'Unknown':
                consolidated.facilitator = raw_data['facilitator']
                updated = True
            elif len(raw_data['facilitator']) > len(consolidated.facilitator):
                consolidated.facilitator = raw_data['facilitator']
                updated = True
        
        # Attendees: take the maximum
        if raw_data['attendees'] is not None:
            if consolidated.attendees is None or raw_data['attendees'] > consolidated.attendees:
                consolidated.attendees = raw_data['attendees']
                updated = True
        
        # Session date: prefer the latest
        if raw_data['session_date']:
            if not consolidated.session_date or raw_data['session_date'] > consolidated.session_date:
                consolidated.session_date = raw_data['session_date']
                updated = True
        
        # Link to raw source
        raw_row = self._get_raw_row(raw_data)
        if raw_row:
            consolidated.raw_sources.add(raw_row)
        
        if updated:
            consolidated.save()
        return updated
    
    def _get_raw_row(self, raw_data):
        try:
            return RawSessionRow.objects.filter(
                session_code=raw_data['session_code'],
                row_hash=raw_data['row_hash'],
                source_file=raw_data['source_file']
            ).first()
        except RawSessionRow.DoesNotExist:
            return None