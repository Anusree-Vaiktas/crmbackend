import requests
from django.conf import settings
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User,UserSession
from django.contrib.auth.hashers import make_password

class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ['password']
        extra_kwargs = {'password': {'write_only': True}}

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    recaptcha_token = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")
        recaptcha_token = data.get("recaptcha_token")
        if settings.DEBUG and recaptcha_token == "test-token":
            # Skip verification in dev mode
            pass
        else:
            if not recaptcha_token:
                raise serializers.ValidationError("reCAPTCHA token is missing.")

            # Step 1: Verify reCAPTCHA
            recaptcha_response = requests.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={
                    "secret": settings.RECAPTCHA_PRIVATE_KEY,
                    "response": recaptcha_token
                }
            )
            result = recaptcha_response.json()

            if not result.get("success"):
                raise serializers.ValidationError("Invalid reCAPTCHA. Try again.")

        # Step 2: Authenticate user
        user = authenticate(request=self.context.get('request'), email=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid credentials.")
        if not user.is_active:
            raise serializers.ValidationError("User is deactivated.")

        data["user"] = user
        return data

class UserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = ['id', 'ip_address', 'user_agent', 'created_at', 'last_seen_at', 'session_token']

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'name', 'email', 'password', 'phone', 'role', 'status',
            'department_id', 'is_active', 'is_verified',
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email is already in use.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        created_by = self.context.get("created_by")
        updated_by = self.context.get("updated_by")
        validated_data['created_by'] = created_by
        validated_data['updated_by'] = updated_by

        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UpdateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['name', 'email', 'phone', 'role', 'status', 'department_id', 'password', 'is_active']

    def validate_email(self, value):
        user_id = self.instance.id if self.instance else None
        if User.objects.exclude(id=user_id).filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        request = self.context.get("request")
        updated_by = self.context.get("updated_by")
        validated_data['updated_by'] = updated_by
        
        if request:
            instance.updated_by = request.user

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email']