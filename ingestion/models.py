from django.db import models
from django.core.validators import MinValueValidator
from django.db.models import Index

class RawSessionRow(models.Model):
    """Every ingested row, stored as received - audit trail"""
    session_code = models.CharField(max_length=50)
    organisation = models.CharField(max_length=200, blank=True)
    programme = models.CharField(max_length=200, blank=True)
    facilitator = models.CharField(max_length=200, blank=True)
    session_date = models.DateField(null=True, blank=True)
    attendees = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    source_file = models.CharField(max_length=500)
    import_timestamp = models.DateTimeField(auto_now_add=True)
    row_hash = models.CharField(max_length=64, db_index=True)
    
    class Meta:
        ordering = ['-import_timestamp']
        indexes = [
            Index(fields=['session_code', 'source_file']),
            Index(fields=['import_timestamp']),
        ]
    
    def __str__(self):
        return f"{self.session_code} ({self.source_file})"

class ConsolidatedSession(models.Model):
    """Canonical record - exactly one per session"""
    session_code = models.CharField(max_length=50, unique=True, db_index=True)
    organisation = models.CharField(max_length=200, blank=True)
    programme = models.CharField(max_length=200, blank=True)
    facilitator = models.CharField(max_length=200, blank=True)
    session_date = models.DateField(null=True, blank=True)
    attendees = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    raw_sources = models.ManyToManyField(RawSessionRow, related_name='consolidated_sessions')
    
    class Meta:
        indexes = [
            Index(fields=['organisation']),
            Index(fields=['programme']),
            Index(fields=['session_date']),
            Index(fields=['organisation', 'programme']),
            Index(fields=['session_date', 'organisation']),
        ]
    
    def __str__(self):
        return self.session_code