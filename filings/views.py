import json

import django_rq
import redis
from django.db import transaction
from django.forms.models import model_to_dict
from django.http import HttpResponse, JsonResponse

from challenge.settings import REDIS_URL

from .models import Award, Organization
from .parser import parse_filing


r = redis.Redis.from_url(REDIS_URL)


def parse_filings(request):
    r.flushall()

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

    return HttpResponse('parsing initiated')


def _get_filings_async(state):
    if state != 'ALL':
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

    r.set(state, json.dumps({'filers': list(filers.values())}))


def get_filings(request):
    state = request.GET.get('state') or 'ALL'
    if r.exists(state):
        state_data = json.loads(r.get(state))
        return JsonResponse(state_data, json_dumps_params={'indent': 2})

    django_rq.enqueue(_get_filings_async, state)
    return HttpResponse('generating data, please wait a few seconds and refresh...')
