from time import localtime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import permissions, status
from django.db.models import Q
from .serializers import LeadAssignmentLogSerializer, LeadAuditLogSerializer, LeadCallLogSerializer, LeadEmailLogSerializer, LeadListSerializer,LeadBulkActionSerializer, LeadSerializer, LeadSourceSerializer, LeadStageCreateUpdateSerializer, LeadStageSerializer
from .utils import CustomUserPagination, log_lead_stage_action, paginate_and_format_response, log_read_action
from django.utils import timezone
from django.contrib.auth import get_user_model
from users.models import User
from tasks.models import Tasks

from users.serializers import SimpleUserSerializer
from .models import Lead, LeadAssignment, LeadAssignmentLog, LeadCallLog, LeadEmailLog, LeadSource, LeadSourceAuditLog, LeadStage, LeadStatus, LeadAuditLog, LeadNote
from django.shortcuts import get_object_or_404
from .serializers import LeadDetailSerializer, LeadNoteSerializer, LeadNoteUpdateSerializer
User = get_user_model()

ALLOWED_SORT_FIELDS = {
    'name': 'name',
    'email': 'email',
    'phone': 'phone',
    'created_at': 'created_at',
    'updated_at': 'updated_at',
    'status': 'status_id',
    'source': 'source_id',
    'assigned_to': 'assigned_to'
}

class UnassignedLeadsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        leads = Lead.objects.filter(assigned_to__isnull=True, is_deleted=False).order_by('-created_at')
        paginated, _ = paginate_and_format_response(leads, request, CustomUserPagination)
        serializer = LeadSerializer(paginated["Details"], many=True)
        paginated["Details"] = serializer.data

        return Response({
            "status": "success",
            "data": paginated,
            "message": "Unassigned leads fetched successfully"
        }, status=status.HTTP_200_OK)
    
class LeadListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = Lead.objects.filter(is_deleted=False)
        sort_by = request.query_params.get('sortBy')
        sort_order = request.query_params.get('sortOrder', 'asc')
        if sort_by in ALLOWED_SORT_FIELDS:
            sort_field = ALLOWED_SORT_FIELDS[sort_by]
            if sort_order == 'desc':
                sort_field = f'-{sort_field}'
            queryset = queryset.order_by(sort_field)
        else:
            queryset = queryset.order_by('-created_at')

        paginated_data, _ = paginate_and_format_response(queryset, request, CustomUserPagination)
        serializer = LeadListSerializer(paginated_data['Details'], many=True)
        paginated_data['Details'] = serializer.data
        
        return Response({
            "status": "success",
            "data": paginated_data,
            "message": "Lead list retrieved successfully."
        }, status=status.HTTP_200_OK)


class LeadFilterView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = Lead.objects.filter(is_deleted=False)
        source_ids = request.query_params.getlist('sourceIds[]')
        status_ids = request.query_params.getlist('statusIds[]')
        assigned_to_ids = request.query_params.getlist('assignedToIds[]')
        date_from = request.query_params.get('dateFrom')
        date_to = request.query_params.get('dateTo')
        tag_ids = request.query_params.getlist('tagIds[]')
        if tag_ids:
            leads = leads.filter(tags__id__in=tag_ids).distinct()
        if source_ids:
            queryset = queryset.filter(source_id__in=source_ids)
        if status_ids:
            queryset = queryset.filter(status_id__in=status_ids)
        if assigned_to_ids:
            queryset = queryset.filter(assigned_to__in=assigned_to_ids)
        if date_from and date_to:
            queryset = queryset.filter(created_at__date__range=[date_from, date_to])

        # Sort
        sort_by = request.query_params.get('sortBy')
        sort_order = request.query_params.get('sortOrder', 'asc')
        if sort_by in ALLOWED_SORT_FIELDS:
            sort_field = ALLOWED_SORT_FIELDS[sort_by]
            if sort_order == 'desc':
                sort_field = f'-{sort_field}'
            queryset = queryset.order_by(sort_field)
        else:
            queryset = queryset.order_by('-created_at')

        paginated_data, _ = paginate_and_format_response(queryset, request, CustomUserPagination)
        serializer = LeadListSerializer(paginated_data['Details'], many=True)
        paginated_data['Details'] = serializer.data
        log_read_action(
            request.user,
            action_type="filter",
            metadata={
                "source": request.query_params.getlist("sourceIds[]"),
                "status": request.query_params.getlist("statusIds[]"),
                "assigned_to": request.query_params.getlist("assignedToIds[]"),
                "date_range": [request.query_params.get("dateFrom"), request.query_params.get("dateTo")],
                "tag_ids": request.query_params.getlist("tagIds[]"),
            }
        )

        return Response({
            "status": "success",
            "data": paginated_data,
            "message": "Filtered lead list retrieved successfully."
        }, status=status.HTTP_200_OK)


class LeadSearchView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        search = request.query_params.get('search', '')
        queryset = Lead.objects.select_related('source', 'status', 'assigned_to', 'created_by')

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search)
            ).order_by('-created_at')
        else:
            queryset = queryset.none()

        paginated_data, _ = paginate_and_format_response(
            queryset, request, CustomUserPagination
        )
        serializer = LeadListSerializer(paginated_data['Details'], many=True)
        paginated_data['Details'] = serializer.data
        log_read_action(
            request.user,
            action_type="search",
            metadata={"term": search}
        )
        return Response({
            "status": "success",
            "data": paginated_data,
            "message": "Search results retrieved successfully"
        })

class LeadBulkActionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = LeadBulkActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "status": "failure",
                "data": {},
                "message": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        lead_ids = data['lead_ids']
        action = data['action']
        user = request.user

        leads = Lead.objects.filter(lead_id__in=lead_ids, is_deleted=False)

        if not leads.exists():
            return Response({
                "status": "failure",
                "data": {},
                "message": "No matching leads found."
            }, status=status.HTTP_404_NOT_FOUND)

        if action == 'assign':
            assigned_to_id = data.get('assigned_to')
            try:
                assigned_user = User.objects.get(id=assigned_to_id)
            except User.DoesNotExist:
                return Response({
                    "status": "failure",
                    "data": {},
                    "message": "Assigned user not found."
                }, status=status.HTTP_404_NOT_FOUND)

            for lead in leads:
                LeadAuditLog.objects.create(
                    lead=lead,
                    user=user,
                    action='assign',
                    old_values={'assigned_to': str(lead.assigned_to)},
                    new_values={'assigned_to': str(assigned_user)}
                )
                LeadAssignment.objects.create(
                    lead=lead,
                    assigned_to=assigned_user,
                    assigned_by=user,
                    assigned_at=timezone.now(),
                    assignment_method='manual',
                    is_active=True
                )
                lead.assigned_to = assigned_user
                lead.save()

        elif action == 'change_stage':
            status_id = data.get('status_id')
            try:
                status_obj = LeadStatus.objects.get(status_id=status_id)
            except LeadStatus.DoesNotExist:
                return Response({
                    "status": "failure",
                    "data": {},
                    "message": "Status not found."
                }, status=status.HTTP_404_NOT_FOUND)

            for lead in leads:
                LeadAuditLog.objects.create(
                    lead=lead,
                    user=user,
                    action='change_stage',
                    old_values={'status': str(lead.status)},
                    new_values={'status': str(status_obj)}
                )
            leads.update(status=status_obj)

        elif action == 'delete':
            for lead in leads:
                LeadAuditLog.objects.create(
                    lead=lead,
                    user=user,
                    action='delete',
                    old_values={'is_deleted': lead.is_deleted},
                    new_values={'is_deleted': True}
                )
            leads.update(is_deleted=True)

        elif action == 'archive':
            for lead in leads:
                LeadAuditLog.objects.create(
                    lead=lead,
                    user=user,
                    action='archive',
                    old_values={'archived': lead.archived},
                    new_values={'archived': True}
                )
            leads.update(archived=True)

        else:
            return Response({
                "status": "failure",
                "data": {},
                "message": "Unsupported action."
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "status": "success",
            "data": {},
            "message": f"{len(leads)} leads processed for '{action}' action."
        }, status=status.HTTP_200_OK)
    
class LeadRetrieveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, lead_id):
        lead = get_object_or_404(Lead, lead_id=lead_id, is_deleted=False)
        serializer = LeadDetailSerializer(lead)
        return Response({
            "status": "success",
            "data": serializer.data,
            "message": "Lead details retrieved successfully."
        })

class LeadUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, lead_id):
        lead = get_object_or_404(Lead, lead_id=lead_id, is_deleted=False)
        old_values = LeadDetailSerializer(lead).data

        serializer = LeadDetailSerializer(lead, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            new_values = serializer.data

            LeadAuditLog.objects.create(
                lead=lead,
                user=request.user,
                action='update',
                old_values=old_values,
                new_values=new_values
            )

            return Response({
                "status": "success",
                "data": serializer.data,
                "message": "Lead updated successfully."
            })

        return Response({
            "status": "failure",
            "data": {},
            "message": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class LeadDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, lead_id):
        lead = get_object_or_404(Lead, lead_id=lead_id, is_deleted=False)
        lead.is_deleted = True
        lead.save()

        LeadAuditLog.objects.create(
            lead=lead,
            user=request.user,
            action='delete',
            old_values={"is_deleted": False},
            new_values={"is_deleted": True}
        )

        return Response({
            "status": "success",
            "data": {},
            "message": "Lead soft deleted successfully."
        }, status=status.HTTP_200_OK)
    
class LeadAuditLogListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, lead_id):
        lead = get_object_or_404(Lead, lead_id=lead_id)

        logs = LeadAuditLog.objects.filter(lead=lead).order_by('-timestamp')
        serializer = LeadAuditLogSerializer(logs, many=True)

        return Response({
            "status": "success",
            "data": serializer.data,
            "message": "Audit logs retrieved successfully."
        }, status=status.HTTP_200_OK)
    
class AddLeadNoteView(APIView):
    serializer_class = LeadNoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, lead_id):
        try:
            lead = Lead.objects.get(lead_id=lead_id, is_deleted=False)
        except Lead.DoesNotExist:
            return Response({
                "status": "failure",
                "data": {},
                "message": "Lead not found."
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save(lead=lead, user=request.user)
            return Response({
                "status": "success",
                "data": serializer.data,
                "message": "Note added successfully."
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            "status": "failure",
            "data": serializer.errors,
            "message": "Invalid data."
        }, status=status.HTTP_400_BAD_REQUEST)
    
class LeadNotesListView(APIView):
    serializer_class = LeadNoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        lead_id = self.kwargs.get('lead_id')
        return LeadNote.objects.filter(lead__lead_id=lead_id).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        try:
            Lead.objects.get(lead_id=kwargs.get('lead_id'), is_deleted=False)
        except Lead.DoesNotExist:
            return Response({
                "status": "failure",
                "data": {},
                "message": "Lead not found."
            }, status=status.HTTP_404_NOT_FOUND)

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "status": "success",
            "data": serializer.data,
            "message": "Lead notes retrieved successfully."
        })
    
class LeadNoteUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, note_id):
        try:
            note = LeadNote.objects.get(note_id=note_id)
        except LeadNote.DoesNotExist:
            return Response({
                "status": "failure",
                "data": {},
                "message": "Note not found."
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = LeadNoteUpdateSerializer(note, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "status": "success",
                "data": serializer.data,
                "message": "Note updated successfully."
            })
        return Response({
            "status": "failure",
            "data": serializer.errors,
            "message": "Invalid data."
        }, status=status.HTTP_400_BAD_REQUEST)
    
class LeadNoteDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, note_id):
        try:
            note = LeadNote.objects.get(note_id=note_id)
            note.delete()
            return Response({
                "status": "success",
                "data": {},
                "message": "Note deleted successfully."
            })
        except LeadNote.DoesNotExist:
            return Response({
                "status": "failure",
                "data": {},
                "message": "Note not found."
            }, status=status.HTTP_404_NOT_FOUND)

class LeadNoteCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, lead_id):
        try:
            lead = Lead.objects.get(lead_id=lead_id, is_deleted=False)
        except Lead.DoesNotExist:
            return Response({
                "status": "failure",
                "data": {},
                "message": "Lead not found."
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = LeadNoteSerializer(data=request.data)
        if serializer.is_valid():
            note = serializer.save(lead=lead, user=request.user)
            return Response({
                "status": "success",
                "data": {
                    "note_id": note.note_id,
                    "content": note.content,
                    "user": str(note.user),
                    "created_at": note.created_at
                },
                "message": "Note added successfully."
            })
        return Response({
            "status": "failure",
            "data": serializer.errors,
            "message": "Invalid data."
        }, status=status.HTTP_400_BAD_REQUEST)

# class LeadTimelineView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request, lead_id):
#         logs = LeadAuditLog.objects.filter(lead_id=lead_id).order_by('-timestamp')
#         serializer = LeadAuditLogSerializer(logs, many=True)
#         return Response({
#             "status": "success",
#             "data": serializer.data,
#             "message": "Timeline fetched successfully"
#         }, status=status.HTTP_200_OK)


class LeadCallLogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lead_id):
        try:
            lead = Lead.objects.get(lead_id=lead_id, is_deleted=False)
        except Lead.DoesNotExist:
            return Response({
                "status": "failure",
                "data": {},
                "message": "Lead not found"
            }, status=status.HTTP_404_NOT_FOUND)

        call_logs = LeadCallLog.objects.filter(lead=lead).order_by('-created_at')
        paginated_data, _ = paginate_and_format_response(call_logs, request, CustomUserPagination)
        serializer = LeadCallLogSerializer(paginated_data['Details'], many=True)

        return Response({
            "status": "success",
            "data": {
                **paginated_data,
                "Details": serializer.data
            },
            "message": "Lead call logs fetched successfully"
        }, status=status.HTTP_200_OK)

    def post(self, request, lead_id):
        try:
            lead = Lead.objects.get(lead_id=lead_id, is_deleted=False)
        except Lead.DoesNotExist:
            return Response({
                "status": "failure",
                "data": {},
                "message": "Lead not found"
            }, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        data['lead'] = str(lead.lead_id)

        serializer = LeadCallLogSerializer(data=data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response({
                "status": "success",
                "data": serializer.data,
                "message": "Call log created successfully"
            }, status=status.HTTP_201_CREATED)

        return Response({
            "status": "failure",
            "data": serializer.errors,
            "message": "Validation error"
        }, status=status.HTTP_400_BAD_REQUEST)

class LeadEmailLogListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lead_id):
        try:
            lead = Lead.objects.get(lead_id=lead_id, is_deleted=False)
        except Lead.DoesNotExist:
            return Response({
                "status": "failure",
                "data": {},
                "message": "Lead not found."
            }, status=status.HTTP_404_NOT_FOUND)

        email_logs = LeadEmailLog.objects.filter(lead=lead).order_by('-sent_at')
        paginated_data, _ = paginate_and_format_response(email_logs, request, CustomUserPagination)
        serializer = LeadEmailLogSerializer(paginated_data['Details'], many=True)

        paginated_data['Details'] = serializer.data
        return Response({
            "status": "success",
            "data": paginated_data,
            "message": "Email logs fetched successfully."
        }, status=status.HTTP_200_OK)


class LeadFullTimelineView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lead_id):
        timeline = []

        # 1. Audit Logs
        audit_logs = LeadAuditLog.objects.filter(lead_id=lead_id)
        for log in audit_logs:
            timeline.append({
                "type": "audit",
                "timestamp": localtime(log.timestamp),
                "user": str(log.user) if log.user else "System",
                "description": f"{log.action} performed",
                "metadata": {
                    "old_values": log.old_values,
                    "new_values": log.new_values
                }
            })

        # 2. Notes
        from leads.models import LeadNote
        notes = LeadNote.objects.filter(lead_id=lead_id)
        for note in notes:
            timeline.append({
                "type": "note",
                "timestamp": localtime(note.created_at),
                "user": str(note.user) if note.user else "Unknown",
                "description": "Note added",
                "metadata": {
                    "content": note.content
                }
            })

        # 3. Tasks
        from tasks.models import Tasks  # Assuming model is Task
        tasks = Tasks.objects.filter(lead_id=lead_id)
        for task in tasks:
            timeline.append({
                "type": "task",
                "timestamp": localtime(task.created_at),
                "user": str(task.created_by) if task.created_by else "Unknown",
                "description": f"Task created: {task.title}",
                "metadata": {
                    "status": task.status,
                    "due_date": task.due_date
                }
            })

        # 4. Call Logs
        from leads.models import LeadCallLog
        calls = LeadCallLog.objects.filter(lead_id=lead_id)
        for call in calls:
            timeline.append({
                "type": "call",
                "timestamp": localtime(call.timestamp),
                "user": str(call.user) if call.user else "Unknown",
                "description": f"Call logged ({call.duration} mins)",
                "metadata": {
                    "notes": call.notes
                }
            })

        # 5. Email Logs (if model exists)
        try:
            from leads.models import LeadEmailLog
            emails = LeadEmailLog.objects.filter(lead_id=lead_id)
            for email in emails:
                timeline.append({
                    "type": "email",
                    "timestamp": localtime(email.sent_at),
                    "user": str(email.sent_by) if email.sent_by else "Unknown",
                    "description": f"Email sent: {email.subject}",
                    "metadata": {
                        "to": email.to,
                        "body": email.body
                    }
                })
        except ImportError:
            pass  # Handle later when implemented

        # Sort all by timestamp descending
        sorted_timeline = sorted(timeline, key=lambda x: x['timestamp'], reverse=True)

        return Response({
            "status": "success",
            "data": sorted_timeline,
            "message": "Full timeline fetched successfully"
        }, status=status.HTTP_200_OK)

class LeadSourceListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
            sources = LeadSource.objects.all().order_by('order')
            data, _ = paginate_and_format_response(sources, request, CustomUserPagination)
            serializer = LeadSourceSerializer(data['Details'], many=True)

            response_data = {
                "total": data["total"],
                "page": data["page"],
                "page_size": data["page_size"],
                "next_page": data["next_page"],
                "previous_page": data["previous_page"],
                "Details": serializer.data
            }

            return Response({
                "status": "success",
                "data": response_data,
                "message": "Lead sources fetched successfully"
            }, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = LeadSourceSerializer(data=request.data)
        if serializer.is_valid():
            source = serializer.save(created_by=request.user)

            # Audit log
            LeadSourceAuditLog.objects.create(
                source=source,
                user=request.user,
                action_type='create',
                old_value=None,
                new_value=serializer.data
            )

            return Response({
                "status": "success",
                "data": serializer.data,
                "message": "Lead source created successfully."
            }, status=status.HTTP_201_CREATED)

        return Response({
            "status": "failure",
            "data": serializer.errors,
            "message": "Lead source creation failed."
        }, status=status.HTTP_400_BAD_REQUEST)
    
class LeadSourceUpdateToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, pk):
        source = get_object_or_404(LeadSource, pk=pk)
        old_data = LeadSourceSerializer(source).data

        serializer = LeadSourceSerializer(source, data=request.data, partial=True)
        if serializer.is_valid():
            updated_source = serializer.save()

            LeadSourceAuditLog.objects.create(
                source=source,
                user=request.user,
                action_type='update',
                old_value=old_data,
                new_value=serializer.data
            )

            return Response({
                "status": "success",
                "data": serializer.data,
                "message": "Lead source updated successfully."
            })

        return Response({
            "status": "failure",
            "data": serializer.errors,
            "message": "Update failed."
        }, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        source = get_object_or_404(LeadSource, pk=pk)
        old_status = source.status
        source.status = not source.status
        source.save()

        LeadSourceAuditLog.objects.create(
            source=source,
            user=request.user,
            action_type='toggle',
            old_value={"status": old_status},
            new_value={"status": source.status}
        )

        return Response({
            "status": "success",
            "data": LeadSourceSerializer(source).data,
            "message": f"Lead source {'activated' if source.status else 'deactivated'} successfully."
        })

class LeadSourceReorderView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        order_list = request.data.get("order", [])

        for item in order_list:
            source = get_object_or_404(LeadSource, pk=item["id"])
            old_order = source.order
            source.order = item["order"]
            source.save()

            if old_order != item["order"]:
                LeadSourceAuditLog.objects.create(
                    source=source,
                    user=request.user,
                    action_type='reorder',
                    old_value={"order": old_order},
                    new_value={"order": item["order"]}
                )

        return Response({
            "status": "success",
            "data": {},
            "message": "Lead source order updated successfully."
        })


class LeadStageListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stages = LeadStage.objects.all().order_by('order_no')
        paginated, _ = paginate_and_format_response(stages, request, CustomUserPagination)
        serializer = LeadStageSerializer(paginated["Details"], many=True)
        paginated["Details"] = serializer.data

        return Response({
            "status": "success",
            "data": paginated,
            "message": "Lead stages fetched successfully"
        }, status=status.HTTP_200_OK)

class LeadStageCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LeadStageSerializer(data=request.data)
        if serializer.is_valid():
            stage = serializer.save(created_by=request.user)
            log_lead_stage_action(
                user=request.user,
                stage=stage,
                action_type='create',
                old_values=None,
                new_values=serializer.data
            )

            return Response({
                "status": "success",
                "data": serializer.data,
                "message": "Lead stage created successfully"
            }, status=status.HTTP_201_CREATED)

        return Response({
            "status": "failure",
            "data": serializer.errors,
            "message": "Lead stage creation failed"
        }, status=status.HTTP_400_BAD_REQUEST)

class LeadStageUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, stage_id):
        try:
            stage = LeadStage.objects.get(id=stage_id)
        except LeadStage.DoesNotExist:
            return Response({
                "status": "failure",
                "data": {},
                "message": "Lead stage not found"
            }, status=status.HTTP_404_NOT_FOUND)

        old_values = LeadStageSerializer(stage).data  # capture before update
        serializer = LeadStageSerializer(stage, data=request.data, partial=True)
        
        if serializer.is_valid():
            updated_stage = serializer.save()
            log_lead_stage_action(
                user=request.user,
                stage=updated_stage,
                action_type='update',
                old_values=old_values,
                new_values=serializer.data
            )

            return Response({
                "status": "success",
                "data": serializer.data,
                "message": "Lead stage updated successfully"
            }, status=status.HTTP_200_OK)

        return Response({
            "status": "failure",
            "data": serializer.errors,
            "message": "Lead stage update failed"
        }, status=status.HTTP_400_BAD_REQUEST)

class LeadStageStatusToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, stage_id):
        try:
            stage = LeadStage.objects.get(id=stage_id)
        except LeadStage.DoesNotExist:
            return Response({
                "status": "failure",
                "data": {},
                "message": "Lead stage not found"
            }, status=status.HTTP_404_NOT_FOUND)

        old_status = stage.is_active
        stage.is_active = not old_status
        stage.save()
        log_lead_stage_action(
            user=request.user,
            stage=stage,
            action_type='status_toggle',
            old_values={"is_active": old_status},
            new_values={"is_active": stage.is_active}
        )

        return Response({
            "status": "success",
            "data": {"is_active": stage.is_active},
            "message": f"Lead stage {'activated' if stage.is_active else 'deactivated'} successfully"
        }, status=status.HTTP_200_OK)

class LeadStageReorderView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        order_data = request.data.get("order", [])

        if not isinstance(order_data, list):
            return Response({
                "status": "failure",
                "data": {},
                "message": "Invalid order format. Expected a list of {id, order_no}."
            }, status=status.HTTP_400_BAD_REQUEST)

        updated_stages = []
        for entry in order_data:
            stage_id = entry.get("id")
            new_order = entry.get("order_no")
            try:
                stage = LeadStage.objects.get(id=stage_id)
                old_order = stage.order_no
                if old_order != new_order:
                    stage.order_no = new_order
                    stage.save()
                    updated_stages.append(stage)
                    log_lead_stage_action(
                        user=request.user,
                        stage=stage,
                        action_type='reorder',
                        old_values={"order_no": old_order},
                        new_values={"order_no": new_order}
                    )
            except LeadStage.DoesNotExist:
                continue  # Skip invalid IDs silently

        return Response({
            "status": "success",
            "data": {"updated_count": len(updated_stages)},
            "message": "Stage order updated successfully"
        }, status=status.HTTP_200_OK)

class LeadAssignmentLogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lead_id):
        logs = LeadAssignmentLog.objects.filter(lead_id=lead_id).order_by('-assigned_at')
        paginated, _ = paginate_and_format_response(logs, request, CustomUserPagination)
        serializer = LeadAssignmentLogSerializer(paginated["Details"], many=True)
        paginated["Details"] = serializer.data

        return Response({
            "status": "success",
            "data": paginated,
            "message": "Assignment logs fetched successfully"
        }, status=status.HTTP_200_OK)
    
class SalesUserListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sales_users = User.objects.filter(role__iexact='Sales', is_active=True).order_by('name')
        serializer = SimpleUserSerializer(sales_users, many=True)

        return Response({
            "status": "success",
            "data": serializer.data,
            "message": "Sales users fetched successfully"
        }, status=status.HTTP_200_OK)
    
class ManualLeadAssignView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        lead_ids = request.data.get("lead_ids", [])
        assigned_to_id = request.data.get("assigned_to")

        if not lead_ids or not assigned_to_id:
            return Response({
                "status": "failure",
                "data": {},
                "message": "lead_ids and assigned_to are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            assignee = User.objects.get(id=assigned_to_id)
        except User.DoesNotExist:
            return Response({
                "status": "failure",
                "data": {},
                "message": "Assigned user not found."
            }, status=status.HTTP_404_NOT_FOUND)

        assigned_count = 0
        failed_ids = []

        for lead_id in lead_ids:
            try:
                lead = Lead.objects.get(id=lead_id, is_deleted=False)
                if lead.assigned_to is None:
                    lead.assigned_to = assignee
                    lead.assigned_at = timezone.now()
                    lead.assigned_by = request.user
                    lead.save()

                    LeadAssignmentLog.objects.create(
                        lead=lead,
                        assigned_to=assignee,
                        assigned_by=request.user,
                        method='manual'
                    )
                    assigned_count += 1
                else:
                    failed_ids.append(str(lead_id))
            except Lead.DoesNotExist:
                failed_ids.append(str(lead_id))

        return Response({
            "status": "success",
            "data": {
                "assigned_count": assigned_count,
                "skipped": failed_ids
            },
            "message": f"{assigned_count} lead(s) assigned successfully. {len(failed_ids)} skipped."
        }, status=status.HTTP_200_OK)