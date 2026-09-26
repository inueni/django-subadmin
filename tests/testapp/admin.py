from django.contrib import admin

from subadmin import RootSubAdmin, SubAdmin

from .models import Child, Grandchild, Parent


class GrandchildAdmin(SubAdmin):
    model = Grandchild


class ChildAdmin(SubAdmin):
    model = Child
    subadmins = [GrandchildAdmin]


@admin.register(Parent)
class ParentAdmin(RootSubAdmin):
    subadmins = [ChildAdmin]
