from django.db import models
from trips.models import Trip

class DailyLog(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="logs")
    date = models.DateField()

    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    total_miles_driven = models.FloatField(default=0.0)
    total_mileage_today = models.FloatField(default=0.0)

    trailer_or_plate = models.CharField(max_length=100, blank=True, null=True)
    carrier_name = models.CharField(max_length=255, blank=True, null=True)
    main_office_address = models.CharField(max_length=255, blank=True, null=True)
    home_terminal_address = models.CharField(max_length=255, blank=True, null=True)
    manifest_number = models.CharField(max_length=100, blank=True, null=True)
    shipper_and_commodity = models.CharField(max_length=255, blank=True, null=True)

    remarks = models.TextField(blank=True, null=True)

    total_driving_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_on_duty_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_off_duty_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_sleeper_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def calculate_and_save_totals(self):
        """
        Calculates total hours for each activity type from related LogEntries
        and updates the fields on the DailyLog.
        """
        
        # Calculate the duration (end_hour - start_hour) for each entry
        duration_expression = ExpressionWrapper(
            F('end_hour') - F('start_hour'), 
            output_field=DecimalField(max_digits=5, decimal_places=2)
        )

        # Aggregate durations based on activity type
        aggregation = self.entries.annotate(
            duration=duration_expression
        ).values('activity_type').annotate(
            total_duration=Sum('duration')
        )

        # Reset all totals to 0 before applying new sums
        self.total_driving_hours = 0
        self.total_on_duty_hours = 0
        self.total_off_duty_hours = 0
        self.total_sleeper_hours = 0

        # Map the calculated totals back to the DailyLog fields
        for item in aggregation:
            activity = item['activity_type']
            duration = item['total_duration']
            
            if activity == 'driving':
                self.total_driving_hours = duration
            elif activity == 'on_duty':
                self.total_on_duty_hours = duration
            elif activity == 'off_duty':
                self.total_off_duty_hours = duration
            elif activity == 'sleeper':
                self.total_sleeper_hours = duration

        # Save the updated DailyLog instance without recursively calling save
        self.save(update_fields=[
            'total_driving_hours', 
            'total_on_duty_hours', 
            'total_off_duty_hours', 
            'total_sleeper_hours'
        ])

    def __str__(self):
        return f"Log {self.date} - Trip {self.trip.id}"


class LogEntry(models.Model):
    daily_log = models.ForeignKey(DailyLog, on_delete=models.CASCADE, related_name="entries")

    ACTIVITY_CHOICES = [
        ("off_duty", "Off Duty"),
        ("sleeper", "Sleeper Berth"),
        ("driving", "Driving"),
        ("on_duty", "On Duty (Not Driving)"),
    ]
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_CHOICES)
    start_hour = models.PositiveSmallIntegerField()
    end_hour = models.PositiveSmallIntegerField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    location_name = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def duration(self):
        return self.end_hour - self.start_hour

    def __str__(self):
        return f"{self.get_activity_type_display()} ({self.start_hour}-{self.end_hour})"
