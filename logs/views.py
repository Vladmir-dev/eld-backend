# logs/views.py
from rest_framework import viewsets
from .models import DailyLog, LogEntry
from .serializers import DailyLogSerializer, LogEntrySerializer
from rest_framework.permissions import IsAuthenticated

class DailyLogViewSet(viewsets.ModelViewSet):
    queryset = DailyLog.objects.all()
    serializer_class = DailyLogSerializer
    permission_classes = [IsAuthenticated]

class LogEntryViewSet(viewsets.ModelViewSet):
    queryset = LogEntry.objects.all()
    serializer_class = LogEntrySerializer
    permission_classes = [IsAuthenticated]
