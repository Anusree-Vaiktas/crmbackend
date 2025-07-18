from rest_framework import serializers
from .models import Tasks
from leads.models import Lead
from django.contrib.auth import get_user_model
from users.models import User
from .models import FollowUp
User = get_user_model()

class LeadSerializer(serializers.ModelSerializer):

    class Meta:
        model = Lead
        fields = '__all__'

class LeadTaskSerializer(serializers.ModelSerializer):
    assigned_to = serializers.StringRelatedField()
    created_by = serializers.StringRelatedField()

    class Meta:
        model = Tasks
        fields = [
            'task_id','lead','title','description','assigned_to','due_date', 'completed','created_by','created_at','updated_at']
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class FollowUpSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source='lead.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.name', read_only=True)

    class Meta:
        model = FollowUp
        fields = [
            'id', 'lead', 'lead_name', 'assigned_to', 'assigned_to_name',
            'date_time', 'type', 'status', 'notes', 'summary',
            'created_by', 'updated_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['status', 'created_by', 'updated_by', 'created_at', 'updated_at', 'lead_name', 'assigned_to_name']
