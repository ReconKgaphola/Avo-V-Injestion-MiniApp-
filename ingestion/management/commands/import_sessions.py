import csv
import hashlib
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from ingestion.models import RawSessionRow, ConsolidatedSession
from ingestion.services import ConsolidationService

class Command(BaseCommand):
    help = 'Import session data from CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to CSV file')
        parser.add_argument('--batch-size', type=int, default=1000, 
                          help='Batch size for bulk operations')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        batch_size = options['batch_size']
        
        stats = {
            'rows_read': 0,
            'rows_skipped': 0,
            'skipped_reasons': [],
            'sessions_created': 0,
            'sessions_updated': 0
        }
        
        # Check if file exists
        try:
            with open(csv_path, 'r') as f:
                pass
        except FileNotFoundError:
            raise CommandError(f"File not found: {csv_path}")
        
        # Process the file
        self.process_file(csv_path, batch_size, stats)
        
        # Print summary
        self.stdout.write("\n=== Import Summary ===")
        self.stdout.write(f"Rows read: {stats['rows_read']}")
        self.stdout.write(f"Rows skipped: {stats['rows_skipped']}")
        if stats['skipped_reasons']:
            self.stdout.write("Skipped reasons:")
            for reason in set(stats['skipped_reasons']):
                self.stdout.write(f"  - {reason}")
        self.stdout.write(f"Sessions created: {stats['sessions_created']}")
        self.stdout.write(f"Sessions updated: {stats['sessions_updated']}")

    def process_file(self, csv_path, batch_size, stats):
        """Process CSV file in batches for memory safety"""
        batch = []
        
        with open(csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row_num, row in enumerate(reader, 2):  # 2 = header row
                stats['rows_read'] += 1
                
                try:
                    processed = self.validate_and_prepare_row(row, row_num, csv_path)
                    if processed:
                        batch.append(processed)
                        
                        # Process batch when full
                        if len(batch) >= batch_size:
                            self.process_batch(batch, stats)
                            batch = []
                    else:
                        stats['rows_skipped'] += 1
                        
                except Exception as e:
                    stats['rows_skipped'] += 1
                    stats['skipped_reasons'].append(f"Row {row_num}: {str(e)}")
            
            # Process remaining rows
            if batch:
                self.process_batch(batch, stats)

    def validate_and_prepare_row(self, row, row_num, source_file):
        """Validate and prepare a row for processing"""
        
        # Required field: session_code
        session_code = row.get('session_code', '').strip()
        if not session_code:
            raise ValueError("Missing session_code")
        
        # Parse date if present
        session_date = None
        if row.get('session_date'):
            try:
                session_date = datetime.strptime(row['session_date'], '%Y-%m-%d').date()
            except ValueError:
                try:
                    session_date = datetime.strptime(row['session_date'], '%m/%d/%Y').date()
                except ValueError:
                    raise ValueError(f"Invalid date format: {row['session_date']}")
        
        # Parse attendees if present
        attendees = None
        if row.get('attendees'):
            try:
                attendees = int(row['attendees'])
                if attendees < 0:
                    raise ValueError("Attendees cannot be negative")
            except ValueError:
                raise ValueError(f"Invalid attendees value: {row['attendees']}")
        
        # Normalize session code (case-insensitive, trimmed)
        normalized_code = session_code.upper().strip()
        
        # Generate row hash for dedup within same file
        row_hash = hashlib.sha256(
            f"{normalized_code}|{row.get('organisation', '')}|{row.get('programme', '')}|{row.get('facilitator', '')}|{row.get('session_date', '')}|{row.get('attendees', '')}".encode()
        ).hexdigest()
        
        return {
            'session_code': normalized_code,
            'organisation': row.get('organisation', '').strip(),
            'programme': row.get('programme', '').strip(),
            'facilitator': row.get('facilitator', '').strip(),
            'session_date': session_date,
            'attendees': attendees,
            'source_file': source_file,
            'row_hash': row_hash,
        }

    @transaction.atomic
    def process_batch(self, batch, stats):
        """Process a batch of rows atomically"""
        
        # Step 1: Create/update RawSessionRow records
        raw_rows = []
        for data in batch:
            # Check if this exact row already exists (idempotency)
            existing = RawSessionRow.objects.filter(
                session_code=data['session_code'],
                row_hash=data['row_hash'],
                source_file=data['source_file']
            ).first()
            
            if not existing:
                raw_row = RawSessionRow(
                    session_code=data['session_code'],
                    organisation=data['organisation'],
                    programme=data['programme'],
                    facilitator=data['facilitator'],
                    session_date=data['session_date'],
                    attendees=data['attendees'],
                    source_file=data['source_file'],
                    row_hash=data['row_hash']
                )
                raw_rows.append(raw_row)
        
        if raw_rows:
            RawSessionRow.objects.bulk_create(raw_rows)
        
        # Step 2: Consolidate - upsert ConsolidatedSession
        consolidation_service = ConsolidationService()
        for data in batch:
            existing = ConsolidatedSession.objects.filter(
                session_code=data['session_code']
            ).first()
            
            if existing:
                updated = consolidation_service.update_existing(existing, data)
                if updated:
                    stats['sessions_updated'] += 1
            else:
                consolidation_service.create_from_raw(data)
                stats['sessions_created'] += 1