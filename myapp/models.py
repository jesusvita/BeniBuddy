from django.db import models
from django.contrib.auth.models import User  # Import Django's built-in User model


class Tip(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    gratuity = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    date = models.DateTimeField()  # Manually entered date (when the tip was earned)
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - ${self.amount} on {self.date.strftime('%Y-%m-%d')}"
    
class PaycheckCycle(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    start_date = models.DateField(null=True, blank=True)  

    def __str__(self):
        return f"{self.user.username}'s cycle starting {self.start_date}"    