from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    email = models.EmailField(unique=True) 
    phone = models.CharField(
        max_length=15,
        blank=True, null=True,
        unique=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Nam'), ('female', 'Nữ'), ('other', 'Khác')], blank=True, null=True)
    birthday = models.DateField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    is_tasker = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.username} ({self.email})'

class IdentityVerification(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    id_number = models.CharField(max_length=20)  # Thêm để fix serializer
    front_image = models.ImageField(upload_to='identity/')
    back_image = models.ImageField(upload_to='identity/')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reason = models.TextField(blank=True, null=True)  # Lý do nếu bị từ chối
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.status}"

class TaskerRegistration(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, null=True)
    experience = models.TextField(blank=True, null=True)
    agreed_terms = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.status}"

