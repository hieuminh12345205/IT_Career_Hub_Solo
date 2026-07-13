from django import forms

from .models import Company


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ("name", "description", "website", "logo", "location")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
        }
