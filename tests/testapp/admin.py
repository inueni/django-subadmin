from django.contrib import admin

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
    subadmins = (
        GrandchildAdmin,
        RepeatedParentGrandchildAdmin,
        UnrelatedParentGrandchildAdmin,
    )


@admin.register(Parent)
class ParentAdmin(RootSubAdmin):
    subadmins = (ChildAdmin,)


class StringChildAdmin(SubAdmin):
    model = StringChild


@admin.register(StringParent)
class StringParentAdmin(RootSubAdmin):
    subadmins = (StringChildAdmin,)
