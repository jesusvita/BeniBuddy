from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Tip, PaycheckCycle

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full p-2 border border-gray-300 rounded mt-1 mb-3',
                'placeholder': field.label
            })
class TipForm(forms.ModelForm):
    class Meta:
        model = Tip
        # Add 'date' to this list:
        fields = ['date', 'amount', 'gratuity', 'note'] 
        widgets = {
            # Ensure the widget uses the correct input type (DateInput for DateField, DateTimeInput for DateTimeField)
            # Since your model uses DateTimeField but your input is just date, DateInput is likely fine
            # if you only care about the date part. Django handles the conversion.
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'hidden'}), # Keep it hidden for the modal
            'note': forms.Textarea(attrs={'rows': 3, 'class': 'w-full p-2 border border-gray-300 rounded'}),
            # You might want to explicitly define widgets for amount/gratuity if needed,
            # otherwise they default to NumberInput.
            'amount': forms.NumberInput(attrs={'step': '0.01'}),
            'gratuity': forms.NumberInput(attrs={'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply styling to all fields except the hidden date and the note textarea
        for field_name, field in self.fields.items():
            # Apply default styling unless it's the hidden date or the note
            if field_name not in ['date', 'note']: 
                 field.widget.attrs.update({
                    'class': 'w-full p-2 border border-gray-300 rounded mt-1 mb-3',
                    'placeholder': field.label.capitalize() # Use capitalize for better placeholder text
                })
            # Ensure the note textarea also gets its specific styling (redundant if already in widgets)
            elif field_name == 'note':
                 field.widget.attrs.update({
                    'rows': 3, 
                    'class': 'w-full p-2 border border-gray-300 rounded'
                 })
            # Ensure the date input remains hidden (redundant if already in widgets)
            elif field_name == 'date':
                 field.widget.attrs.update({
                     'type': 'date', # Keep type for potential browser fallback/validation
                     'class': 'hidden' # Ensure it stays hidden
                 })

class PaycheckCycleForm(forms.ModelForm):
    class Meta:
        model = PaycheckCycle
        fields = ['start_date']
        widgets = {
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full p-2 border border-gray-300 rounded mt-1 mb-3'
            })
        }