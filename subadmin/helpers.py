from django.contrib.admin.utils import unquote
from django.core.exceptions import FieldDoesNotExist
from django.http import Http404
from django.utils.functional import cached_property


class SubAdminHelper:
    def __init__(self, sub_admin, view_args, parents, object_id=None):
        self.parents = list(parents)
        self.lookup_kwargs = {}
        self.related_instances = {}
        self.object_id = object_id
        self.view_args = view_args
        self.base_viewname = sub_admin.get_base_viewname()
        nested_model = sub_admin.model
        fk_lookup = sub_admin.fk_name

        for parent in self.parents:
            obj = parent["object"]
            self.lookup_kwargs[fk_lookup] = obj
            try:
                field = nested_model._meta.get_field(sub_admin.fk_name)
            except FieldDoesNotExist:
                pass
            else:
                if (
                    field.concrete
                    and (field.many_to_one or field.one_to_one)
                    and isinstance(obj, field.remote_field.model)
                ):
                    self.related_instances.setdefault(sub_admin.fk_name, obj)

            sub_admin = parent["admin"]
            if getattr(sub_admin, "parent_admin", None):
                fk_lookup = f"{fk_lookup}__{sub_admin.fk_name}"

        for parent, ancestor in zip(self.parents, self.parents[1:]):
            obj = parent["object"]
            parent_field = obj._meta.get_field(parent["admin"].fk_name)
            expected = getattr(ancestor["object"], parent_field.target_field.attname)
            if getattr(obj, parent_field.attname) != expected:
                raise Http404

    @cached_property
    def parent(self):
        return self.parents[0]

    @cached_property
    def root(self):
        return self.parents[-1]

    @cached_property
    def parent_instance(self):
        return self.parent["object"]

    @cached_property
    def base_url_args(self):
        return [unquote(arg) for arg in self.view_args]
