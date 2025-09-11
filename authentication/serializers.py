# authentication/serializers.py - FIXED VERSION

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Election, Candidate, Vote

User = get_user_model()

class ElectionSerializer(serializers.ModelSerializer):
    election_type_display = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    candidate_count = serializers.SerializerMethodField()
    voter_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Election
        fields = [
            'id', 'title', 'description', 'election_type', 'custom_election_type', 'election_type_display',
            'start_date', 'end_date', 'is_active', 'created_by', 'created_by_name',
            'created_at', 'updated_at', 'blockchain_id', 'contract_address',
            'candidate_count', 'voter_count'
        ]
        # CRITICAL FIX: Remove 'created_by' from read_only_fields
        read_only_fields = ['created_at', 'updated_at', 'blockchain_id', 'contract_address', 'created_by_name']
        extra_kwargs = {
            # Make created_by not required in validation but allow it to be set
            'created_by': {'required': False, 'allow_null': True}
        }
    
    def get_election_type_display(self, obj):
        return obj.get_display_type()
    
    def get_candidate_count(self, obj):
        return obj.candidates.count()
    
    def get_voter_count(self, obj):
        return obj.participants.filter(is_elector=True).count()
    
    def validate(self, data):
        # If custom type is selected, require custom_election_type field
        if data.get('election_type') == 'custom' and not data.get('custom_election_type'):
            raise serializers.ValidationError({
                'custom_election_type': 'Custom election type name is required when "Custom Type" is selected.'
            })
        
        # If not custom, clear the custom field
        if data.get('election_type') != 'custom':
            data['custom_election_type'] = None
            
        return data

# Keep the rest of your serializers unchanged...
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    wallet_address = serializers.CharField(required=False, allow_blank=True)
    selected_election_details = ElectionSerializer(source='selected_election', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'is_candidate', 'is_elector', 
            'is_admin', 'wallet_address', 'verified', 'approved', 'selected_election',
            'selected_election_details', 'date_joined'
        ]
        read_only_fields = ['date_joined']
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user

class CandidateSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    election_details = ElectionSerializer(source='election', read_only=True)
    
    class Meta:
        model = Candidate
        fields = [
            'id', 'blockchain_id', 'name', 'wallet_address', 'manifesto',
            'user_details', 'election_details', 'created_at'
        ]

class VoteSerializer(serializers.ModelSerializer):
    voter_details = UserSerializer(source='voter', read_only=True)
    candidate_details = CandidateSerializer(source='candidate', read_only=True)
    election_details = ElectionSerializer(source='election', read_only=True)
    reviewed_by_details = UserSerializer(source='reviewed_by', read_only=True)
    
    class Meta:
        model = Vote
        fields = [
            'id', 'transaction_hash', 'status', 'voted_at', 'reviewed_at',
            'voter_details', 'candidate_details', 'election_details', 'reviewed_by_details'
        ]

class ElectionChoiceSerializer(serializers.ModelSerializer):
    """Simplified serializer for election dropdown in registration"""
    election_type_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Election
        fields = ['id', 'title', 'election_type', 'election_type_display', 'start_date', 'end_date', 'is_active']
    
    def get_election_type_display(self, obj):
        return obj.get_display_type()
