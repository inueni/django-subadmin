# django-subadmin

`django-subadmin` provides a special kind of `ModelAdmin`, called `SubAdmin`, that allows it to be nested within another `ModelAdmin` instance. Similar to django's built-in `InlineModelAdmin`, it allows editing of related objects, but instead of doing it inline, it gives you a full `ModelAdmin` as sub-admin of parent `ModelAdmin`. Like `InlineModelAdmin` it works on models related by `ForeignKey`. Multiple `SubAdmin` instances can be nested within a single `ModelAdmin` or `SubAdmin` allowing for multi-level nesting.

## Installation

The easiest and recommended way to install `django-subadmin` is from [PyPI](https://pypi.python.org/pypi/django-subadmin)

```
pip install django-subadmin
```

You need to add `subadmin` to `INSTALLED_APPS` in your projects `settings.py`, otherwise `django` will not be able to find the necessary templates and template tags.

```
# settings.py

INSTALLED_APPS = (
    ...
    'subadmin',
    ...
)
```

## Example Usage

Sometimes things are best explained by an example. Let's say you have two related models.

```python
# models.py

class MailingList(models.Model):
    name = models.CharField(max_length=100)


class Subscriber(models.Model):
    mailing_list = models.ForeignKey(MailingList)
    username = models.CharField(max_length=100)
```

If you wish to display only subscribers belonging to a particular mailing list in django admin, your only options is to use `InlineModelAdmin`, which is not very practical when dealing with large number of related objects, plus, you loose all the cool functionality of `ModelAdmin` like searching, filtering, pagination, etc ...

This is where `SubAdmin` comes in.

```python
# admin.py

from subadmin import SubAdmin, RootSubAdmin
from .models import MailingList, Subscriber

# Instead of admin.ModelAdmin we subclass SubAdmin,
# we also set model attribute

class SubscriberSubAdmin(SubAdmin): 
    model = Subscriber
    list_display = ('username',)


# Since this is the top level model admin, which will be registred with admin.site,
# we subclass RootSubAdmin and set subadmins attribute

class MailingListAdmin(RootSubAdmin):
    list_display = ('name',)

    subadmins = [SubscriberSubAdmin]
    

admin.site.register(MailingList, MailingListAdmin)
```

With just a few lines of code you get a fully functional `ModelAdmin`, that will automatically pull in just the relevant related objects, based on `ForeignKey` relation between the two models, it will also auto set `ForeignKey` fields for nested relations and exclude them from change form when adding and editing objects on subadmin.

If you want to see it in action, or get a more in-depth look at how to set everything up, check out <https://github.com/inueni/django-subadmin-example>.


## Supported Django versions

Current release of `django-subadmin` is **1.9.0** and is compatible with Django 1.9, 1.10 and 1.11.

Since Django versions before 1.11 don't support `get_exclude` on `ModelAdmin` instances, a workaround that temporarily stores excluded fields on `ModelAdmin` instance, is used. This should not cause any issues under normal circumstances.

#### Verison numbering

`django-subadmin` version numbers are related to Django version numbers. `django-subadmin` major and minor version numbers equal the minimal compatible django release.


## Stability

`django-subadmin` has evolved from code that has been running on production servers since early 2014 without any issues. Still, the code has been heavily refactored prior to public release, and while it is unlikely to eat your data, consider it **BETA** software.
