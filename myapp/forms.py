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
        fields = ['amount', 'gratuity', 'note']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full p-2 border border-gray-300 rounded'}),
            'note': forms.Textarea(attrs={'rows': 3, 'class': 'w-full p-2 border border-gray-300 rounded'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name != 'note':
                field.widget.attrs.update({
                    'class': 'w-full p-2 border border-gray-300 rounded mt-1 mb-3',
                    'placeholder': field.label
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