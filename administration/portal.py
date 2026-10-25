"""Terms, complaints, admin history, and activity log. Reads existing records only."""

import csv
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from administration.models import AdminActivity, Complaint, PackagePayment, SiteSettings
from administration.terms_content import DEFAULT_TERMS
from wallet.models import Transaction, Withdrawal

User = get_user_model()


def record_activity(admin, action, detail=''):
    AdminActivity.objects.create(admin=admin if getattr(admin, 'is_authenticated', False) else None, action=action, detail=(detail or '')[:1000])


def terms_sections():
    settings, _ = SiteSettings.objects.get_or_create(id=1)
    sections = settings.terms_sections or []
    if not sections:
        settings.terms_sections = DEFAULT_TERMS
        settings.save(update_fields=['terms_sections'])
        sections = DEFAULT_TERMS
    return sections


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_terms(request):
    return Response({'sections': terms_sections()})


@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])
def admin_terms(request):
    settings, _ = SiteSettings.objects.get_or_create(id=1)
    if request.method == 'GET':
        return Response({'sections': terms_sections()})
    sections = request.data.get('sections')
    if not isinstance(sections, list) or not sections:
        return Response({'error': 'Add at least one section.'}, status=400)
    cleaned = []
    for item in sections:
        title = str(item.get('title', '')).strip()
        body = str(item.get('body', '')).strip()
        if title and body:
            cleaned.append({'title': title[:200], 'body': body})
    if not cleaned:
        return Response({'error': 'Each section needs a title and text.'}, status=400)
    settings.terms_sections = cleaned
    settings.save(update_fields=['terms_sections'])
    record_activity(request.user, 'terms_update', f'{len(cleaned)} sections')
    return Response({'message': 'Terms updated', 'sections': cleaned})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def user_complaints(request):
    if request.method == 'GET':
        rows = Complaint.objects.filter(user=request.user)
        return Response({'complaints': [_complaint_payload(row) for row in rows[:50]]})
    message = str(request.data.get('message', '')).strip()
    if len(message) < 5:
        return Response({'error': 'Write your feedback or complaint.'}, status=400)
    complaint = Complaint.objects.create(user=request.user, message=message[:4000])
    return Response({
        'message': 'Your feedback submitted successfully!',
        'complaint': _complaint_payload(complaint),
    }, status=201)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_complaints(request):
    rows = Complaint.objects.select_related('user').all()[:300]
    return Response({
        'count': Complaint.objects.count(),
        'complaints': [_complaint_payload(row, include_user=True) for row in rows],
    })


def _complaint_payload(row, include_user=False):
    data = {
        'id': row.id,
        'message': row.message,
        'created_at': row.created_at,
    }
    if include_user:
        data.update({
            'user_id': row.user_id,
            'username': row.user.username,
            'email': row.user.email,
        })
    return data


def _range_bounds(request):
    today = timezone.localdate()
    preset = request.GET.get('range', '7d')
    if preset == 'today':
        return today, today
    if preset == 'month':
        return today.replace(day=1), today
    if preset == 'custom':
        try:
            start = datetime.strptime(request.GET.get('from', ''), '%Y-%m-%d').date()
            end = datetime.strptime(request.GET.get('to', ''), '%Y-%m-%d').date()
        except ValueError:
            start, end = today - timedelta(days=6), today
        if end < start:
            start, end = end, start
        return start, end
    return today - timedelta(days=6), today


def history_rows(start, end, kind='all'):
    rows = []
    if kind in ('all', 'joining'):
        for user in User.objects.filter(created_at__date__gte=start, created_at__date__lte=end).order_by('-created_at')[:400]:
            rows.append({
                'kind': 'joining',
                'when': user.created_at,
                'user_id': user.id,
                'username': user.username,
                'detail': 'Member joined',
                'amount': '',
                'status': 'active' if user.is_active else 'inactive',
            })
    if kind in ('all', 'approval'):
        for payment in PackagePayment.objects.filter(submitted_at__date__gte=start, submitted_at__date__lte=end).select_related('user')[:400]:
            rows.append({
                'kind': 'approval',
                'when': payment.processed_at or payment.submitted_at,
                'user_id': payment.user_id,
                'username': payment.user.username,
                'detail': f'Package {payment.package_name}',
                'amount': float(payment.amount),
                'status': payment.status,
            })
    if kind in ('all', 'withdrawal'):
        for item in Withdrawal.objects.filter(created_at__date__gte=start, created_at__date__lte=end).select_related('user')[:400]:
            rows.append({
                'kind': 'withdrawal',
                'when': item.processed_at or item.created_at,
                'user_id': item.user_id,
                'username': item.user.username,
                'detail': item.payment_method,
                'amount': float(item.amount),
                'status': item.status,
            })
    if kind in ('all', 'transaction'):
        for item in Transaction.objects.filter(created_at__date__gte=start, created_at__date__lte=end).select_related('user')[:400]:
            rows.append({
                'kind': 'transaction',
                'when': item.created_at,
                'user_id': item.user_id,
                'username': item.user.username,
                'detail': item.description or item.transaction_type,
                'amount': float(item.amount),
                'status': item.transaction_type,
            })
    if kind in ('all', 'complaint'):
        for item in Complaint.objects.filter(created_at__date__gte=start, created_at__date__lte=end).select_related('user')[:400]:
            rows.append({
                'kind': 'complaint',
                'when': item.created_at,
                'user_id': item.user_id,
                'username': item.user.username,
                'detail': item.message[:180],
                'amount': '',
                'status': 'submitted',
            })
    rows.sort(key=lambda row: row['when'] or timezone.now(), reverse=True)
    return rows


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_history(request):
    start, end = _range_bounds(request)
    kind = request.GET.get('kind', 'all')
    rows = history_rows(start, end, kind)
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="instova-history.csv"'
        writer = csv.writer(response)
        writer.writerow(['When', 'Kind', 'User ID', 'Name', 'Detail', 'Amount', 'Status'])
        for row in rows:
            writer.writerow([row['when'], row['kind'], row['user_id'], row['username'], row['detail'], row['amount'], row['status']])
        return response
    return Response({
        'from': start,
        'to': end,
        'count': len(rows),
        'rows': rows[:200],
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_activity(request):
    rows = AdminActivity.objects.select_related('admin')[:100]
    return Response({'activities': [{
        'id': row.id,
        'action': row.action,
        'detail': row.detail,
        'admin': row.admin.username if row.admin else '',
        'created_at': row.created_at,
    } for row in rows]})
