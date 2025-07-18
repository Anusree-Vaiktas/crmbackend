from rest_framework.pagination import PageNumberPagination
from leads.models import LeadAuditLog, LeadStageLog

class CustomUserPagination(PageNumberPagination):
    page_size = None
    page_size_query_param = 'page_size'

    def get_next_page_number(self, page):
        return page.next_page_number() if page.has_next() else None

    def get_previous_page_number(self, page):
        return page.previous_page_number() if page.has_previous() else None

def paginate_and_format_response(paginated_data, request, pagination_class):
    paginator = pagination_class()
    page = paginator.paginate_queryset(paginated_data, request)

    if page is not None:
        page_size = int(request.query_params.get('page_size', paginator.page_size))
        return {
            'total': paginator.page.paginator.count,
            'page': paginator.page.number,
            'page_size': page_size,
            'next_page': paginator.get_next_page_number(paginator.page),
            'previous_page': paginator.get_previous_page_number(paginator.page),
            'Details': page
        }, None

    return {
        'total': len(paginated_data),
        'page': 1,
        'page_size': len(paginated_data),
        'next_page': None,
        'previous_page': None,
        'Details': paginated_data
    }, None


def log_read_action(user, action_type, metadata):
    LeadAuditLog.objects.create(
        user=user,
        lead=None,  # No specific lead associated with search/filter
        action=action_type,
        old_values=None,
        new_values=metadata  # Store search/filter/sort params
    )


def log_lead_stage_action(user, stage, action_type, old_values=None, new_values=None):
    """
    Logs create, update, status toggle, or reorder actions on a LeadStage.

    Args:
        user: User instance who performed the action.
        stage: LeadStage instance.
        action_type: One of ['create', 'update', 'status_toggle', 'reorder'].
        old_values (dict): Previous state of the stage.
        new_values (dict): New state of the stage.
    """
    if action_type not in dict(LeadStageLog.ACTION_CHOICES):
        raise ValueError("Invalid action_type for LeadStageLog")

    LeadStageLog.objects.create(
        stage=stage,
        user=user,
        action_type=action_type,
        old_values=old_values or {},
        new_values=new_values or {}
    )
