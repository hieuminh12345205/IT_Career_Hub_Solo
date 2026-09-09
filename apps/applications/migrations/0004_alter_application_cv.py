import django.core.validators
from django.db import migrations, models

import apps.core.validators


class Migration(migrations.Migration):
    dependencies = [
        (
            "applications",
            "0003_alter_application_options_alter_bookmark_options_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="application",
            name="cv",
            field=models.FileField(
                upload_to="application_cvs/",
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=["pdf"]
                    ),
                    apps.core.validators.validate_pdf_upload,
                ],
            ),
        ),
    ]
