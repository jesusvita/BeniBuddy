from django import forms
from .models import Expense

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['name', 'amount'] # expense_date will be handled separately
        widgets = {
            'name': forms.TextInput(attrs={'class': 'mt-1 block w-full px-3 py-2 bg-paleWhite border border-softBlue rounded-md text-sm shadow-sm placeholder-gray-400 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-deepBlue', 'placeholder': 'e.g., Coffee, Lunch'}),
            'amount': forms.NumberInput(attrs={'class': 'mt-1 block w-full px-3 py-2 bg-paleWhite border border-softBlue rounded-md text-sm shadow-sm placeholder-gray-400 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-deepBlue', 'placeholder': 'e.g., 5.99'}),
        }