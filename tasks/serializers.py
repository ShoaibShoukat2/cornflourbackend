from rest_framework import serializers
from .models import Task, UserTask, DailyLoginBonus, PromoCode

class TaskSerializer(serializers.ModelSerializer):
    is_completed = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'task_type', 'reward', 'time_required', 'url', 'is_active', 'is_completed']
    
    def get_is_completed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return UserTask.objects.filter(user=request.user, task=obj, status='verified').exists()
        return False

class UserTaskSerializer(serializers.ModelSerializer):
    task = TaskSerializer(read_only=True)
    
    class Meta:
        model = UserTask
        fields = ['id', 'task', 'status', 'started_at', 'completed_at']

class StartTaskSerializer(serializers.Serializer):
    task_id = serializers.IntegerField()

class CompleteTaskSerializer(serializers.Serializer):
    task_id = serializers.IntegerField()
    verification_input = serializers.CharField(required=False, allow_blank=True)

class PromoCodeSerializer(serializers.Serializer):
    code = serializers.CharField()
