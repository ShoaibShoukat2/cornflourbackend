import random
import string
from django.core.mail import send_mail
from django.conf import settings

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def generate_verification_token():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=64))

def send_verification_email(user):
    token = generate_verification_token()
    user.email_verification_token = token
    user.save()
    
    verification_link = f"http://localhost:5173/verify-email/{token}"
    
    send_mail(
        'Verify Your Email - YTEarn',
        f'Click the link to verify your email: {verification_link}',
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    
    return token

def send_otp_email(user):
    otp = generate_otp()
    user.otp = otp
    user.save()
    
    send_mail(
        'Your OTP Code - YTEarn',
        f'Your OTP code is: {otp}\n\nThis code will expire in 10 minutes.',
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    
    return otp
