from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.contrib.admin.templatetags.admin_modify import submit_row
from django.utils.encoding import force_text
from django.template import Library


register = Library()

@register.inclusion_tag('subadmin/breadcrumbs.html', takes_context=True)
def subadmin_breadcrumbs(context):
    request = context['request']
    opts = context['opts']
    root = {
        'name': request.subadmin.root['object']._meta.app_config.verbose_name,
        'url': reverse('admin:app_list', kwargs={'app_label': request.subadmin.root['object']._meta.app_label})
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
            'has_change_permission': adm.has_change_permission(request),
        }, {
            'name': force_text(obj),
            'url': adm.reverse_url('change', *view_args[:i + 1]),
            'has_change_permission': adm.has_change_permission(request, obj),
        }])
        i += 1
    
    return {
        'root': root,
        'breadcrumbs': breadcrumbs,
        'opts': opts,
    }

@register.simple_tag(takes_context=True)
def subadmin_url(context, viewname, *args, **kwargs):
    subadmin = context['request'].subadmin
    view_args = subadmin.base_url_args[:-1] if subadmin.object_id else subadmin.base_url_args
    return reverse('admin:%s_%s' % (subadmin.base_viewname, viewname), args=view_args + list(args), kwargs=kwargs)

@register.inclusion_tag('subadmin/submit_line.html', takes_context=True)
def subadmin_submit_row(context):
    ctx = submit_row(context)    
    ctx.update({
        'request': context['request']
    })
    return ctx