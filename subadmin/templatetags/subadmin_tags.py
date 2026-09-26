from django.urls import reverse
from django.contrib.admin.utils import quote
from django.contrib.admin.templatetags.admin_modify import submit_row
from django.utils.encoding import force_str
from django.template import Library


register = Library()

@register.inclusion_tag('subadmin/breadcrumbs.html', takes_context=True)
def subadmin_breadcrumbs(context):
    request = context['request']
    opts = context['opts']
    root = {
        'name': request.subadmin.root['object']._meta.app_config.verbose_name,
        'url': reverse(
            'admin:app_list',
            kwargs={'app_label': request.subadmin.root['object']._meta.app_label},
            current_app=getattr(request, 'current_app', None),
        )
    }

    breadcrumbs =[]
    view_args = list(request.subadmin.view_args)

    i = 0
    subadmin_parents = request.subadmin.parents[::-1]

    for parent in subadmin_parents:
        adm = parent['admin']
        obj = parent['object']

        breadcrumbs.extend([{
            'name': obj._meta.verbose_name_plural,
            'url': adm.reverse_url('changelist', *view_args[:i]),
            'has_view_permission': adm.has_view_permission(request),
        }, {
            'name': force_str(obj),
            'url': adm.reverse_url('change', *view_args[:i + 1]),
            'has_view_permission': adm.has_view_permission(request, obj),
        }])
        i += 1

    return {
        'root': root,
        'breadcrumbs': breadcrumbs,
        'opts': opts,
    }

@register.simple_tag(takes_context=True)
def subadmin_url(context, viewname, *args, **kwargs):
    request = context['request']
    subadmin = request.subadmin
    view_args = subadmin.base_url_args[:-1] if subadmin.object_id else subadmin.base_url_args
    return reverse(
        'admin:%s_%s' % (subadmin.base_viewname, viewname),
        args=[quote(arg) for arg in view_args] + list(args),
        kwargs=kwargs,
        current_app=getattr(request, 'current_app', None),
    )

@register.simple_tag(takes_context=True)
def subadmin_add_preserved_filters(context, url, popup=False, to_field=None):
    adminform = context.get('adminform')
    model_admin = adminform.model_admin if adminform else context['cl'].model_admin
    return model_admin.add_preserved_filters(context, url, popup, to_field)

@register.inclusion_tag('subadmin/submit_line.html', takes_context=True)
def subadmin_submit_row(context):
    ctx = submit_row(context)
    ctx.update({
        'request': context['request']
    })
    return ctx
