from datetime import timedelta
from django.utils.timezone import now
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework import status, permissions, generics
from .serializers import UserLoginSerializer, UserDetailSerializer, UserSessionSerializer, UserCreateSerializer,UpdateUserSerializer
from .models import LoginLog, User, UserSession
from rest_framework.permissions import IsAdminUser
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.timezone import now
from datetime import timedelta
from django.contrib.auth.hashers import make_password
from .pagination import CustomUserPagination, paginate_and_format_response
from django.db.models import Q
from django.utils.dateparse import parse_date

class LoginView(APIView):
    MAX_ATTEMPTS = 5
    LOCK_DURATION_MINUTES = 10

    def post(self, request):
        email = request.data.get("email")
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT')

        user_obj = User.objects.filter(email=email).first()

        # Step 1: Check if account is locked
        if user_obj and user_obj.account_locked_at:
            elapsed = now() - user_obj.account_locked_at
            if elapsed < timedelta(minutes=self.LOCK_DURATION_MINUTES):
                LoginLog.objects.create(
                    user=user_obj,
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    reason="Account locked due to too many failed attempts"
                )
                return Response(
                    {"detail": "Account is locked. Try again after 10 minutes."},
                    status=403
                )
            else:
                # Auto-unlock after timeout
                user_obj.login_attempts = 0
                user_obj.account_locked_at = None
                user_obj.save()

        # Step 2: Validate credentials
        serializer = UserLoginSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            # Log failed attempt if user exists
            if user_obj:
                user_obj.login_attempts += 1
                user_obj.last_failed_login_at = now()
                if user_obj.login_attempts >= self.MAX_ATTEMPTS:
                    user_obj.account_locked_at = now()
                user_obj.save()

                LoginLog.objects.create(
                    user=user_obj,
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    reason="Invalid credentials"
                )

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data["user"]

        # Step 3: Check if account is active
        if not user.is_active:
            LoginLog.objects.create(
                user=user,
                success=False,
                ip_address=ip_address,
                user_agent=user_agent,
                reason="Inactive account"
            )
            return Response({"detail": "Account is inactive."}, status=403)

        # Step 4: Successful login
        refresh = RefreshToken.for_user(user)
        UserSession.objects.create(
            user=user,
            session_token=str(refresh),
            ip_address=ip_address,
            user_agent=user_agent
        )
        user.last_login_at = now()
        user.login_attempts = 0
        user.account_locked_at = None
        user.save()

        LoginLog.objects.create(
            user=user,
            success=True,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": UserDetailSerializer(user).data
        })

class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        refresh_token = request.data.get("refresh")
        if refresh_token and response.status_code == 200:
            try:
                token = RefreshToken(refresh_token)
                user_id = token.payload.get("user_id")
                user = User.objects.get(id=user_id)

                # Update session record's last seen
                UserSession.objects.filter(
                    user=user,
                    session_token=refresh_token
                ).update(last_seen_at=now())

                return Response({
                    "status": "success",
                    "data": response.data,
                    "message": "Token refreshed successfully."
                }, status=status.HTTP_200_OK)

            except Exception as e:
                # Optionally log error here
                return Response({
                    "status": "failure",
                    "data": {},
                    "message": "Failed to refresh token. Invalid refresh token or user not found."
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "status": "failure",
            "data": {},
            "message": "Invalid refresh request."
        }, status=response.status_code)
    
class UserSessionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user_id_param = request.query_params.get('user_id')

        if user.is_staff:
            if user_id_param:
                queryset = UserSession.objects.filter(user__id=user_id_param)
            else:
                queryset = UserSession.objects.all()
        else:
            queryset = UserSession.objects.filter(user=user)

        serializer = UserSessionSerializer(queryset, many=True)
        return Response({
            "status": "success",
            "data": serializer.data,
            "message": "User session list fetched successfully."
        }, status=status.HTTP_200_OK)
    
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        session_token = request.data.get("session_token")
        if not session_token:
            return Response({
                "status": "failure",
                "data": {},
                "message": "Session token is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        session_qs = UserSession.objects.filter(user=request.user, session_token=session_token)
        if not session_qs.exists():
            return Response({
                "status": "failure",
                "data": {},
                "message": "Session not found or already logged out."
            }, status=status.HTTP_404_NOT_FOUND)

        session_qs.delete()
        return Response({
            "status": "success",
            "data": {},
            "message": "Logged out successfully."
        }, status=status.HTTP_200_OK)
   
class UserCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]  # Or remove if not needed

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                created_by=request.user.id,
                updated_by=request.user.id
            )
            return Response({
                "status": "success",
                "data": serializer.data,
                "message": "User created successfully"
            }, status=status.HTTP_201_CREATED)
        return Response({
            "status": "failure",
            "data": serializer.errors,
            "message": "User creation failed"
        }, status=status.HTTP_400_BAD_REQUEST)
    
class UserListAllAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        users = User.objects.filter(status='Active').order_by('-created_at')
        serialized_users = UserDetailSerializer(users, many=True)
        paginated_data, _ = paginate_and_format_response(serialized_users.data, request, CustomUserPagination)

        return Response({
            "status": "success",
            "data": paginated_data,
            "message": "All users fetched successfully"
        }, status=status.HTTP_200_OK)

class UserSearchAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('query', '').strip()
        if not query:
            return Response({
                "status": "failure",
                "data": {},
                "message": "Search query cannot be empty."
            }, status=status.HTTP_400_BAD_REQUEST)

        users = User.objects.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(role__icontains=query)
        ).order_by('-created_at')

        serialized_users = UserDetailSerializer(users, many=True)
        paginated_data, _ = paginate_and_format_response(serialized_users.data, request, CustomUserPagination)

        return Response({
            "status": "success",
            "data": paginated_data,
            "message": "Users matching search query fetched successfully"
        }, status=status.HTTP_200_OK)

class UserFilterAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = request.query_params.get('role')
        status_val = request.query_params.get('status')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        filters = Q()

        if role:
            filters &= Q(role__iexact=role)
        if status_val:
            filters &= Q(status__iexact=status_val)
        if start_date:
            filters &= Q(created_at__date__gte=parse_date(start_date))
        if end_date:
            filters &= Q(created_at__date__lte=parse_date(end_date))

        users = User.objects.filter(filters).order_by('-created_at')

        serialized_users = UserDetailSerializer(users, many=True)
        paginated_data, _ = paginate_and_format_response(serialized_users.data, request, CustomUserPagination)

        return Response({
            "status": "success",
            "data": paginated_data,
            "message": "Filtered users fetched successfully"
        }, status=status.HTTP_200_OK)
    
class GetUserByIdView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            serializer = UserDetailSerializer(user)
            return Response({
                "status": "success",
                "data": serializer.data,
                "message": "User fetched successfully"
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({
                "status": "failure",
                "data": {},
                "message": "User not found"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "status": "failure",
                "data": {},
                "message": "An error occurred while fetching the user"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                "status": "failure",
                "data": {},
                "message": "User not found"
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = UpdateUserSerializer(user, data=request.data, partial=True, context={
            'request': request,
            'updated_by': request.user.id
        })

        if serializer.is_valid():
            serializer.save()
            return Response({
                "status": "success",
                "data": UserDetailSerializer(serializer.instance).data,
                "message": "User updated successfully"
            }, status=status.HTTP_200_OK)

        return Response({
            "status": "failure",
            "data": serializer.errors,
            "message": "User update failed"
        }, status=status.HTTP_400_BAD_REQUEST)

class ToggleUserStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, user_id):
        if request.user.role != "Admin":
            return Response({
                "status": "failure",
                "data": {},
                "message": "You do not have permission to perform this action."
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                "status": "failure",
                "data": {},
                "message": "User not found"
            }, status=status.HTTP_404_NOT_FOUND)

        is_active = request.data.get("is_active")
        if is_active is None:
            return Response({
                "status": "failure",
                "data": {},
                "message": "Missing 'is_active' in request body"
            }, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = is_active
        user.updated_by = request.user.id  # ✅ FIXED
        user.save()

        status_str = "activated" if is_active else "deactivated"
        return Response({
            "status": "success",
            "data": {"is_active": user.is_active},
            "message": f"User successfully {status_str}"
        }, status=status.HTTP_200_OK)
