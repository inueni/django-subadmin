from django.core.exceptions import NON_FIELD_ERRORS, FieldDoesNotExist, ValidationError
from django.utils.functional import cached_property


class SubAdminFormMixin:
    def _post_clean(self):
        for fk_field, fk_instance in self._related_instances_fields.items():
            setattr(self.instance, fk_field, fk_instance)
        super()._post_clean()

    def _get_validation_exclusions(self):
        return (
            super()._get_validation_exclusions() - self._related_instances_fields.keys()
        )

    def _update_errors(self, errors):
        if hasattr(errors, "error_dict"):
            error_dict = {
                name: list(messages) for name, messages in errors.error_dict.items()
            }
            for name in self._related_instances_fields.keys() - self.fields.keys():
                if name in error_dict:
                    error_dict.setdefault(NON_FIELD_ERRORS, []).extend(
                        error_dict.pop(name)
                    )
            errors = ValidationError(error_dict)
        super()._update_errors(errors)

    @cached_property
    def _related_instances_fields(self):
        fields = {}
        for name, instance in self._related_instances.items():
            try:
                field = self._meta.model._meta.get_field(name)
            except FieldDoesNotExist:
                continue
            if field.concrete:
                fields[name] = instance
        return fields
