import json
from collections import OrderedDict
from functools import partial, update_wrapper
from urllib.parse import parse_qsl, urlparse, urlunparse

from django.urls import path, re_path, include
from django.core.exceptions import ValidationError
from django.contrib.admin.options import IS_POPUP_VAR, TO_FIELD_VAR
from django.contrib.admin.utils import unquote, quote
from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.views.main import ChangeList
from django.contrib.admin.actions import delete_selected
from django.db import transaction
from django.forms.models import _get_foreign_key
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.http import urlencode
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_protect
from django.urls import Resolver404, get_script_prefix, resolve, reverse

csrf_protect_m = method_decorator(csrf_protect)

__all__ = ('SubAdmin', 'RootSubAdmin', 'SubAdminMixin', 'RootSubAdminMixin', 'SubAdminChangeList', 'SubAdminHelper', 'SubAdminFormMixin')


class SubAdminHelper(object):
    def __init__(self, sub_admin, view_args, object_id=None):
        self.parents = []
        self.lookup_kwargs = {}
        self.related_instances = OrderedDict()
        self.object_id = object_id
        self.view_args = view_args
        self.base_viewname = sub_admin.get_base_viewname()
        self.load_tree(sub_admin)

    def load_tree(self, sub_admin):
        parent_admin = sub_admin.parent_admin
        fk_lookup = sub_admin.fk_name

        i = 2 if self.object_id else 1
        while parent_admin:
            obj = sub_admin.get_parent_instance(self.view_args[-i])
            self.parents.append({
                'admin': parent_admin,
                'object': obj,
            })
            self.lookup_kwargs[fk_lookup] = obj
            self.related_instances[sub_admin.fk_name] = obj

            sub_admin = parent_admin
            parent_admin = getattr(sub_admin, 'parent_admin', None)
            if parent_admin:
                fk_lookup = '%s__%s' % (fk_lookup, sub_admin.fk_name)

            i += 1

    @cached_property
    def parent(self):
        return self.parents[0]

    @cached_property
    def root(self):
        return self.parents[-1]

    @cached_property
    def parent_instance(self):
        return self.parent['object']

    @cached_property
    def base_url_args(self):
        return [unquote(arg) for arg in self.view_args]


class SubAdminChangeList(ChangeList):
    def __init__(self, request, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.request = request

    def url_for_result(self, result):
        pk = getattr(result, self.pk_attname)
        return self.model_admin.reverse_url('change', *self.model_admin.get_base_url_args(self.request) + [pk])


class SubAdminFormMixin(object):
    def _post_clean(self):
        validate_unique = self._validate_unique
        self._validate_unique = False
        super()._post_clean()

        for fk_field, fk_instance in self._related_instances_fields.items():
            setattr(self.instance, fk_field, fk_instance)

        self._validate_unique = validate_unique
        if self._validate_unique:
            self.validate_unique()


    def validate_unique(self):
        exclude = self._get_subadmin_validation_exclusions()

        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError as e:
            self._update_errors(e)

    def _get_subadmin_validation_exclusions(self):
        return [f for f in self._get_validation_exclusions() if f not in self._related_instances_fields.keys()]

    @cached_property
    def _related_instances_fields(self):
        return {
            key: self._related_instances[key] for key in self._related_instances.keys() if key in self._meta.model._meta._forward_fields_map.keys()
        }


class SubAdminBase(object):
    subadmins = None

    def get_subadmin_instances(self):
        return [modeladmin_class(self.model, self) for modeladmin_class in self.subadmins or []]

    def get_subadmin_urls(self):
        urlpatterns = []

        for modeladmin in self.subadmin_instances:
            regex = r'^(.+)/%s/' % modeladmin.model._meta.model_name

            urls = [
                re_path(regex , include(modeladmin.urls))
            ]

            urlpatterns += urls

        return urlpatterns

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        subadmin_links = []
        if obj:
            for modeladmin in self.subadmin_instances:
                if modeladmin.has_change_permission(request):
                    url_args = modeladmin.get_base_url_args(request) or [obj.pk]
                    subadmin_links.append({
                        'name': modeladmin.model._meta.verbose_name_plural,
                        'url': modeladmin.reverse_url('changelist', *url_args),
                    })

        context.update({'subadmin_links': subadmin_links})
        return super().render_change_form(request, context, add=add, change=change,
                                                                      form_url=form_url, obj=obj)


class SubAdminMixin(SubAdminBase):
    model = None
    fk_name = None

    change_list_template = 'subadmin/change_list.html'
    change_form_template = 'subadmin/change_form.html'
    delete_confirmation_template = 'subadmin/delete_confirmation.html'
    delete_selected_confirmation_template = 'subadmin/delete_selected_confirmation.html'
    object_history_template = 'subadmin/object_history.html'
    subadmin_helper_class = SubAdminHelper

    def __init__(self, parent_model, parent_admin):
        self.parent_model = parent_model
        self.parent_admin = parent_admin

        if self.fk_name is None:
            self.fk_name = _get_foreign_key(parent_model, self.model).name

        super().__init__(self.model, parent_admin.admin_site)

        self.subadmin_instances = self.get_subadmin_instances()

    def get_subadmin_helper(self, view_args, object_id=None):
        return self.subadmin_helper_class(self, view_args, object_id=object_id)

    def get_model_perms(self, request):
        return super().get_model_perms(request)

    def get_actions(self, request):
        actions = super().get_actions(request)

        def subadmin_delete_selected(modeladmin, req, qs):
            response = delete_selected(modeladmin, req, qs)
            if response:
                response.context_data.update(self.context_add_parent_data(request))
            return response

        if 'delete_selected' in actions:
            actions['delete_selected'] = (subadmin_delete_selected, 'delete_selected', actions['delete_selected'][2])

        return actions

    def get_changelist(self, request, **kwargs):
        return SubAdminChangeList

    def get_urls(self):
        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        base_viewname = self.get_base_viewname()

        urlpatterns = [
            path('' , include(self.get_subadmin_urls())),
            path('', wrap(self.changelist_view), name='%s_changelist' % base_viewname),
            path('add/', wrap(self.add_view), name='%s_add' % base_viewname),
            re_path(r'^(.+)/history/$', wrap(self.history_view), name='%s_history' % base_viewname),
            re_path(r'^(.+)/delete/$', wrap(self.delete_view), name='%s_delete' % base_viewname),
            re_path(r'^(.+)/change/$', wrap(self.change_view), name='%s_change' % base_viewname),
        ]

        urlpatterns =  urlpatterns
        return urlpatterns

    def get_queryset(self, request):
        lookup_kwargs = request.subadmin.lookup_kwargs
        return super().get_queryset(request).filter(**lookup_kwargs)

    def get_exclude(self, request, obj=None):
        exclude = super().get_exclude(request, obj)
        exclude = list(exclude) if exclude else []
        exclude.extend(request.subadmin.related_instances.keys())
        return list(set(exclude))

    def prep_subadmin_form(self, request, form):
        attrs = {'_related_instances': request.subadmin.related_instances}
        return type(form)(form.__name__, (SubAdminFormMixin, form), attrs)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        return self.prep_subadmin_form(request, form)

    def get_changelist_form(self, request, **kwargs):
        form = super().get_changelist_form(request, **kwargs)
        return self.prep_subadmin_form(request, form)

    def get_base_viewname(self):
        if hasattr(self.parent_admin, 'get_base_viewname'):
            base_viewname = self.parent_admin.get_base_viewname()
        else:
            base_viewname = '%s_%s' % (self.parent_model._meta.app_label, self.parent_model._meta.model_name)

        return '%s_%s' % (base_viewname, self.model._meta.model_name)

    def reverse_url(self, viewname, *args, **kwargs):
        return reverse('admin:%s_%s' % (self.get_base_viewname(), viewname), args=args, kwargs=kwargs,
                       current_app=self.admin_site.name)

    def get_base_url_args(self, request):
        if hasattr(request, 'subadmin'):
            return request.subadmin.base_url_args
        return []

    def context_add_parent_data(self, request, context=None):
        context = context or {}
        parent_instance = request.subadmin.parent_instance
        context.update({
            'parent_instance': parent_instance,
            'parent_opts': parent_instance._meta,
        })
        return context

    def get_parent_instance(self, parent_id):
        return get_object_or_404(self.parent_model, pk=unquote(parent_id))

    def get_preserved_filters(self, request):
        match = request.resolver_match
        if self.preserve_filters and match:
            current_url = '%s:%s' % (match.app_name, match.url_name)
            changelist_url = 'admin:%s_changelist' % self.get_base_viewname()
            if current_url == changelist_url:
                preserved_filters = request.GET.urlencode()
            else:
                preserved_filters = request.GET.get('_changelist_filters')

            if preserved_filters:
                return urlencode({'_changelist_filters': preserved_filters})
        return ''

    def add_preserved_filters(self, context, url, popup=False, to_field=None):
        opts = context.get('opts')
        preserved_filters = context.get('preserved_filters')

        parsed_url = list(urlparse(url))
        parsed_qs = dict(parse_qsl(parsed_url[4]))
        merged_qs = dict()

        if opts and preserved_filters:
            preserved_filters = dict(parse_qsl(preserved_filters))

            match_url = '/%s' % url.partition(get_script_prefix())[2]
            try:
                match = resolve(match_url)
            except Resolver404:
                pass
            else:
                current_url = '%s:%s' % (match.app_name, match.url_name)
                changelist_url = 'admin:%s_changelist' % self.get_base_viewname()
                if changelist_url == current_url and '_changelist_filters' in preserved_filters:
                    preserved_filters = dict(parse_qsl(preserved_filters['_changelist_filters']))

            merged_qs.update(preserved_filters)

        if popup:
            from django.contrib.admin.options import IS_POPUP_VAR
            merged_qs[IS_POPUP_VAR] = 1
        if to_field:
            from django.contrib.admin.options import TO_FIELD_VAR
            merged_qs[TO_FIELD_VAR] = to_field

        merged_qs.update(parsed_qs)

        parsed_url[4] = urlencode(merged_qs)
        return urlunparse(parsed_url)

    @csrf_protect_m
    def changelist_view(self, request, *args, **kwargs):
        extra_context = kwargs.get('extra_context')
        request.subadmin = SubAdminHelper(self, args)
        extra_context = self.context_add_parent_data(request, extra_context)
        return super().changelist_view(request, extra_context)

    def add_view(self, request, *args, **kwargs):
        form_url, extra_context = kwargs.get('form_url', ''), kwargs.get('extra_context')
        request.subadmin = SubAdminHelper(self, args)
        extra_context = self.context_add_parent_data(request, extra_context)
        return super().add_view(request, form_url, extra_context)

    def change_view(self, request, *args, **kwargs):
        form_url, extra_context = kwargs.get('form_url', ''), kwargs.get('extra_context')
        object_id = args[-1]
        request.subadmin = SubAdminHelper(self, args, object_id=object_id)
        extra_context = self.context_add_parent_data(request, extra_context)
        return super().change_view(request, object_id, form_url, extra_context)

    @csrf_protect_m
    @transaction.atomic
    def delete_view(self, request, *args, **kwargs):
        extra_context = kwargs.get('extra_context')
        object_id = args[-1]
        request.subadmin = SubAdminHelper(self, args, object_id=object_id)
        extra_context = self.context_add_parent_data(request, extra_context)
        return super().delete_view(request, object_id, extra_context)

    def history_view(self, request, *args, **kwargs):
        extra_context = kwargs.get('extra_context')
        object_id = args[-1]
        request.subadmin = SubAdminHelper(self, args, object_id=object_id)
        extra_context = self.context_add_parent_data(request, extra_context)
        return super().history_view(request, object_id, extra_context)

    def response_add(self, request, obj, post_url_continue=None):
        opts = obj._meta
        pk_value = obj._get_pk_val()
        preserved_filters = self.get_preserved_filters(request)
        url_args = self.get_base_url_args(request)

        if "_saveasnew" in request.POST:
            url_args = url_args[:-1]

        obj_url = self.reverse_url('change', *url_args + [quote(pk_value)])

        if self.has_change_permission(request, obj):
            obj_repr = format_html('<a href="{}">{}</a>', obj_url, obj)
        else:
            obj_repr = str(obj)

        msg_dict = {
            'name': opts.verbose_name,
            'obj': obj_repr,
        }

        if IS_POPUP_VAR in request.POST:
            to_field = request.POST.get(TO_FIELD_VAR)
            if to_field:
                attr = str(to_field)
            else:
                attr = obj._meta.pk.attname
            value = obj.serializable_value(attr)
            popup_response_data = json.dumps({
                'value': str(value),
                'obj': str(obj),
            })
            return TemplateResponse(request, self.popup_response_template or [
                'admin/%s/%s/popup_response.html' % (opts.app_label, opts.model_name),
                'admin/%s/popup_response.html' % opts.app_label,
                'admin/popup_response.html',
            ], {
                'popup_response_data': popup_response_data,
            })

        elif "_continue" in request.POST or (
                "_saveasnew" in request.POST and self.save_as_continue and
                self.has_change_permission(request, obj)
        ):
            msg = format_html(
                _('The {name} "{obj}" was added successfully. You may edit it again below.'),
                **msg_dict
            )
            self.message_user(request, msg, messages.SUCCESS)
            if post_url_continue is None:
                post_url_continue = obj_url
            post_url_continue = self.add_preserved_filters(
                {'preserved_filters': preserved_filters, 'opts': opts},
                post_url_continue
            )
            return HttpResponseRedirect(post_url_continue)

        elif "_addanother" in request.POST:
            msg = format_html(
                _('The {name} "{obj}" was added successfully. You may add another {name} below.'),
                **msg_dict
            )
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = request.path
            redirect_url = self.add_preserved_filters({'preserved_filters': preserved_filters, 'opts': opts}, redirect_url)
            return HttpResponseRedirect(redirect_url)

        else:
            msg = format_html(
                _('The {name} "{obj}" was added successfully.'),
                **msg_dict
            )
            self.message_user(request, msg, messages.SUCCESS)
            return self.response_post_save_add(request, obj)

    def response_change(self, request, obj):
        if IS_POPUP_VAR in request.POST:
            to_field = request.POST.get(TO_FIELD_VAR)
            attr = str(to_field) if to_field else obj._meta.pk.attname
            value = request.resolver_match.args[0]
            new_value = obj.serializable_value(attr)
            popup_response_data = json.dumps({
                'action': 'change',
                'value': str(value),
                'obj': str(obj),
                'new_value': str(new_value),
            })
            return TemplateResponse(request, self.popup_response_template or [
                'admin/%s/%s/popup_response.html' % (opts.app_label, opts.model_name),
                'admin/%s/popup_response.html' % opts.app_label,
                'admin/popup_response.html',
            ], {
                'popup_response_data': popup_response_data,
            })

        opts = self.model._meta
        pk_value = obj._get_pk_val()
        preserved_filters = self.get_preserved_filters(request)

        msg_dict = {
            'name': str(opts.verbose_name),
            'obj': format_html('<a href="{}">{}</a>', request.path, obj),
        }
        if "_continue" in request.POST:
            msg = format_html(
                _('The {name} "{obj}" was changed successfully. You may edit it again below.'),
                **msg_dict
            )
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = request.path
            redirect_url = self.add_preserved_filters({'preserved_filters': preserved_filters, 'opts': opts}, redirect_url)
            return HttpResponseRedirect(redirect_url)

        elif "_saveasnew" in request.POST:
            msg = format_html(
                _('The {name} "{obj}" was added successfully. You may edit it again below.'),
                **msg_dict
            )
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = self.reverse_url('change', *self.get_base_url_args(request))
            redirect_url = self.add_preserved_filters({'preserved_filters': preserved_filters, 'opts': opts}, redirect_url)
            return HttpResponseRedirect(redirect_url)

        elif "_addanother" in request.POST:
            msg = format_html(
                _('The {name} "{obj}" was changed successfully. You may add another {name} below.'),
                **msg_dict
            )
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = self.reverse_url('add', *self.get_base_url_args(request)[:-1])
            redirect_url = self.add_preserved_filters({'preserved_filters': preserved_filters, 'opts': opts}, redirect_url)
            return HttpResponseRedirect(redirect_url)

        else:
            msg = format_html(
                _('The {name} "{obj}" was changed successfully.'),
                **msg_dict
            )
            self.message_user(request, msg, messages.SUCCESS)
        return self.response_post_save_change(request, obj)

    def response_post_save_add(self, request, obj):
        opts = self.model._meta
        if self.has_change_permission(request, None):
            post_url = self.reverse_url('changelist', *self.get_base_url_args(request))
            preserved_filters = self.get_preserved_filters(request)
            post_url = self.add_preserved_filters({'preserved_filters': preserved_filters, 'opts': opts}, post_url)
        else:
            post_url = reverse('admin:index', current_app=self.admin_site.name)
        return HttpResponseRedirect(post_url)

    def response_post_save_change(self, request, obj):
        opts = self.model._meta

        if self.has_change_permission(request, None):
            post_url = self.reverse_url('changelist', *self.get_base_url_args(request)[:-1])
            preserved_filters = self.get_preserved_filters(request)
            post_url = self.add_preserved_filters({'preserved_filters': preserved_filters, 'opts': opts}, post_url)
        else:
            post_url = reverse('admin:index', current_app=self.admin_site.name)
        return HttpResponseRedirect(post_url)

    def response_delete(self, request, obj_display, obj_id):
        opts = self.model._meta

        if IS_POPUP_VAR in request.POST:
            popup_response_data = json.dumps({
                'action': 'delete',
                'value': str(obj_id),
            })
            return TemplateResponse(request, self.popup_response_template or [
                'admin/%s/%s/popup_response.html' % (opts.app_label, opts.model_name),
                'admin/%s/popup_response.html' % opts.app_label,
                'admin/popup_response.html',
            ], {
                'popup_response_data': popup_response_data,
            })

        self.message_user(
            request,
            _('The %(name)s "%(obj)s" was deleted successfully.') % {
                'name': str(opts.verbose_name),
                'obj': str(obj_display),
            },
            messages.SUCCESS,
        )

        if self.has_change_permission(request, None):
            post_url = self.reverse_url('changelist', *self.get_base_url_args(request)[:-1])
            preserved_filters = self.get_preserved_filters(request)
            post_url = self.add_preserved_filters(
                {'preserved_filters': preserved_filters, 'opts': opts}, post_url
            )
        else:
            post_url = reverse('admin:index', current_app=self.admin_site.name)
        return HttpResponseRedirect(post_url)


class RootSubAdminMixin(SubAdminBase):
    change_form_template = 'subadmin/parent_change_form.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subadmin_instances = self.get_subadmin_instances()

    def get_urls(self):
        return self.get_subadmin_urls() + super().get_urls()

    def reverse_url(self, viewname, *args, **kwargs):
        info = self.model._meta.app_label, self.model._meta.model_name, viewname
        return reverse('admin:%s_%s_%s' % info, args=args, kwargs=kwargs, current_app=self.admin_site.name)


class SubAdmin(SubAdminMixin, admin.ModelAdmin):
    pass


class RootSubAdmin(RootSubAdminMixin, admin.ModelAdmin):
    pass