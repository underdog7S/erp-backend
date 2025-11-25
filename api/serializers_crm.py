from rest_framework import serializers
from api.models.crm import Contact, Company, ContactTag, Activity, Deal, DealStage
from api.models.user import Tenant, UserProfile
from django.contrib.auth.models import User


class ContactTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactTag
        fields = ['id', 'tenant', 'name', 'color', 'created_at']
        read_only_fields = ['id', 'tenant', 'created_at']


class CompanySerializer(serializers.ModelSerializer):
    contact_count = serializers.IntegerField(read_only=True)
    tags = ContactTagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=ContactTag.objects.all(), 
        source='tags', 
        write_only=True, 
        required=False
    )
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Company
        fields = [
            'id', 'tenant', 'name', 'industry', 'website', 'phone', 'email',
            'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country',
            'company_size', 'annual_revenue', 'description',
            'parent_company', 'tags', 'tag_ids', 'custom_fields',
            'owner', 'owner_name', 'created_by', 'created_by_name',
            'created_at', 'updated_at', 'last_contacted_at', 'notes',
            'contact_count', 'full_address'
        ]
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at', 'contact_count', 'full_address']
    
    def validate(self, data):
        # Ensure tenant is set from request context
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user_profile = UserProfile.objects.filter(user=request.user).first()
            if user_profile:
                data['tenant'] = user_profile.tenant
        return data


class ContactSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    full_address = serializers.CharField(read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    tags = ContactTagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=ContactTag.objects.all(), 
        source='tags', 
        write_only=True, 
        required=False
    )
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    activity_count = serializers.SerializerMethodField()
    deal_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Contact
        fields = [
            'id', 'tenant', 'contact_type', 'lifecycle_stage',
            'first_name', 'last_name', 'full_name',
            'email', 'phone', 'mobile',
            'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country', 'full_address',
            'date_of_birth', 'gender', 'job_title',
            'company', 'company_name',
            'email_opt_in', 'sms_opt_in', 'preferred_contact_method',
            'tags', 'tag_ids', 'custom_fields',
            'owner', 'owner_name', 'created_by', 'created_by_name',
            'created_at', 'updated_at', 'last_contacted_at', 'notes',
            'activity_count', 'deal_count'
        ]
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at', 'full_name', 'full_address', 'activity_count', 'deal_count']
    
    def get_activity_count(self, obj):
        return obj.activities.count()
    
    def get_deal_count(self, obj):
        return obj.deals.count()
    
    def validate(self, data):
        # Ensure tenant is set from request context
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user_profile = UserProfile.objects.filter(user=request.user).first()
            if user_profile:
                data['tenant'] = user_profile.tenant
        return data


class ActivitySerializer(serializers.ModelSerializer):
    contact_name = serializers.CharField(source='contact.full_name', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True)
    
    class Meta:
        model = Activity
        fields = [
            'id', 'tenant', 'activity_type', 'subject', 'description',
            'contact', 'contact_name', 'company', 'company_name',
            'activity_date', 'duration_minutes', 'status', 'outcome',
            'created_by', 'created_by_name', 'assigned_to', 'assigned_to_name',
            'created_at', 'updated_at', 'attachments'
        ]
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']
    
    def validate(self, data):
        # Ensure tenant is set from request context
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user_profile = UserProfile.objects.filter(user=request.user).first()
            if user_profile:
                data['tenant'] = user_profile.tenant
                if 'created_by' not in data:
                    data['created_by'] = request.user
        return data


class DealStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealStage
        fields = ['id', 'tenant', 'name', 'order', 'probability', 'is_closed', 'color']
        read_only_fields = ['id', 'tenant']


class DealSerializer(serializers.ModelSerializer):
    contact_name = serializers.CharField(source='contact.full_name', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    weighted_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    stage_name = serializers.CharField(source='stage', read_only=True)
    
    class Meta:
        model = Deal
        fields = [
            'id', 'tenant', 'name', 'description', 'amount', 'currency',
            'contact', 'contact_name', 'company', 'company_name',
            'stage', 'stage_name', 'probability',
            'close_date', 'expected_close_date',
            'won', 'lost', 'lost_reason',
            'owner', 'owner_name', 'created_by', 'created_by_name',
            'created_at', 'updated_at', 'custom_fields',
            'weighted_amount'
        ]
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at', 'weighted_amount']
    
    def validate(self, data):
        # Ensure tenant is set from request context
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user_profile = UserProfile.objects.filter(user=request.user).first()
            if user_profile:
                data['tenant'] = user_profile.tenant
                if 'created_by' not in data:
                    data['created_by'] = request.user
        return data

