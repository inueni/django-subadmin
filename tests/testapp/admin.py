from django.contrib import admin

from subadmin import RootSubAdmin, SubAdmin

from .models import Child, Grandchild, Parent, StringChild, StringParent


class GrandchildAdmin(SubAdmin):
    model = Grandchild


class ChildAdmin(SubAdmin):
    model = Child
    subadmins = [GrandchildAdmin]


@admin.register(Parent)
class ParentAdmin(RootSubAdmin):
    subadmins = [ChildAdmin]


class StringChildAdmin(SubAdmin):
    model = StringChild


@admin.register(StringParent)
class StringParentAdmin(RootSubAdmin):
    subadmins = [StringChildAdmin]
