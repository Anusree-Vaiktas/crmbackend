from django.urls import path
from .views import GetUserByIdView, LoginView,CustomTokenRefreshView, UserUpdateAPIView, UserSessionListView, LogoutView, UserCreateAPIView, UserListAllAPIView, UserSearchAPIView, UserFilterAPIView
from .views import ToggleUserStatusView

urlpatterns = [
    path("users/login/", LoginView.as_view(), name="login"),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('admin/user-sessions/', UserSessionListView.as_view(), name='user_sessions_list'),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("create/users/", UserCreateAPIView.as_view(), name="create_user"),
    path("users/list/", UserListAllAPIView.as_view(), name="user-list-all"),
    path("users/search/", UserSearchAPIView.as_view(), name="user-search"),
    path("users/filter/", UserFilterAPIView.as_view(), name="user-filter"),
    path("users/<uuid:user_id>/", GetUserByIdView.as_view(), name="get_user_by_id"),
    path("users/<uuid:user_id>/update/", UserUpdateAPIView.as_view(), name="update_user"),
    path("users/<uuid:user_id>/status/", ToggleUserStatusView.as_view(), name="toggle_user_status"),
]
