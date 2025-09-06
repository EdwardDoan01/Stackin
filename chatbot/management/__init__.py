from django.core.management.base import BaseCommand
from chatbot.models import ChatbotSuggestion

class Command(BaseCommand):
    help = 'Create sample chatbot suggestions'

    def handle(self, *args, **options):
        suggestions_data = [
            {
                'title': 'Dich vu cua Stackin',
                'description': 'Tim hieu ve cac dich vu nhu lap rap do noi that, di chuyen, sua chua nha cua...',
                'category': 'services',
                'order': 1
            },
            {
                'title': 'Cach su dung nen tang',
                'description': 'Huong dan tung buoc de dang task, chon tasker va thanh toan',
                'category': 'general',
                'order': 2
            },
            {
                'title': 'Gia ca va thanh toan',
                'description': 'Thong tin ve gia dich vu va he thong thanh toan escrow an toan',
                'category': 'pricing',
                'order': 3
            },
            {
                'title': 'Tro thanh Tasker',
                'description': 'Huong dan dang ky va kiem tien tren Stackin',
                'category': 'tasker',
                'order': 4
            },
            {
                'title': 'Ho tro ky thuat',
                'description': 'Lien he ho tro khi gap van de hoac can giup do',
                'category': 'support',
                'order': 5
            }
        ]

        for data in suggestions_data:
            suggestion, created = ChatbotSuggestion.objects.get_or_create(
                title=data['title'],
                defaults=data
            )
            if created:
                self.stdout.write(f"Created: {suggestion.title}")
            else:
                self.stdout.write(f"Already exists: {suggestion.title}")

        self.stdout.write(self.style.SUCCESS('Sample chatbot suggestions created successfully!'))
