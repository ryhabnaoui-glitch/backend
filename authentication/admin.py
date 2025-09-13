# authentication/admin.py - UPDATED WITH ELECTION MANAGEMENT


// hadi rani nekhdam biha just pour admin configuration fel url /admin/ par exemple rani dayretha just bach nchof fel url les models 
// et tous avec des options rechercher filter ...etc 




from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Election, Candidate, Vote, ContractDeployment

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_candidate', 'is_elector', 'is_admin', 'verified', 'approved', 'selected_election')
    list_filter = ('is_candidate', 'is_elector', 'is_admin', 'verified', 'approved', 'is_staff', 'is_active', 'selected_election')
    search_fields = ('username', 'email', 'wallet_address')
    fieldsets = UserAdmin.fieldsets + (
        ('Custom fields', {
            'fields': ('is_candidate', 'is_elector', 'is_admin', 'wallet_address', 'verified', 'approved', 'selected_election')
        }),
    )

@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'election_type', 'start_date', 'end_date', 'is_active', 'created_by', 'blockchain_id')
    list_filter = ('election_type', 'is_active', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('blockchain_id', 'contract_address', 'created_at', 'updated_at')
    date_hierarchy = 'start_date'

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'election', 'blockchain_id', 'wallet_address')
    list_filter = ('election', 'created_at')
    search_fields = ('name', 'user__username', 'user__email', 'wallet_address')
    readonly_fields = ('blockchain_id', 'created_at')

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('voter', 'candidate', 'election', 'status', 'voted_at', 'transaction_hash')
    list_filter = ('status', 'election', 'voted_at')
    search_fields = ('voter__username', 'candidate__name', 'transaction_hash')
    readonly_fields = ('voted_at', 'reviewed_at')
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('voter', 'candidate', 'election', 'transaction_hash')
        return self.readonly_fields

@admin.register(ContractDeployment)
class ContractDeploymentAdmin(admin.ModelAdmin):
    list_display = ('contract_address', 'deployed_by', 'deployed_at', 'is_active', 'election')
    list_filter = ('is_active', 'deployed_at')
    search_fields = ('contract_address', 'deployed_by__username')
    readonly_fields = ('deployed_at',)
