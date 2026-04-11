from django.core.management.base import BaseCommand
from tasks.models import Task

class Command(BaseCommand):
    help = 'Add YouTube short tasks (7 tasks)'

    def handle(self, *args, **kwargs):
        # Delete old youtube tasks first
        Task.objects.filter(task_type='youtube').delete()
        self.stdout.write('Deleted old YouTube tasks')

        tasks = [
            {
                'title': 'Watch YouTube Short #1',
                'description': 'Watch this short video completely and earn reward.',
                'url': 'https://youtube.com/shorts/VpA82H2NmzU?si=AjE28yl61qsGt6RU',
            },
            {
                'title': 'Watch YouTube Short #2',
                'description': 'Watch this short video completely and earn reward.',
                'url': 'https://youtube.com/shorts/sBBQlbILnF0?si=X1jNoxfkdtT0okLW',
            },
            {
                'title': 'Watch YouTube Short #3',
                'description': 'Watch this short video completely and earn reward.',
                'url': 'https://youtube.com/shorts/4QRx-4A8q7Q?si=l7XcuixUO556iQXk',
            },
            {
                'title': 'Watch YouTube Short #4',
                'description': 'Watch this short video completely and earn reward.',
                'url': 'https://youtube.com/shorts/bA9eLSDMe0g?si=TozAuM4Dj6ZsAW6W',
            },
            {
                'title': 'Watch YouTube Short #5',
                'description': 'Watch this short video completely and earn reward.',
                'url': 'https://youtube.com/shorts/aHJ_l36h9qc?si=XkHeX0DE0K3TDrME',
            },
            {
                'title': 'Watch YouTube Short #6',
                'description': 'Watch this short video completely and earn reward.',
                'url': 'https://youtube.com/shorts/RwfwO5IXEEw?si=-e60twWLEAv_TuXg',
            },
            {
                'title': 'Watch YouTube Short #7',
                'description': 'Watch this short video completely and earn reward.',
                'url': 'https://youtube.com/shorts/eGZRzh6UivI?si=-EtTm3yS6VL28Dzl',
            },
        ]

        for t in tasks:
            task = Task.objects.create(
                title=t['title'],
                description=t['description'],
                task_type='youtube',
                reward=0.10,
                time_required=60,
                url=t['url'],
                is_active=True,
                max_completions=0,
            )
            self.stdout.write(self.style.SUCCESS(f'Created: {task.title}'))

        self.stdout.write(self.style.SUCCESS('Done! 7 tasks created.'))
