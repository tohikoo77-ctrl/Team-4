from django import forms
from .models.user import User

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = [
            'username',
            'password',
            'phone_number',
            'workplace',
            'salary',
            'is_married',
        ]

from django import forms
from .models.credit import Credit

class CreditForm(forms.ModelForm):
    class Meta:
        model = Credit
        fields = ['amount', 'years']