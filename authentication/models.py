# authentication/models.py - COMPLETE WITH HYBRID ELECTION TYPES
from django.contrib.auth.models import AbstractUser
from django.db import models
// hado les models ta3 base donnée
class Election(models.Model):
    # HYBRID APPROACH: Predefined choices + custom option
    ELECTION_TYPES = [
        ('presidential', 'Presidential Election'),
        ('parliamentary', 'Parliamentary Election'),
        ('local', 'Local Government Election'),
        ('referendum', 'Referendum'),
        ('student', 'Student Council Election'),
        ('corporate', 'Corporate Board Election'),
        ('custom', 'Custom Type'),  # Special option for custom input
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    election_type = models.CharField(max_length=20, choices=ELECTION_TYPES, default='presidential')
    custom_election_type = models.CharField(max_length=100, blank=True, null=True, help_text="Custom election type name (only if 'Custom Type' is selected)")
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE, related_name='created_elections')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Blockchain integration fields
    blockchain_id = models.IntegerField(null=True, blank=True)
    contract_address = models.CharField(max_length=42, blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def get_display_type(self):
        """Return the display name for the election type"""
        if self.election_type == 'custom' and self.custom_election_type:
            return self.custom_election_type
        return self.get_election_type_display()
    
    def __str__(self):
        return f"{self.title} ({self.get_display_type()})"

class User(AbstractUser):
    is_candidate = models.BooleanField(default=False)
    is_elector = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    wallet_address = models.CharField(max_length=42, blank=True, null=True)
    verified = models.BooleanField(default=False)
    approved = models.BooleanField(default=False)
    
    # Election assignment
    selected_election = models.ForeignKey(Election, on_delete=models.SET_NULL, null=True, blank=True, related_name='participants')
    
    def __str__(self):
        return self.username

class Candidate(models.Model):
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='candidates')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    blockchain_id = models.IntegerField(null=True, blank=True)  # Position in blockchain
    name = models.CharField(max_length=200)
    wallet_address = models.CharField(max_length=42)
    manifesto = models.TextField(blank=True)  # Candidate's political platform
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['election', 'user']

    def __str__(self):
        return f"{self.name} - {self.election.title}"

class Vote(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    voter = models.ForeignKey(User, on_delete=models.CASCADE)
    transaction_hash = models.CharField(max_length=66)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    voted_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_votes')
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['election', 'voter']

    def __str__(self):
        return f"{self.voter.username} -> {self.candidate.name} ({self.status})"

class ContractDeployment(models.Model):
    contract_address = models.CharField(max_length=42, unique=True)
    deployed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    deployed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    election = models.ForeignKey(Election, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"Contract: {self.contract_address}"
