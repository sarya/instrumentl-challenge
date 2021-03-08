import django_rq
from django.db import transaction
from django.forms.models import model_to_dict
from django.http import HttpResponse, JsonResponse

from .models import Award, Organization
from .parser import parse_filing


def parse_filings(request):
    Award.objects.all().delete()
    Organization.objects.all().delete()

    urls = [
        'http://s3.amazonaws.com/irs-form-990/201132069349300318_public.xml',
        'http://s3.amazonaws.com/irs-form-990/201612429349300846_public.xml',
        'http://s3.amazonaws.com/irs-form-990/201521819349301247_public.xml',
        'http://s3.amazonaws.com/irs-form-990/201641949349301259_public.xml',
        'http://s3.amazonaws.com/irs-form-990/201921719349301032_public.xml',
        'http://s3.amazonaws.com/irs-form-990/201831309349303578_public.xml',
        'http://s3.amazonaws.com/irs-form-990/201823309349300127_public.xml',
        'http://s3.amazonaws.com/irs-form-990/201401839349300020_public.xml',
        'http://s3.amazonaws.com/irs-form-990/201522139349100402_public.xml',
        'http://s3.amazonaws.com/irs-form-990/201831359349101003_public.xml',
    ]

    for u in urls:
        django_rq.enqueue(parse_filing, u)

    return HttpResponse('parsing...')


def get_filings(request):
    state = request.GET.get('state')
    
    if state:
        awards = Award.objects.filter(recipient__in=Organization.objects.filter(state=state))
    else:
        awards = Award.objects.all()

    filers = {}
    for a in awards:
        if a.filer.id not in filers:
            filers[a.filer.id] = model_to_dict(a.filer, exclude=['id'])
            filers[a.filer.id]['awards'] = []

        award_data = model_to_dict(a, exclude=['id', 'filer'])
        award_data['recipient'] = model_to_dict(a.recipient)
        filers[a.filer.id]['awards'].append(award_data)

    return JsonResponse({'filers': list(filers.values())}, json_dumps_params={'indent': 2})
