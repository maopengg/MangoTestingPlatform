from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("functional_test", "0011_remove_modulecoveragecase_automation_decision_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="ModuleCoverageInterfaceSnapshot"),
                migrations.DeleteModel(name="ModuleCoverageCaseSnapshot"),
                migrations.DeleteModel(name="ModuleCoverageCase"),
                migrations.DeleteModel(name="ModuleCoverageScan"),
            ],
        ),
    ]
