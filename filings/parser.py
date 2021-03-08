import re
from urllib.request import urlopen

import xmltodict
from django.db import transaction

from .models import Award, Organization


def _fetch_field(data, possible_field_names, error_if_missing=True):
    current_value = data
    found_fields = [False] * len(possible_field_names)

    for i, p in enumerate(possible_field_names):
        for f in p:
            if f in current_value:
                current_value = current_value[f]
                found_fields[i] = True
                break

    if not all(found_fields):
        if not error_if_missing:
            return ''
        
        raise Exception(f'Missing value for expected field path: {possible_field_names}')

    return current_value


def _fetch_address_fields(data):
    return {
        'address_line_1': _fetch_field(data, [['AddressLine1Txt', 'AddressLine1']]),
        'city': _fetch_field(data, [['CityNm', 'City']]),
        'state': _fetch_field(data, [['StateAbbreviationCd', 'State']]),
        'zipcode': _fetch_field(data, [['ZIPCd', 'ZIPCode']]),
    }


def _parse_filer(filing_tree):
    filer = filing_tree['Return']['ReturnHeader']['Filer']
    filer_data = {
        'ein': re.sub('[^0-9]', '', filer['EIN']),
        'name': _fetch_field(filer, [['BusinessName', 'Name'], ['BusinessNameLine1Txt', 'BusinessNameLine1']]),
    }
    filer_data.update(_fetch_address_fields(filer['USAddress']))

    return filer_data


def _parse_recipient(recipient_tree):
    recipient_data = {
        'ein': re.sub('[^0-9]', '', _fetch_field(recipient_tree, [['RecipientEIN', 'EINOfRecipient']], error_if_missing=False)),
        'name': _fetch_field(recipient_tree, [['RecipientBusinessName', 'RecipientNameBusiness'], ['BusinessNameLine1Txt', 'BusinessNameLine1']]),
    }
    recipient_address = _fetch_field(recipient_tree, [['USAddress', 'AddressUS']])
    recipient_data.update(_fetch_address_fields(recipient_address))

    return recipient_data


def parse_filing(url):
    with transaction.atomic():
        filing_tree = xmltodict.parse(urlopen(url))

        filer_data = _parse_filer(filing_tree)
        filer_model, _ = Organization.objects.get_or_create(**filer_data)

        for recipient_tree in filing_tree['Return']['ReturnData'].get('IRS990ScheduleI', {}).get('RecipientTable', []):
            recipient_data = _parse_recipient(recipient_tree)
            recipient_model, _ = Organization.objects.get_or_create(**recipient_data)

            award = Award(
                filer=filer_model,
                recipient=recipient_model,
                purpose=_fetch_field(recipient_tree, [['PurposeOfGrantTxt', 'PurposeOfGrant']]),
                amount_dollars=int(_fetch_field(recipient_tree, [['CashGrantAmt', 'AmountOfCashGrant']])),
                filing_url=url,
            )
            award.save()
