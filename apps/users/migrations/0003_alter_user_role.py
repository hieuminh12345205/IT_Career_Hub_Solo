from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0002_candidateprofile_recruiterprofile"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("admin", "Admin"),
                    ("recruiter", "Recruiter"),
                    ("candidate", "Candidate"),
                ],
                default="candidate",
                max_length=20,
            ),
        ),
    ]
