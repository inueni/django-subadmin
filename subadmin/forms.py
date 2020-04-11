from django.core.exceptions import ValidationError
from django.forms.widgets import HiddenInput
from django.forms.models import ModelChoiceField


class SubAmdinFormMixin(object):
    """
    Helper form mixin to correclty handle validation with foreign-key
    """
    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        # re-add foreing-key for unique-validation
        for fk_field, fk_instance in self._related_instances.items():
            if fk_field in self._meta.model._meta._forward_fields_map and fk_field in exclude:
                exclude.remove(fk_field)
                # also set model attribute
                setattr(self.instance, fk_field, fk_instance)

        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError as e:
            self._update_errors(e)


def get_form(base_form, model, related_instances):
    """
    Helper to return correctly configured ModelForm with foreignkeys
    """
    attrs = {'_related_instances': related_instances}
    return type(base_form)(base_form.__name__, (SubAmdinFormMixin, base_form), attrs)