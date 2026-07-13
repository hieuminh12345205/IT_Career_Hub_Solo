from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import CandidateProfile, RecruiterProfile, User

MAX_CV_SIZE = 5 * 1024 * 1024


def validate_pdf_upload(uploaded_file):
    """Validate a newly uploaded CV without trusting its extension alone."""
    if not uploaded_file:
        return uploaded_file
    if not hasattr(uploaded_file, "content_type"):
        return uploaded_file
    if uploaded_file.size > MAX_CV_SIZE:
        raise forms.ValidationError("CV không được lớn hơn 5MB.")
    if uploaded_file.content_type != "application/pdf":
        raise forms.ValidationError("CV phải là file PDF hợp lệ.")
    uploaded_file.seek(0)
    header = uploaded_file.read(5)
    uploaded_file.seek(0)
    if header != b"%PDF-":
        raise forms.ValidationError("CV phải là file PDF hợp lệ.")
    return uploaded_file


class BaseSignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=False, label="Tên")
    last_name = forms.CharField(max_length=150, required=False, label="Họ")

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "password1",
            "password2",
        )

    role = None

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if self.role:
            user.role = self.role
        if commit:
            user.save()
        return user

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Email này đã được sử dụng.")
        return email


class CandidateSignUpForm(BaseSignUpForm):
    role = User.Role.CANDIDATE


class RecruiterSignUpForm(BaseSignUpForm):
    role = User.Role.RECRUITER


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "phone",
            "avatar",
            "bio",
        )
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if not email:
            return email
        if (
            User.objects.filter(email__iexact=email)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError("Email này đã được sử dụng.")
        return email


class CandidateProfileForm(forms.ModelForm):
    class Meta:
        model = CandidateProfile
        fields = (
            "full_name",
            "bio",
            "skills",
            "experience_years",
            "cv_file",
            "location",
        )
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4}),
            "skills": forms.CheckboxSelectMultiple,
            "cv_file": forms.FileInput,
        }

    def clean_cv_file(self):
        return validate_pdf_upload(self.cleaned_data.get("cv_file"))


class RecruiterProfileForm(forms.ModelForm):
    class Meta:
        model = RecruiterProfile
        # Company assignment is controlled by an admin, not by a public
        # recruiter profile form. This prevents self-assigning to another
        # company's jobs and applications.
        fields = ("position",)
