# management/commands/seeder_users.py - FIXED VERSION WITH PREDICTABLE ORDERING

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed initial users with Ganache wallet addresses - FIXED WITH CONSISTENT ORDERING'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete existing users first'
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write("Deleting all users...")
            User.objects.all().delete()

        # STATIC GANACHE ADDRESSES (same every restart)
        ganache_addresses = [
            "0xaC00fcF18e03E91Db8055c283952850e7c2bE6a2",
            "0xAbFDD2c725C4621B4bfd46d8d8c26b3ede911b32", 
            "0xb0E986DCA239dca5f06371fdec400D7ca0357D74",
            "0x4A9D09c03e109f58A6343BBBE4901eF91a48F0a9",
            "0x1C83BFAc51d9d4E57BaFa0cB0493E2F4d7FD0BeA",
            "0x7f894e69bD3afefB184D93171D9D8C3b220cD531",
            "0x5DD897779bde383884d7D8cD1295e475A671D0d0",
            "0x0B7ea402204001Ca6edD41a2Cec10d7D0033d19e",
            "0x0412F8BE1bd07bC5d2457ec2932c955c84958288",
            "0xe02F4B54AB39b0bDfc2FED374c23b66647AB2047",
        ]

        users = [
            # Admin first
            {
                'username': 'admin',
                'email': 'admin@votechain.com',
                'password': 'admin123',
                'is_superuser': True,
                'is_staff': True,
                'is_admin': True,
                'is_candidate': False,
                'is_elector': False,
                'verified': True,
                'approved': True,
                'wallet_address': ganache_addresses[0],
                'order': 1
            },
            # Candidates in alphabetical order (predictable blockchain mapping)
            {
                'username': 'bob_wilson',
                'email': 'bob@example.com',
                'password': 'password123',
                'is_candidate': True,
                'is_elector': False,
                'is_admin': False,
                'verified': True,
                'approved': True,
                'wallet_address': ganache_addresses[1],
                'order': 2
            },
            {
                'username': 'jane_smith',
                'email': 'jane@example.com',
                'password': 'password123',
                'is_candidate': True,
                'is_elector': False,
                'is_admin': False,
                'verified': True,
                'approved': True,
                'wallet_address': ganache_addresses[2],
                'order': 3
            },
            {
                'username': 'john_doe',
                'email': 'john@example.com',
                'password': 'password123',
                'is_candidate': True,
                'is_elector': False,
                'is_admin': False,
                'verified': True,
                'approved': True,
                'wallet_address': ganache_addresses[3],
                'order': 4
            },
            # Electors
            {
                'username': 'alice_voter',
                'email': 'alice@example.com',
                'password': 'password123',
                'is_candidate': False,
                'is_elector': True,
                'is_admin': False,
                'verified': True,
                'approved': True,
                'wallet_address': ganache_addresses[4],
                'order': 5
            },
        ]

        # Sort by order to ensure predictable IDs
        users_sorted = sorted(users, key=lambda x: x['order'])

        with transaction.atomic():
            for user_data in users_sorted:
                if not User.objects.filter(username=user_data['username']).exists():
                    user_data.pop('order')  # Remove order field
                    
                    user = User.objects.create_user(
                        username=user_data['username'],
                        email=user_data['email'],
                        password=user_data['password'],
                        is_candidate=user_data['is_candidate'],
                        is_elector=user_data['is_elector'],
                        is_admin=user_data['is_admin'],
                        verified=user_data['verified'],
                        approved=user_data['approved'],
                        wallet_address=user_data['wallet_address']
                    )
                    
                    if user_data.get('is_superuser'):
                        user.is_superuser = True
                        user.is_staff = True
                        user.save()
                    
                    self.stdout.write(f'✅ Created: {user.username} (ID: {user.id})')

        self.stdout.write(self.style.SUCCESS('\n🎉 Users seeded with predictable IDs!'))