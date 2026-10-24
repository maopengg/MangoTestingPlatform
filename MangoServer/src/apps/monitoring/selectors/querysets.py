from src.apps.monitoring.models import MonitoringReport, MonitoringTask


class MonitoringQuerySelector:
    @staticmethod
    def monitoring_task():
        return MonitoringTask.objects.all()

    @staticmethod
    def monitoring_report():
        return MonitoringReport.objects.all()
