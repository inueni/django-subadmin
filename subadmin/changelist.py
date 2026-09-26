from django.contrib.admin.utils import quote
from django.contrib.admin.views.main import ChangeList


class SubAdminChangeList(ChangeList):
    def __init__(self, request, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.request = request

    def url_for_result(self, result):
        pk = getattr(result, self.pk_attname)
        url_args = self.model_admin.get_base_url_args(self.request) + [pk]
        return self.model_admin.reverse_url("change", *[quote(arg) for arg in url_args])
