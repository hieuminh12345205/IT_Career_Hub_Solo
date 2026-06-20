from django import forms

from .models import Application


MAX_CV_SIZE = 5 * 1024 * 1024


class ApplicationForm(forms.ModelForm):
    """Form ứng tuyển với các kiểm tra phụ thuộc candidate và job hiện tại."""

    class Meta:
        model = Application
        fields = ("cover_letter", "cv")
        widgets = {
            "cover_letter": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, candidate=None, job=None, **kwargs):
        super().__init__(*args, **kwargs)
        # View truyền hai giá trị này vào để form kiểm tra trạng thái và đơn trùng.
        self.candidate = candidate
        self.job = job

    def clean_cv(self):
        """Chỉ nhận file PDF có kích thước tối đa 5MB."""
        cv = self.cleaned_data["cv"]

        if cv.size > MAX_CV_SIZE:
            raise forms.ValidationError("CV không được lớn hơn 5MB.")

        if getattr(cv, "content_type", None) != "application/pdf":
            raise forms.ValidationError("CV phải là file PDF.")

        return cv

    def clean(self):
        """Không cho ứng tuyển job đã đóng hoặc ứng tuyển cùng job hai lần."""
        cleaned_data = super().clean()

        if self.job and not self.job.is_active:
            raise forms.ValidationError("Công việc này đã đóng ứng tuyển.")

        if (
            self.candidate
            and self.job
            and Application.objects.filter(
                candidate=self.candidate,
                job=self.job,
            ).exists()
        ):
            raise forms.ValidationError("Bạn đã ứng tuyển công việc này rồi.")

        return cleaned_data
