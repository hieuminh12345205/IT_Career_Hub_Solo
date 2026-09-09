import django.core.validators
from django.db import migrations, models

import apps.core.validators


class Migration(migrations.Migration):
    dependencies = [("users", "0003_alter_user_role")]

    operations = [
        migrations.AlterField(
            model_name="candidateprofile",
            name="cv_file",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="cvs/",
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=["pdf"]
                    ),
                    apps.core.validators.validate_pdf_upload,
                ],
            ),
        ),
    ]
