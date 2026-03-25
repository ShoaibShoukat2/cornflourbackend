from django.core.management.base import BaseCommand
from tasks.models import Task

class Command(BaseCommand):
    help = 'Add YouTube short tasks'

    def handle(self, *args, **kwargs):
        tasks = [
            {
                'title': 'Watch YouTube Short #1',
                'description': 'Watch this short video completely and earn reward.',
                'task_type': 'youtube',
                'reward': 0.10,  # Rs 10
                'time_required': 60,
                'url': 'https://youtube.com/shorts/l-s5g6x-VZ4?si=jvytE4WFLAHUKkte',
            },
            {
                'title': 'Watch YouTube Short #2',
                'description': 'Watch this short video completely and earn reward.',
                'task_type': 'youtube',
                'reward': 0.10,
                'time_required': 60,
                'url': 'https://youtube.com/shorts/QWnWrC7s0fg?si=p6gJ06l1NAnVDMXU',
            },
            {
                'title': 'Watch YouTube Short #3',
                'description': 'Watch this short video completely and earn reward.',
                'task_type': 'youtube',
                'reward': 0.10,
                'time_required': 60,
                'url': 'https://youtube.com/shorts/jst0n42tm7A?si=LB7kaLG_MDkro19r',
            },
            {
                'title': 'Watch YouTube Short #4',
                'description': 'Watch this short video completely and earn reward.',
                'task_type': 'youtube',
                'reward': 0.10,
                'time_required': 60,
                'url': 'https://youtube.com/shorts/RPRIxiumafc?si=S-EKges0V2zKnXUJ',
            },
            {
                'title': 'Watch YouTube Short #5',
                'description': 'Watch this short video completely and earn reward.',
                'task_type': 'youtube',
                'reward': 0.10,
                'time_required': 60,
                'url': 'https://youtube.com/shorts/NmqlmjilMGg?si=lg4vqmiJ__7swOAo',
            },
        ]

        for t in tasks:
            task, created = Task.objects.get_or_create(
                url=t['url'],
                defaults={
                    'title': t['title'],
                    'description': t['description'],
                    'task_type': t['task_type'],
                    'reward': t['reward'],
                    'time_required': t['time_required'],
                    'is_active': True,
                    'max_completions': 0,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created: {task.title}'))
            else:
                self.stdout.write(f'Already exists: {task.title}')

        self.stdout.write(self.style.SUCCESS('Done!'))
