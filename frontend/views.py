from __future__ import unicode_literals
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.models import User
from tangent.models import Position, Member, Organization, Club, PositionHolder
import logging

logger = logging.getLogger(__name__)

# ---------- HELPERS -----------------

def get_all_orgs_from_positions(positions):
    orgs = {}
    for pos in positions:
        org = pos.primary_organization
        if org.name in orgs:
            orgs[org.name]['positions'].append(pos)
        else:
            orgs[org.name] = {
                'description': org.description,
                'positions': [pos]
            }
    return orgs

# --------- View Functions ------------

def index(request):
    return render(request, 'frontend/index.html')


def governance(request):
    gov = Organization.objects.all() 
    positions = []
    for org in gov:
        positions += org.position_set.all()
    position_holders = PositionHolder.get_position_and_holders_list(positions)
    context_dict = {'orgs': gov, 'position_holders': position_holders}
    return render(request, 'frontend/governance.html', context_dict)


def organization(request, org_id):
    org = Organization.objects.get(id=org_id)
    positions = org.position_set.all()
    position_holders = PositionHolder.get_position_and_holders_list(positions)
    context_dict = {
        'org' : org,
        'position_holders': position_holders
    }
    return render(request,
                  'frontend/organization.html',
                  context_dict)


def office(request):
    org = None
    try:
        org = Organization.objects.get(name="MathSoc Office")
    except Organization.DoesNotExist:
        logger.error("org DNE")

    context_dict = {
        'org': org
    }
    return render(request, 'frontend/office.html', context_dict)


def volunteers(request):
    free_positions = Position.objects.filter(
        positionholder=None,
        want_applications=True
    ).select_related('primary_organization__name', 'primary_organization__description')
    occupied_positions = Position.objects.exclude(
        positionholder=None
    ).select_related('primary_organization__name', 'primary_organization__description')
    context_dict = {'free_position_orgs': get_all_orgs_from_positions(free_positions),
                    'occupied_position_orgs': get_all_orgs_from_positions(occupied_positions)}
    return render(request, 'frontend/volunteers.html', context_dict)

def position(request, pos_id):
    pos = Position.objects.get(id=pos_id)
    context_dict = {
        'pos': pos
    }
    return render(request, 'frontend/position.html', context_dict)


def clubs(request):
    c = Club.objects.all() 
    context_dict = {'clubs': c}
    return render(request, 'frontend/clubs.html', context_dict)

def club(request, club_id):
    club = Club.objects.get(id=club_id)
    positions = club.position_set.all()
    position_holders = PositionHolder.get_position_and_holders_list(positions)
    context_dict = {
        'club': club,
        'position_holders': position_holders
    }
    return render(request, 'frontend/club.html', context_dict)

def contact(request):
    return render(request, 'frontend/contact.html')
