from django.contrib import admin

from .base import RootSubAdminMixin, SubAdminMixin
from .base import SubAdminBase as SubAdminBase
from .changelist import SubAdminChangeList
from .forms import SubAdminFormMixin
from .helpers import SubAdminHelper

__all__ = (
    "RootSubAdmin",
    "RootSubAdminMixin",
    "SubAdmin",
    "SubAdminChangeList",
    "SubAdminFormMixin",
    "SubAdminHelper",
    "SubAdminMixin",
)


class SubAdmin(SubAdminMixin, admin.ModelAdmin):
    pass


class RootSubAdmin(RootSubAdminMixin, admin.ModelAdmin):
    pass
