from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Expense(models.Model):
    class ExpenseCategory(models.TextChoices):
        BILL = 'BILL', _('Bill')
        FOOD = 'FOOD', _('Food')
        GROCERIES = 'GROCERIES', _('Groceries')
        GAS = 'GAS', _('Gas')
        SHOPPING = 'SHOPPING', _('Shopping')
        OTHER = 'OTHER', _('Other')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(
        max_length=20,
        choices=ExpenseCategory.choices,
        default=ExpenseCategory.OTHER,
    )
    expense_date = models.DateField() 
    date_added = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} - ${self.amount} on {self.expense_date.strftime('%Y-%m-%d')} by {self.user.username}"

    class Meta:
        ordering = ['-expense_date', '-date_added']
