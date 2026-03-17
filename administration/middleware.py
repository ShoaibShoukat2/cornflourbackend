from django.utils.deprecation import MiddlewareMixin
from .models import IPTracking, FraudDetection
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.utils import timezone

User = get_user_model()

class SecurityMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            ip_address = self.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Track IP
            IPTracking.objects.create(
                user=request.user,
                ip_address=ip_address,
                user_agent=user_agent,
                action=request.path
            )
            
            # Check for multiple accounts from same IP
            self.check_multiple_accounts(request.user, ip_address)
            
            # Check for rapid task completion
            if 'tasks/complete' in request.path:
                self.check_rapid_tasks(request.user)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def check_multiple_accounts(self, user, ip_address):
        # Check if multiple users are using same IP
        recent_ips = IPTracking.objects.filter(
            ip_address=ip_address,
            created_at__gte=timezone.now() - timedelta(days=7)
        ).values_list('user_id', flat=True).distinct()
        
        if len(set(recent_ips)) > 3:  # More than 3 users from same IP
            FraudDetection.objects.get_or_create(
                user=user,
                fraud_type='same_ip',
                defaults={
                    'description': f'Multiple accounts detected from IP: {ip_address}',
                    'severity': 'high'
                }
            )
    
    def check_rapid_tasks(self, user):
        from tasks.models import UserTask
        
        # Check if user completed more than 10 tasks in last 5 minutes
        recent_tasks = UserTask.objects.filter(
            user=user,
            completed_at__gte=timezone.now() - timedelta(minutes=5),
            status='verified'
        ).count()
        
        if recent_tasks > 10:
            FraudDetection.objects.get_or_create(
                user=user,
                fraud_type='rapid_tasks',
                defaults={
                    'description': f'Completed {recent_tasks} tasks in 5 minutes',
                    'severity': 'critical'
                }
            )
