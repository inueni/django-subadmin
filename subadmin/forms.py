from django.forms.widgets import HiddenInput
from django.forms.models import ModelChoiceField


class SubAmdinFormMixin(object):
    """
    Helper form mixin to correclty handle validation with foreign-key
    """

    def _get_validation_exclusions(self):
        exclude = super()._get_validation_exclusions()
        return [exclude_field for exclude_field in exclude if exclude_field not in self._related_instances.keys()]

    def validate_unique(self):
        for fk_field, fk_instance in self._related_instances.items():
            if fk_field in self._meta.model._meta._forward_fields_map.keys():
                setattr(self.instance, fk_field, fk_instance)
        super().validate_unique()


def get_form(base_form, model, related_instances):
    """
    Helper to return correctly configured ModelForm with foreignkeys
    """
    attrs = {'_related_instances': related_instances}
    for fk_field, fk_instance in related_instances.items():
        if fk_field in model._meta._forward_fields_map.keys():
            fk_queryset = type(fk_instance)._default_manager.get_queryset().filter(pk=fk_instance.pk)
            attrs[fk_field] = ModelChoiceField(
                fk_queryset,
                initial=fk_instance,
                limit_choices_to={'pk': fk_instance.pk},
                widget=HiddenInput()
            )
    return type(base_form)(base_form.__name__, (SubAmdinFormMixin, base_form), attrs)