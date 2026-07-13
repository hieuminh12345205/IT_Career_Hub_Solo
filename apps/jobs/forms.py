from django import forms

from apps.companies.models import Company
from apps.jobs.models import Job, Skill

JOB_TYPE_CHOICES_VI = [
    (Job.JobType.FULL_TIME, "Toàn thời gian"),
    (Job.JobType.PART_TIME, "Bán thời gian"),
    (Job.JobType.INTERN, "Thực tập"),
]
EXPERIENCE_CHOICES_VI = [
    (Job.ExperienceLevel.INTERN, "Thực tập sinh"),
    (Job.ExperienceLevel.JUNIOR, "Junior"),
    (Job.ExperienceLevel.MIDDLE, "Middle"),
    (Job.ExperienceLevel.SENIOR, "Senior"),
]


class JobFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Từ khóa",
        widget=forms.TextInput(attrs={"placeholder": "Tên việc, công ty, kỹ năng..."}),
    )
    location = forms.CharField(required=False, label="Địa điểm")
    skill = forms.ModelChoiceField(
        queryset=Skill.objects.none(),
        required=False,
        empty_label="Tất cả kỹ năng",
        label="Kỹ năng",
    )
    salary_min = forms.IntegerField(
        required=False,
        min_value=0,
        label="Lương tối thiểu (VNĐ)",
        widget=forms.NumberInput(attrs={"min": 0, "placeholder": "Ví dụ: 10000000"}),
    )
    salary_max = forms.IntegerField(
        required=False,
        min_value=0,
        label="Lương tối đa (VNĐ)",
        widget=forms.NumberInput(attrs={"min": 0, "placeholder": "Ví dụ: 30000000"}),
    )
    job_type = forms.ChoiceField(
        required=False,
        label="Loại việc",
        choices=[("", "Tất cả")] + JOB_TYPE_CHOICES_VI,
    )
    experience_level = forms.ChoiceField(
        required=False,
        label="Kinh nghiệm",
        choices=[("", "Tất cả")] + EXPERIENCE_CHOICES_VI,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["skill"].queryset = Skill.objects.order_by("name")

    def clean(self):
        cleaned_data = super().clean()
        salary_min = cleaned_data.get("salary_min")
        salary_max = cleaned_data.get("salary_max")
        if (
            salary_min is not None
            and salary_max is not None
            and salary_min > salary_max
        ):
            self.add_error(
                "salary_max",
                "Mức lương tối đa phải lớn hơn hoặc bằng mức lương tối thiểu.",
            )
        return cleaned_data


class JobForm(forms.ModelForm):
    skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all().order_by("name"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Kỹ năng",
    )

    class Meta:
        model = Job
        fields = (
            "company",
            "title",
            "description",
            "requirement",
            "skills",
            "salary_min",
            "salary_max",
            "location",
            "job_type",
            "experience_level",
            "is_active",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "requirement": forms.Textarea(attrs={"rows": 5}),
        }
        labels = {
            "company": "Công ty",
            "title": "Vị trí tuyển dụng",
            "description": "Mô tả công việc",
            "requirement": "Yêu cầu ứng viên",
            "salary_min": "Mức lương tối thiểu (VNĐ)",
            "salary_max": "Mức lương tối đa (VNĐ)",
            "location": "Địa điểm",
            "job_type": "Loại việc",
            "experience_level": "Kinh nghiệm",
            "is_active": "Đang tuyển",
        }

    def __init__(self, *args, recruiter=None, **kwargs):
        super().__init__(*args, **kwargs)
        if recruiter is not None:
            companies = Company.objects.filter(recruiter=recruiter)
            assigned_company = getattr(
                getattr(recruiter, "recruiter_profile", None),
                "company",
                None,
            )
            if assigned_company:
                companies = companies | Company.objects.filter(pk=assigned_company.pk)
            self.fields["company"].queryset = companies.distinct()

        self.fields["salary_min"].min_value = 0
        self.fields["salary_min"].widget.attrs["min"] = 0
        self.fields["salary_max"].min_value = 0
        self.fields["salary_max"].widget.attrs["min"] = 0
        self.fields["job_type"].choices = JOB_TYPE_CHOICES_VI
        self.fields["experience_level"].choices = EXPERIENCE_CHOICES_VI
