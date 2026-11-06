from src.apps.monitoring.models import MonitoringReport, MonitoringTask, ServiceHeartbeat


class MonitoringQuerySelector:
    @staticmethod
    def service_heartbeats():
        return ServiceHeartbeat.objects.all()

    @staticmethod
    def monitoring_task():
        return MonitoringTask.objects.all()

    @staticmethod
    def monitoring_report():
        return MonitoringReport.objects.all()
