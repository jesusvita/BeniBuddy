from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _ # For choices
from datetime import date, timedelta, datetime
import decimal

class Tip(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    gratuity = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    date = models.DateTimeField()  # Manually entered date (when the tip was earned)
    note = models.TextField(blank=True, null=True)

    cash_made = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=decimal.Decimal('0.00'), # Or null=True, blank=True if optional
        verbose_name="Cash Made ($)"
    )

    hours_worked = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=decimal.Decimal('0.00'), # Or null=True, blank=True if optional
        verbose_name="Hours Worked"
    )

    def __str__(self):
        return f"{self.user.username} - ${self.amount} on {self.date.strftime('%Y-%m-%d')}"
    
class PaycheckCycle(models.Model):
    # Define choices for pay frequency directly here
    class PayFrequency(models.TextChoices):
        WEEKLY = 'weekly', _('Weekly')
        BIWEEKLY = 'biweekly', _('Bi-weekly (Every 2 weeks)')
        # Add more if needed, e.g.:
        # MONTHLY = 'monthly', _('Monthly')
        # SEMIMONTHLY = 'semimonthly', _('Semi-monthly (Twice a month)')

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='paycheck_cycle') # Added related_name
    start_date = models.DateField(null=True, blank=True)
    # Add the frequency field
    frequency = models.CharField(
        max_length=20,
        choices=PayFrequency.choices,
        default=PayFrequency.BIWEEKLY, # Set a sensible default
        null=True, # Allow null initially if preferred
        blank=True # Allow blank initially if preferred
    )

    def __str__(self):
        freq_display = self.get_frequency_display() if self.frequency else "Not set"
        start_display = self.start_date.strftime('%Y-%m-%d') if self.start_date else "Not set"
        return f"{self.user.username}'s {freq_display} cycle starting {start_display}"

    # Optional: Add a property to calculate the end date based on frequency
    @property
    def end_date(self):
        if not self.start_date or not self.frequency:
            return None
        if self.frequency == self.PayFrequency.WEEKLY:
            return self.start_date + timedelta(days=6)
        elif self.frequency == self.PayFrequency.BIWEEKLY:
            return self.start_date + timedelta(days=13)
        # Add logic for other frequencies if needed
        # elif self.frequency == self.PayFrequency.MONTHLY:
        #     # This is more complex, need to find end of month or specific day
        #     pass
        return None # Default if frequency logic isn't implemented