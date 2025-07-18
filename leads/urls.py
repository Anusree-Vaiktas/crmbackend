from django.urls import path
from .views import LeadAssignmentLogView, LeadAuditLogListView, LeadBulkActionView, LeadCallLogView, LeadDeleteView
from .views import LeadNotesListView, LeadRetrieveView, LeadSearchView, LeadFilterView, LeadUpdateView,AddLeadNoteView
from .views import LeadNoteUpdateView
from .views import LeadStageListView,LeadStageCreateView,LeadStageUpdateView,LeadStageStatusToggleView,LeadStageReorderView
from .views import LeadEmailLogListView, LeadFullTimelineView, LeadListView, LeadNoteCreateView, LeadNoteDeleteView
from .views import LeadSourceListCreateView, LeadSourceReorderView, LeadSourceUpdateToggleView, ManualLeadAssignView, SalesUserListView, UnassignedLeadsListView


urlpatterns = [
    path('leads/', LeadListView.as_view(), name='lead-list-all'),
    path('leads/search/', LeadSearchView.as_view(), name='lead-search'),
    path('leads/filter/', LeadFilterView.as_view(), name='lead-filter'),
    path('leads/unassigned/', UnassignedLeadsListView.as_view(), name='unassigned-leads'),
    path('leads/bulk-action/', LeadBulkActionView.as_view(), name='lead-bulk-action'),
    path('leads/<uuid:lead_id>/', LeadRetrieveView.as_view(), name='lead-detail'),
    path('leads/<uuid:lead_id>/update/', LeadUpdateView.as_view(), name='lead-update'),
    path('leads/<uuid:lead_id>/delete/', LeadDeleteView.as_view(), name='lead-delete'),
    path('leads/<uuid:lead_id>/audit-logs/', LeadAuditLogListView.as_view(), name='lead-audit-logs'),
    path('leads/<uuid:lead_id>/notes/', LeadNoteCreateView.as_view(), name='lead-note-create'),
    path('leads/<uuid:lead_id>/add-note/', AddLeadNoteView.as_view(), name='add-lead-note'),
    path('leads/<uuid:lead_id>/notes/', LeadNotesListView.as_view(), name='lead-notes-list'),
    path('notes/<uuid:note_id>/update/', LeadNoteUpdateView.as_view(), name='lead-note-update'),
    path('notes/<uuid:note_id>/delete/', LeadNoteDeleteView.as_view(), name='lead-note-delete'),
    path('leads/<uuid:lead_id>/call-logs/', LeadCallLogView.as_view(), name='lead-call-logs'),
    path('leads/<uuid:lead_id>/email-logs/', LeadEmailLogListView.as_view(), name='lead-email-logs'),
    path('leads/<uuid:lead_id>/full-timeline/', LeadFullTimelineView.as_view()),
    path('lead-sources/', LeadSourceListCreateView.as_view()),
    path('lead-sources/<uuid:pk>/', LeadSourceUpdateToggleView.as_view()),
    path('lead-sources/reorder/', LeadSourceReorderView.as_view()),
    path('lead-stages/', LeadStageListView.as_view(), name='lead-stage-list'),
    path('lead-stages/create/', LeadStageCreateView.as_view(), name='lead-stage-create'),
    path('lead-stages/<uuid:stage_id>/update/', LeadStageUpdateView.as_view(), name='lead-stage-update'),
    path('lead-stages/<uuid:stage_id>/toggle/', LeadStageStatusToggleView.as_view(), name='lead-stage-toggle'),
    path('lead-stages/reorder/', LeadStageReorderView.as_view(), name='lead-stage-reorder'),
    path("leads/<uuid:lead_id>/assignment-logs/", LeadAssignmentLogView.as_view(), name="lead-assignment-logs"),
    path("users/sales/", SalesUserListView.as_view(), name="sales-user-list"),
    path('leads/assign/', ManualLeadAssignView.as_view(), name='manual-lead-assign'),
]

