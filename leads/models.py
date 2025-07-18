import uuid
from django.db import models
from django.conf import settings

class LeadTag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class LeadSourceAuditLog(models.Model):
    log_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey('LeadSource', on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action_type = models.CharField(max_length=50)  # e.g., "create", "update", "toggle", "reorder"
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action_type} by {self.user} on {self.timestamp}"

class LeadSource(models.Model):
    source_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order_no = models.IntegerField()
    is_default = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_lead_sources')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class LeadStatus(models.Model):
    status_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_lead_statuses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class LeadAssignmentLog(models.Model):
    ASSIGNMENT_METHOD_CHOICES = [
        ('manual', 'Manual'),
        ('auto', 'Auto'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey('Lead', on_delete=models.CASCADE, related_name='assignment_logs')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='lead_assignments_received')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='lead_assignments_given')
    assigned_at = models.DateTimeField(auto_now_add=True)
    method = models.CharField(max_length=10, choices=ASSIGNMENT_METHOD_CHOICES, default='manual')

    def __str__(self):
        return f"{self.lead.name} assigned to {self.assigned_to} by {self.assigned_by} ({self.method})"


class Lead(models.Model):
    lead_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    email = models.CharField(max_length=150, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    company = models.CharField(max_length=150, blank=True, null=True)
    source = models.ForeignKey(LeadSource, on_delete=models.SET_NULL, null=True)
    status = models.ForeignKey(LeadStatus, on_delete=models.SET_NULL, null=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='assigned_leads')
    assigned_at = models.DateTimeField(blank=True, null=True)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='lead_assignments_done')
    priority = models.CharField(max_length=20, blank=True, null=True)
    tags = models.ManyToManyField(LeadTag, related_name='leads', blank=True)
    custom_fields = models.JSONField(blank=True, null=True)
    archived = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_leads')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class LeadAssignment(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lead_assignments')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='assigned_leads_by_user')
    assigned_at = models.DateTimeField(auto_now_add=True)
    assignment_method = models.CharField(max_length=20, choices=[('manual', 'Manual'), ('auto', 'Auto')])
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.lead.name} assigned to {self.assigned_to}"


class LeadAuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('assign', 'Assign'),
        ('change_stage', 'Change Stage'),
        ('archive', 'Archive'),
        ('delete', 'Delete'),
    ]

    audit_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    old_values = models.JSONField(blank=True, null=True)
    new_values = models.JSONField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.lead.name} - {self.action} by {self.user}"

class LeadNote(models.Model):
    note_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey('Lead', on_delete=models.CASCADE, related_name='notes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Note by {self.user} on {self.lead.name}"


class LeadCallLog(models.Model):
    CALL_TYPE_CHOICES = [
        ('incoming', 'Incoming'),
        ('outgoing', 'Outgoing'),
    ]

    call_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey('Lead', on_delete=models.CASCADE, related_name='call_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    call_type = models.CharField(max_length=10, choices=CALL_TYPE_CHOICES)
    duration = models.IntegerField(help_text="Duration in seconds", null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    recording_url = models.URLField(blank=True, null=True)  # future-proof
    external_id = models.CharField(max_length=150, blank=True, null=True)  # For Twilio/Exotel SID
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.call_type.title()} call for {self.lead.name}"

class LeadEmailLog(models.Model):
    email_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey('Lead', on_delete=models.CASCADE, related_name='email_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Email to {self.lead.name} - {self.subject}"
    
class LeadStage(models.Model):
    STAGE_TYPE_CHOICES = [
        ('Open', 'Open'),
        ('Won', 'Won'),
        ('Lost', 'Lost'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=10, choices=STAGE_TYPE_CHOICES)
    order_no = models.IntegerField(unique=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    color_code = models.CharField(max_length=10, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_stages'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order_no']

    def __str__(self):
        return self.name
    
class LeadStageLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('status_toggle', 'Status Toggle'),
        ('reorder', 'Reorder'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stage = models.ForeignKey(LeadStage, on_delete=models.CASCADE, related_name='logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    old_values = models.JSONField(blank=True, null=True)
    new_values = models.JSONField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action_type} on {self.stage.name} by {self.user}"
