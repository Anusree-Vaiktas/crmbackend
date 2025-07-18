from django.urls import path
from .views import GlobalTaskListView, LeadTaskCreateView, LeadTaskDeleteView, LeadTaskListView, LeadTaskUpdateView, TaskDashboardSummaryView, TaskSearchView, TaskStatusUpdateView
from .views import FollowUpCreateView,FollowUpListView,FollowUpUpdateView,FollowUpStatusUpdateView,FollowUpDeleteView

urlpatterns = [
    path('leads/<uuid:lead_id>/tasks/', LeadTaskListView.as_view(), name='lead-task-list'),
    path('leads/<uuid:lead_id>/tasks/create/', LeadTaskCreateView.as_view(), name='lead-task-create'),
    path('leads/tasks/<uuid:task_id>/update/', LeadTaskUpdateView.as_view(), name='lead-task-update'),
    path('leads/tasks/<uuid:task_id>/delete/', LeadTaskDeleteView.as_view(), name='lead-task-delete'),
    path('tasks/', GlobalTaskListView.as_view(), name='global-task-list'),
    path('tasks/<uuid:task_id>/status/', TaskStatusUpdateView.as_view(), name='update-task-status'),
    path('tasks/search/', TaskSearchView.as_view(), name='task-search'),
    path('tasks/dashboard-summary/', TaskDashboardSummaryView.as_view(), name='task-dashboard-summary'),
    path('api/followups/', FollowUpListView.as_view(), name='followup-list'),
    path('api/followups/', FollowUpCreateView.as_view(), name='followup-create'),
    path('api/followups/<uuid:followup_id>/', FollowUpUpdateView.as_view(), name='followup-update'),
    path('api/followups/<uuid:followup_id>/status/', FollowUpStatusUpdateView.as_view(), name='followup-status-update'),
    path('api/followups/<uuid:followup_id>/', FollowUpDeleteView.as_view(), name='followup-delete'),
]

