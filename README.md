# django-subadmin

`django-subadmin` provides a special kind of `ModelAdmin`, called `SubAdmin`, that allows it to be nested within another `ModelAdmin` instance. Similar to django's built-in `InlineModelAdmin`, it allows editing of related objects, but instead of doing it inline, it gives you a full `ModelAdmin` as sub-admin of parent `ModelAdmin`. Like `InlineModelAdmin` it works on models related by `ForeignKey`. Multiple `SubAdmin` instances can be nested within a single `ModelAdmin` or `SubAdmin` allowing for multi-level nesting.

### Suported Python and Django releases

Current release of `django-subadmin` is **2.0.1** and it supports Python 3 only and Django versions 2.0 and up (including Django 3.0).

There is also a *legacy* **1.9.3** release with support for Python 2.7 and Django versions 1.9, 1.10 and 1.11. This release is **no longer maintained and supported**, but it's made available for legacy applications.

#### Verison numbering

django-subadmin versions follow Django version numbers. django-subadmin major and minor version numbers equal the minimal compatible django release.

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


### Caveats

In order to properly support unique field validation (see Issue #7), `SubAdmin` will inject a small mixin into the form. This is done in the `get_form` method and if you override this method in your own classes, make sure to call `super()` or `perp_subadmin_form()` directly. See `subadmin` source code for more details.

Also, the injected mixin `SubAdminFormMixin` overrides `validate_unique` on the form. If your custom form overrides this method as well, have a look at `subadmin` source code for ways in which it differs from stock `ModelForm` implementation and adjust your code as neccesarry.


### Screenshots

![alt text](https://github.com/inueni/django-subadmin-example/raw/master/screenshots/subadmin_screenshot_1.png?raw=true)

 `SubAdmin` instances are accesible from edit view of the `ModelAdmin` instance they are nested in. In the screenshot above you can see links to _Subscribers_ and _Messages_ subadmins (marked with red rectangle) for `MailingList` instance _Mailing list 5_.

---

![alt text](https://github.com/inueni/django-subadmin-example/raw/master/screenshots/subadmin_screenshot_2.png?raw=true)

 `SubAdmin` looks and behaves just like a regular `ModelAdmin`, but looking at breadcrumbs (marked with red rectangle), you can see it is nested within another `ModelAdmin`. Displayed `Subscribers` are limited to those related to `MailingList` instance _Mailing list 5_.

---

 ![alt text](https://github.com/inueni/django-subadmin-example/raw/master/screenshots/subadmin_screenshot_3.png?raw=true)

When adding or editing objects with `SubAdmin`, `ForeignKey` fields to parent instances are removed from the form and automatically set when saving. In this example `mailing_list` field is removed and value is set to parent `MailingList` instance _Mailing list 5_.

> If you want to see it in action, or get a more in-depth look at how to set everything up, check out <https://github.com/inueni/django-subadmin-example>.

## Stability

`django-subadmin` has evolved from code that has been running on production servers since early 2014 without any issues. The code is provided **as-is** and the developers bear no responsibility for any issues stemming from it's use.
