from rest_framework import serializers
from .models import Lead, LeadAssignmentLog, LeadCallLog, LeadEmailLog, LeadSource, LeadSourceAuditLog, LeadStatus, LeadAssignment, LeadAuditLog, LeadTag, LeadNote
from .models import LeadStage, LeadStageLog
from django.contrib.auth import get_user_model
from users.models import User
User = get_user_model()

class LeadSourceAuditLogSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = LeadSourceAuditLog
        fields = ['log_id', 'source', 'user', 'action_type', 'old_value', 'new_value', 'timestamp']

class LeadSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadSource
        fields = '__all__'

class LeadStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadStatus
        fields = '__all__'


class UserMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email']

class LeadListSerializer(serializers.ModelSerializer):
    source = LeadSourceSerializer(read_only=True)
    status = LeadStatusSerializer(read_only=True)
    assigned_to = UserMinimalSerializer(read_only=True)
    created_by = UserMinimalSerializer(read_only=True)

    class Meta:
        model = Lead
        fields = '__all__'

class LeadAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadAssignment
        fields = '__all__'

class LeadBulkActionSerializer(serializers.Serializer):
    lead_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False
    )
    action = serializers.ChoiceField(choices=['assign', 'change_stage', 'delete', 'archive'])
    # Optional fields based on action type
    assigned_to = serializers.UUIDField(required=False)
    status_id = serializers.UUIDField(required=False)

class LeadAuditLogSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    lead = serializers.StringRelatedField()

    class Meta:
        model = LeadAuditLog
        fields = ['audit_id','lead','user','action','old_values','new_values','timestamp']

class LeadDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = '__all__'
        read_only_fields = ['lead_id', 'created_by', 'created_at', 'updated_at']

class LeadTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadTag
        fields = ['id', 'name']

class LeadNoteSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = LeadNote
        fields = ['note_id', 'user', 'content', 'created_at']
        read_only_fields = ['note_id', 'user', 'created_at']

class LeadNoteUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadNote
        fields = ['content']

class LeadSerializer(serializers.ModelSerializer):
    tags = LeadTagSerializer(many=True, required=False)
    notes = LeadNoteSerializer(many=True, read_only=True)

    class Meta:
        model = Lead
        fields = [
            'id', 'name', 'email', 'phone', 'company',
            'source', 'status', 'assigned_to', 'priority',
            'tags', 'notes', 'created_by', 'created_at', 'updated_at'
        ]

    def create(self, validated_data):
        tags_data = validated_data.pop('tags', [])
        lead = Lead.objects.create(**validated_data)
        for tag in tags_data:
            tag_obj, _ = LeadTag.objects.get_or_create(name=tag['name'])
            lead.tags.add(tag_obj)
        return lead

    def update(self, instance, validated_data):
        tags_data = validated_data.pop('tags', None)
        if tags_data is not None:
            instance.tags.clear()
            for tag in tags_data:
                tag_obj, _ = LeadTag.objects.get_or_create(name=tag['name'])
                instance.tags.add(tag_obj)
        return super().update(instance, validated_data)

class LeadCallLogSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = LeadCallLog
        fields = [
            'call_id', 'lead', 'user', 'call_type',
            'duration', 'notes', 'recording_url', 'external_id',
            'created_at'
        ]
        read_only_fields = ['call_id', 'user', 'recording_url', 'external_id', 'created_at']

class LeadEmailLogSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = LeadEmailLog
        fields = ['email_id', 'lead', 'user', 'subject', 'body', 'sent_at']
        read_only_fields = ['email_id', 'user', 'sent_at']

class TimelineEntrySerializer(serializers.Serializer):
    type = serializers.CharField()
    timestamp = serializers.DateTimeField()
    user = serializers.CharField()
    description = serializers.CharField()
    metadata = serializers.JSONField()

class LeadStageSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)  # shows name or email

    class Meta:
        model = LeadStage
        fields = [
            'id', 'name', 'type', 'order_no', 'is_active', 'is_default',
            'color_code', 'description', 'created_by', 'created_at', 'updated_at'
        ]

class LeadStageCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadStage
        fields = [
            'name', 'type', 'order_no', 'is_active', 'is_default',
            'color_code', 'description'
        ]

    def validate(self, data):
        if data.get("is_default", False):
            existing_default = LeadStage.objects.filter(is_default=True)
            if self.instance:
                existing_default = existing_default.exclude(id=self.instance.id)
            if existing_default.exists():
                raise serializers.ValidationError("Only one default stage is allowed.")
        return data

    def create(self, validated_data):
        if validated_data.get("is_default", False):
            LeadStage.objects.filter(is_default=True).update(is_default=False)
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get("is_default", False):
            LeadStage.objects.filter(is_default=True).exclude(id=instance.id).update(is_default=False)
        return super().update(instance, validated_data)

class LeadStageLogSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    stage = serializers.StringRelatedField()

    class Meta:
        model = LeadStageLog
        fields = ['id', 'stage', 'user', 'action_type', 'old_values', 'new_values', 'timestamp']


class LeadAssignmentLogSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source='lead.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.name', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.name', read_only=True)

    class Meta:
        model = LeadAssignmentLog
        fields = [
            'id', 'lead', 'lead_name',
            'assigned_to', 'assigned_to_name',
            'assigned_by', 'assigned_by_name',
            'assigned_at', 'method'
        ]
        read_only_fields = ['assigned_at', 'method']

