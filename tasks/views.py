from datetime import date
from django.shortcuts import render
from time import localtime, timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import permissions, status
from django.db.models import Q
from leads.models import Lead
from .serializers import FollowUpSerializer, LeadTaskSerializer
from .models import FollowUp, Tasks
from .utils import CustomUserPagination, paginate_and_format_response,log_task_action

class LeadTaskCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, lead_id):
        try:
            lead = Lead.objects.get(lead_id=lead_id)
        except Lead.DoesNotExist:
            return Response({
                "status": "failure",
                "data": {},
                "message": "Lead not found"
            }, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        data['lead'] = str(lead.lead_id)
        serializer = LeadTaskSerializer(data=data)
        if serializer.is_valid():
            task_obj = serializer.save(created_by=request.user)
            log_task_action(task=task_obj, user=request.user, action='create', new_data=serializer.data)
            return Response({
                "status": "success",
                "data": serializer.data,
                "message": "Task created successfully"
            }, status=status.HTTP_201_CREATED)
        return Response({
            "status": "failure",
            "data": serializer.errors,
            "message": "Invalid data"
        }, status=status.HTTP_400_BAD_REQUEST)

class LeadTaskListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, lead_id):
            tasks = Tasks.objects.filter(lead__lead_id=lead_id).order_by('-updated_at')
            paginated_data, _ = paginate_and_format_response(tasks, request, CustomUserPagination)
            serializer = LeadTaskSerializer(paginated_data['Details'], many=True)
            paginated_data['Details'] = serializer.data
            return Response({
                "status": "success",
                "data": paginated_data,
                "message": "Lead tasks fetched successfully"
            }, status=status.HTTP_200_OK)

class LeadTaskUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, task_id):
        try:
            task = Tasks.objects.get(task_id=task_id)
            old_data = LeadTaskSerializer(task).data
        except Tasks.DoesNotExist:
            return Response({
                "status": "failure",
                "data": {},
                "message": "Task not found"
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = LeadTaskSerializer(task, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            log_task_action(task=task, user=request.user, action='update', old_data=old_data, new_data=serializer.data)
            return Response({
                "status": "success",
                "data": serializer.data,
                "message": "Task updated successfully"
            }, status=status.HTTP_200_OK)

        return Response({
            "status": "failure",
            "data": serializer.errors,
            "message": "Invalid data"
        }, status=status.HTTP_400_BAD_REQUEST)

class LeadTaskDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, task_id):
        try:
            task = Tasks.objects.get(task_id=task_id)
        except Tasks.DoesNotExist:
            return Response({
                "status": "failure",
                "data": {},
                "message": "Task not found"
            }, status=status.HTTP_404_NOT_FOUND)

        task.delete()
        log_task_action(task=task, user=request.user, action='delete')
        return Response({
            "status": "success",
            "data": {},
            "message": "Task deleted successfully"
        }, status=status.HTTP_200_OK)

class GlobalTaskListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tasks = Tasks.objects.filter(is_deleted=False)

        # Filtering
        status_filter = request.GET.get('status')
        priority = request.GET.get('priority')
        assigned_to = request.GET.get('assigned_to')
        due_from = request.GET.get('due_date_from')
        due_to = request.GET.get('due_date_to')
        search = request.GET.get('search')

        if status_filter:
            if status_filter == "pending":
                tasks = tasks.filter(completed=False)
            elif status_filter == "completed":
                tasks = tasks.filter(completed=True)

        if priority:
            tasks = tasks.filter(priority__iexact=priority)

        if assigned_to:
            tasks = tasks.filter(assigned_to_id=assigned_to)

        if due_from and due_to:
            tasks = tasks.filter(due_date__range=[due_from, due_to])
        elif due_from:
            tasks = tasks.filter(due_date__gte=due_from)
        elif due_to:
            tasks = tasks.filter(due_date__lte=due_to)

        if search:
            tasks = tasks.filter(
                Q(title__icontains=search) |
                Q(lead__name__icontains=search)
            )

        tasks = tasks.order_by('-updated_at')
        paginated_data, _ = paginate_and_format_response(tasks, request, CustomUserPagination)
        serializer = LeadTaskSerializer(paginated_data['Details'], many=True)
        paginated_data['Details'] = serializer.data

        return Response({
            "status": "success",
            "data": paginated_data,
            "message": "Tasks fetched successfully"
        }, status=status.HTTP_200_OK)

class TaskStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, task_id):
        try:
            task = Tasks.objects.get(task_id=task_id, is_deleted=False)
        except Tasks.DoesNotExist:
            return Response({
                "status": "failure",
                "data": {},
                "message": "Task not found"
            }, status=status.HTTP_404_NOT_FOUND)

        if task.completed:
            return Response({
                "status": "failure",
                "data": {},
                "message": "Task is already marked as completed"
            }, status=status.HTTP_400_BAD_REQUEST)

        task.completed = True
        task.completed_at = timezone.now()
        task.completed_by = request.user
        task.completion_remarks = request.data.get("completion_remarks", "")
        task.save()

        serializer = LeadTaskSerializer(task)
        log_task_action(task=task, user=request.user, action='complete', notes=request.data.get('remarks'))
        return Response({
            "status": "success",
            "data": serializer.data,
            "message": "Task marked as completed"
        }, status=status.HTTP_200_OK)

class TaskSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.GET.get('q', '').strip()
        user = request.user
        tasks = Tasks.objects.filter(is_deleted=False)

        # Restrict to current user's tasks unless Admin
        if user.role != "Admin":
            tasks = tasks.filter(assigned_to=user)

        # Search keywords
        if query:
            tasks = tasks.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(lead__name__icontains=query)
            )

        # Optional filters
        if request.GET.get('priority'):
            tasks = tasks.filter(priority__iexact=request.GET.get('priority'))
        if request.GET.get('assigned_to') and user.role == "Admin":
            tasks = tasks.filter(assigned_to_id=request.GET.get('assigned_to'))

        status_filter = request.GET.get('status')
        if status_filter == 'pending':
            tasks = tasks.filter(completed=False)
        elif status_filter == 'completed':
            tasks = tasks.filter(completed=True)

        due_from = request.GET.get('due_date_from')
        due_to = request.GET.get('due_date_to')
        if due_from and due_to:
            tasks = tasks.filter(due_date__range=[due_from, due_to])
        elif due_from:
            tasks = tasks.filter(due_date__gte=due_from)
        elif due_to:
            tasks = tasks.filter(due_date__lte=due_to)

        tasks = tasks.order_by('-created_at')
        paginated_data, _ = paginate_and_format_response(tasks, request, CustomUserPagination)
        serializer = LeadTaskSerializer(paginated_data['Details'], many=True)
        paginated_data['Details'] = serializer.data

        return Response({
            "status": "success",
            "data": paginated_data,
            "message": "Task search results"
        }, status=status.HTTP_200_OK)

class TaskDashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = date.today()

        base_queryset = Tasks.objects.filter(is_deleted=False, assigned_to=user, completed=False)

        data = {
            "today": base_queryset.filter(due_date=today).count(),
            "overdue": base_queryset.filter(due_date__lt=today).count(),
            "upcoming": base_queryset.filter(due_date__gt=today).count()
        }

        return Response({
            "status": "success",
            "data": data,
            "message": "Task summary counts fetched successfully"
        })

class FollowUpCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = FollowUpSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response({
                "status": "success",
                "data": serializer.data,
                "message": "Follow-up scheduled successfully"
            }, status=status.HTTP_201_CREATED)
        return Response({
            "status": "failure",
            "data": serializer.errors,
            "message": "Invalid follow-up data"
        }, status=status.HTTP_400_BAD_REQUEST)

class FollowUpListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = FollowUp.objects.filter(is_deleted=False)

        # Filters
        status_filter = request.GET.get('status')
        assigned_to = request.GET.get('assigned_to')
        followup_type = request.GET.get('type')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        search = request.GET.get('search')

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)
        if followup_type:
            queryset = queryset.filter(type=followup_type)
        if date_from and date_to:
            queryset = queryset.filter(date_time__range=[date_from, date_to])
        elif date_from:
            queryset = queryset.filter(date_time__gte=date_from)
        elif date_to:
            queryset = queryset.filter(date_time__lte=date_to)
        if search:
            queryset = queryset.filter(
                Q(notes__icontains=search) |
                Q(lead__name__icontains=search)
            )

        queryset = queryset.order_by('-date_time')
        paginated, _ = paginate_and_format_response(queryset, request, CustomUserPagination)
        serializer = FollowUpSerializer(paginated["Details"], many=True)
        paginated["Details"] = serializer.data

        return Response({
            "status": "success",
            "data": paginated,
            "message": "Follow-ups fetched successfully"
        }, status=status.HTTP_200_OK)

class FollowUpUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, followup_id):
        try:
            followup = FollowUp.objects.get(id=followup_id, is_deleted=False)
        except FollowUp.DoesNotExist:
            return Response({
                "status": "failure",
                "data": {},
                "message": "Follow-up not found"
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = FollowUpSerializer(followup, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "status": "success",
                "data": serializer.data,
                "message": "Follow-up updated successfully"
            }, status=status.HTTP_200_OK)

        return Response({
            "status": "failure",
            "data": serializer.errors,
            "message": "Invalid data"
        }, status=status.HTTP_400_BAD_REQUEST)

class FollowUpStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, followup_id):
        try:
            followup = FollowUp.objects.get(id=followup_id, is_deleted=False)
        except FollowUp.DoesNotExist:
            return Response({
                "status": "failure",
                "data": {},
                "message": "Follow-up not found"
            }, status=status.HTTP_404_NOT_FOUND)

        status_value = request.data.get('status')
        notes = request.data.get('completion_notes', '')

        if status_value not in ['completed', 'rescheduled']:
            return Response({
                "status": "failure",
                "data": {},
                "message": "Invalid status value"
            }, status=status.HTTP_400_BAD_REQUEST)

        followup.status = status_value
        followup.completed_by = request.user
        followup.completed_at = timezone.now()
        followup.completion_notes = notes
        followup.save()

        serializer = FollowUpSerializer(followup)
        return Response({
            "status": "success",
            "data": serializer.data,
            "message": f"Follow-up marked as {status_value}"
        }, status=status.HTTP_200_OK)


class FollowUpDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, followup_id):
        try:
            followup = FollowUp.objects.get(id=followup_id, is_deleted=False)
        except FollowUp.DoesNotExist:
            return Response({
                "status": "failure",
                "data": {},
                "message": "Follow-up not found"
            }, status=status.HTTP_404_NOT_FOUND)

        followup.is_deleted = True
        followup.save()

        return Response({
            "status": "success",
            "data": {},
            "message": "Follow-up deleted successfully"
        }, status=status.HTTP_200_OK)
