from rest_framework import serializers
from api.models.email_marketing import (
    EmailTemplate, ContactList, EmailCampaign, EmailActivity,
    EmailSequence, EmailSequenceStep
)
from api.models.user import UserProfile
from api.models.crm import Contact
from api.serializers_crm import ContactSerializer


class EmailTemplateSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = EmailTemplate
        fields = [
            'id', 'tenant', 'name', 'subject', 'body_html', 'body_text',
            'variables', 'created_by', 'created_by_name',
            'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']
    
    def validate(self, data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user_profile = UserProfile.objects.filter(user=request.user).first()
            if user_profile:
                data['tenant'] = user_profile.tenant
                if 'created_by' not in data:
                    data['created_by'] = request.user
        return data


class ContactListSerializer(serializers.ModelSerializer):
    contact_count = serializers.IntegerField(read_only=True)
    contacts = ContactSerializer(many=True, read_only=True)
    contact_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Contact.objects.all(),  # Default queryset, will be filtered in __init__
        source='contacts',
        write_only=True,
        required=False
    )
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = ContactList
        fields = [
            'id', 'tenant', 'name', 'description', 'filter_criteria',
            'contacts', 'contact_ids', 'contact_count',
            'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at', 'contact_count']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set queryset for contact_ids based on tenant
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user_profile = UserProfile.objects.filter(user=request.user).first()
            if user_profile:
                from api.models.crm import Contact
                self.fields['contact_ids'].queryset = Contact.objects.filter(tenant=user_profile.tenant)
    
    def validate(self, data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user_profile = UserProfile.objects.filter(user=request.user).first()
            if user_profile:
                data['tenant'] = user_profile.tenant
                if 'created_by' not in data:
                    data['created_by'] = request.user
        return data


class EmailActivitySerializer(serializers.ModelSerializer):
    contact_name = serializers.CharField(source='contact.full_name', read_only=True)
    contact_email = serializers.CharField(source='contact.email', read_only=True)
    
    class Meta:
        model = EmailActivity
        fields = [
            'id', 'campaign', 'contact', 'contact_name', 'contact_email',
            'status', 'sent_at', 'delivered_at', 'opened_at', 'clicked_at',
            'bounced_at', 'open_count', 'click_count', 'bounce_reason',
            'links_clicked', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmailCampaignSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True)
    contact_list_name = serializers.CharField(source='contact_list.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    # Statistics
    total_recipients = serializers.IntegerField(read_only=True)
    sent_count = serializers.IntegerField(read_only=True)
    opened_count = serializers.IntegerField(read_only=True)
    clicked_count = serializers.IntegerField(read_only=True)
    open_rate = serializers.FloatField(read_only=True)
    click_rate = serializers.FloatField(read_only=True)
    
    recipients = ContactSerializer(many=True, read_only=True)
    recipient_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Contact.objects.all(),  # Default queryset, will be filtered in __init__
        source='recipients',
        write_only=True,
        required=False
    )
    
    class Meta:
        model = EmailCampaign
        fields = [
            'id', 'tenant', 'name', 'subject', 'body_html', 'body_text',
            'template', 'template_name', 'contact_list', 'contact_list_name',
            'recipients', 'recipient_ids', 'status', 'scheduled_at', 'sent_at',
            'from_email', 'from_name', 'reply_to',
            'created_by', 'created_by_name',
            'created_at', 'updated_at',
            'total_recipients', 'sent_count', 'opened_count', 'clicked_count',
            'open_rate', 'click_rate'
        ]
        read_only_fields = [
            'id', 'tenant', 'created_at', 'updated_at', 'sent_at',
            'total_recipients', 'sent_count', 'opened_count', 'clicked_count',
            'open_rate', 'click_rate'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user_profile = UserProfile.objects.filter(user=request.user).first()
            if user_profile:
                from api.models.crm import Contact
                self.fields['recipient_ids'].queryset = Contact.objects.filter(tenant=user_profile.tenant)
    
    def validate(self, data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user_profile = UserProfile.objects.filter(user=request.user).first()
            if user_profile:
                data['tenant'] = user_profile.tenant
                if 'created_by' not in data:
                    data['created_by'] = request.user
        return data


class EmailSequenceStepSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True)
    
    class Meta:
        model = EmailSequenceStep
        fields = [
            'id', 'sequence', 'order', 'template', 'template_name',
            'subject', 'body_html', 'delay_days', 'delay_hours', 'conditions'
        ]
        read_only_fields = ['id']


class EmailSequenceSerializer(serializers.ModelSerializer):
    steps = EmailSequenceStepSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = EmailSequence
        fields = [
            'id', 'tenant', 'name', 'description', 'trigger_event',
            'is_active', 'created_by', 'created_by_name',
            'created_at', 'updated_at', 'steps'
        ]
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']
    
    def validate(self, data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user_profile = UserProfile.objects.filter(user=request.user).first()
            if user_profile:
                data['tenant'] = user_profile.tenant
                if 'created_by' not in data:
                    data['created_by'] = request.user
        return data

