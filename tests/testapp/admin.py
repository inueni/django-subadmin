from django.contrib import admin
from django.contrib.admin import ActionLocation

from subadmin import RootSubAdmin, SubAdmin

from .models import (
    Child,
    Grandchild,
    Parent,
    RepeatedParentGrandchild,
    StringChild,
    StringParent,
    UnrelatedParentGrandchild,
)


class GrandchildAdmin(SubAdmin):
    model = Grandchild


class RepeatedParentGrandchildAdmin(SubAdmin):
    model = RepeatedParentGrandchild


class UnrelatedParentGrandchildAdmin(SubAdmin):
    model = UnrelatedParentGrandchild


class ChildAdmin(SubAdmin):
    model = Child
    actions = ("mark_actioned",)
    subadmins = (
        GrandchildAdmin,
        RepeatedParentGrandchildAdmin,
        UnrelatedParentGrandchildAdmin,
    )

    @admin.action(description="Mark as actioned", location=ActionLocation.CHANGE_FORM)
    def mark_actioned(self, request, queryset):
        queryset.update(name="Actioned")


@admin.register(Parent)
class ParentAdmin(RootSubAdmin):
    subadmins = (ChildAdmin,)


class StringChildAdmin(SubAdmin):
    model = StringChild


@admin.register(StringParent)
class StringParentAdmin(RootSubAdmin):
    subadmins = (StringChildAdmin,)
