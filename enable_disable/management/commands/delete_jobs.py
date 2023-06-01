from django.core.management.base import BaseCommand
from enable_disable.models import Job
import datetime

class Command(BaseCommand):

    def handle(self, *args, **options):
        
        one_day_ago = datetime.datetime.now() - datetime.timedelta(hours=24)
        jobs = Job.objects.filter(created_date__lt = one_day_ago)
        jobs.delete()


