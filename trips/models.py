from django.db import models
from django.conf import settings

class Trip(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trips")
    pickup_location = models.CharField(max_length=255)
    pickup_latitude = models.FloatField(blank=True, null=True)
    pickup_longitude = models.FloatField(blank=True, null=True)
    dropoff_location = models.CharField(max_length=255)
    dropoff_latitude = models.FloatField(blank=True, null=True)
    dropoff_longitude = models.FloatField(blank=True, null=True)
    current_location = models.CharField(max_length=255, blank=True, null=True)
    current_cycle_used = models.DecimalField(max_digits=5, decimal_places=2)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(blank=True, null=True)
    total_miles = models.FloatField(default=0.0)
    status = models.CharField(
        max_length=20,
        choices=[("ongoing", "Ongoing"), ("completed", "Completed")],
        default="ongoing"
    )

    def __str__(self):
        return f"{self.user.email} Trip {self.id}: {self.pickup_location} → {self.dropoff_location}"
