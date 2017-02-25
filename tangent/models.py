from __future__ import unicode_literals

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from oat.helpers import is_society_member
import os

def upload_file_to(self, filename):
    return os.path.join(
        "documents", "{name}".format(name=self.name), filename)


def meeting_upload_file_path(self, filename, classification='unknown'):
    return os.path.join("{org_name}", classification,
                        "{number}-{date}".format(org_name=self.organization.name,
                                                 number=self.number,
                                                 date=self.date.isoformat()),
                        filename)


class MemberManager(models.Manager):
    def create_member(self, username):
        user = User.objects.get_or_create(username=username)[0]
        return user.member

class Member(models.Model):
    user = models.OneToOneField(User)

    #Services
    requested_refund = models.BooleanField(default=False)
    used_resources = models.BooleanField(default=False)

    # TODO we need to determine how to handle this field properly
    do_not_email = models.BooleanField(default=False)

    # information about the member
    bio = models.TextField(default="", blank=True, null=True)
    picture = models.ImageField(blank=True, null=True, upload_to='profile_pictures')
    website = models.URLField(blank=True, null=True)

    # Will indicate interest for the current term, which will forward resume and cover letter
    interested_in = models.ManyToManyField('Position', blank=True)

    # for applications, and also so they have a place to host this stuff
    resume = models.FileField(upload_to='resumes', blank=True, null=True)
    cover_letter = models.TextField(default="", blank=True, null=True)

    objects = MemberManager()

    def __str__(self):
        return self.user.username

    def is_society_member(self):
        return is_society_member(self.user.username)

    def can_post(self):
        return self.position_set.filter(
            can_post=True
        )

    def can_edit(self):
        return self.position_set.filter(
            can_edit=True
        )

    def is_org_admin(self, org):
        for position in org.position_set.filter(is_admin=True):
            if position.occupied_by.filter(id=self.id):
                return True
        return self.user.is_staff

def attach_member(sender, instance, created, **kwargs):
    if created:
        member, created = Member.objects.get_or_create(user=instance)

post_save.connect(attach_member, sender=User)
    
class Announcement(models.Model):
    class Meta:
        permissions = (
                ("can_promote", "Can promote announcements to reach all MathSoc members (rather than members of org)"),
        )
    # determines what order posts appear on the page
    # TODO order 0 means the header
    order_key = models.IntegerField(unique=True)
    title = models.CharField(max_length=256)
    author = models.ForeignKey(Member)
    author_position = models.ForeignKey('Position')
    date = models.DateTimeField(auto_now_add=True)
    body = models.TextField()
    image = models.ImageField(blank=True, null=True)
    # a link that will be used if people want more information or to act
    # TODO implement
    action = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.title


class BaseOrg(models.Model):
    name = models.CharField(max_length=256, unique=True)
    description = models.TextField(default="", blank=True, null=True)
    office = models.CharField(max_length=32, default="MC 3038")
    website = models.URLField(default='http://mathsoc.uwaterloo.ca')
    documents = models.ManyToManyField('OrganizationDocument', default=None, blank=True)

    def __str__(self):
        return self.name

class Organization(BaseOrg):
    class Meta:
        permissions = (
                ("add_announcements", "Can post announcements belonging to org"),
                ("manage_announcement", "Can edit announcements belonging to org"),
                ("attach_positions", "Can attach members to positions/add members in the org"),
                ("add_meetings", "Can add meetings to the org"),
                ("manage_meetings", "Can manage meetings (not created by themselves) within the org"),
                ("add_documents", "Can add documents beloging to the org"),
                ("manage_documents", "Can manage documents belonging to the org"),
        )
    # Allows us to add affiliates and sponsors and such
    external = models.BooleanField(default=False)
    affiliate = models.BooleanField(default=False)
    sponsor = models.BooleanField(default=False)
   
class Club(BaseOrg):
    class Meta:
        permissions = (
                ("add_announcements", "Can post announcements belonging to org"),
                ("manage_announcement", "Can edit announcements belonging to org"),
                ("attach_positions", "Can attach members to positions/add members in the org"),
                ("add_meetings", "Can add meetings to the org"),
                ("manage_meetings", "Can manage meetings (not created by themselves) within the org"),
                ("add_documents", "Can add documents beloging to the org"),
                ("manage_documents", "Can manage documents belonging to the org"),
        )
    members = models.ManyToManyField('Member', blank=True)
    # club fee in cents
    fee = models.IntegerField(default=200)

    def fee_in_dollars(self):
        return '{:,.2f}'.format(self.fee / 100)

class OrganizationDocument(models.Model):
    name = models.CharField(max_length=256)
    description = models.TextField(default="")
    date_added = models.DateField(auto_now_add=True)
    last_modified = models.DateField(auto_now=True)

    # TODO if document is .tex generate pdf
    file = models.FileField(upload_to=upload_file_to)

    def __str__(self):
        return self.name

class Position(models.Model):
    title = models.CharField(max_length=256)
    responsibilities = models.TextField(blank=True, null=True)
    # some positions belong to multiple organizations, but they mostly have a home org
    # this is just to differentiate and determine ex-officio positions
    primary_organization = models.ForeignKey(BaseOrg, default=None, blank=True, null=True)

    # permissions
    permissions_group = models.ForeignKey(Group, default=None, blank=True, null=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    key_holder = models.BooleanField(default=False)

    # do we want to hire this position 
    want_applications = models.BooleanField(default=False)

    def __str__(self):
        return self.title + " - " + self.primary_organization.name

    def occupied_by(self, term=settings.CURRENT_TERM):
        return self.positionholder_set.filter(term=term)

class PositionHolder(models.Model):
    term = models.IntegerField(default=settings.CURRENT_TERM)
    position = models.ForeignKey(Position)
    occupied_by = models.ForeignKey(Member)

def attach_position(sender, instance, created, **kwargs):
    if created:
        group = instance.position.permissions_group
        if group and instance.term == settings.CURRENT_TERM:
            user = instance.occupied_by.user
            group.user_set.add(user)
            if instance.position.is_staff or instance.position.is_superuser:
                user.is_staff = instance.position.is_staff or user.is_staff
                user.is_superuser = instance.position.is_superuser or user.is_superuser
                user.save()

post_save.connect(attach_position, sender=PositionHolder)

class Scholarship(models.Model):
    name = models.CharField(max_length=256)
    organization = models.CharField(max_length=256)
    #TODO amount should maybe be a char field for ranges
    amount = models.IntegerField()
    description = models.TextField(default="")
    website = models.URLField(default="")

    def __str__(self):
        return self.name


class Meeting(models.Model):
    date = models.DateField()
    location = models.CharField(max_length=256, default="Comfy Lounge")
    organization = models.ForeignKey('Organization')
    term = models.CharField(choices=(
        ('W', 'Winter'),
        ('S', 'Spring'),
        ('F', 'Fall')
    ), max_length=2)
    general = models.BooleanField(default=False)
    budget = models.BooleanField(default=False)

    agenda = models.FileField(upload_to=meeting_upload_file_path, blank=True, null=True)
    minutes = models.FileField(upload_to=meeting_upload_file_path, blank=True, null=True)
    budget_file = models.FileField(upload_to=meeting_upload_file_path, blank=True, null=True)

    attendance = models.ManyToManyField('Member', blank=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return self.date.isoformat()


# TODO This may be unnecessary... However it makes me think of something else
class Log(models.Model):
    title = models.CharField(max_length=128)
    datetime = models.DateTimeField(auto_now_add=True)
    body = models.TextField()
    user = models.ForeignKey(Member)

    def __str__(self):
        return self.title
