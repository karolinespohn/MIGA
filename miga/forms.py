from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        help_text='Required. Enter a valid email address.'
    )
    first_name = forms.CharField(
        required=True,
        help_text='Required. Enter your first name.'
    )
    last_name = forms.CharField(
        required=True,
        help_text='Required. Enter your last name.'
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2')

    def clean(self):
        cleaned_data = super().clean()
        print("Form cleaned_data:", cleaned_data)  # Debug print
        print("Form errors:", self.errors)  # Debug print

        # Get the password values
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        # Check if both passwords are provided and match
        if password1 and password2 and password1 != password2:
            self.add_error('password2', "The two password fields must match.")

        # Check password length
        if password1 and len(password1) < 8:
            self.add_error('password1', "Password must be at least 8 characters long.")

        return cleaned_data

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email address is already in use.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user
