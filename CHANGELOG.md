# Changelog

## [1.9.2] - 2017-11-21
- _Fix_: setup.py is now python2 compatible ([Issue #4])

## [1.9.1] - 2017-11-18
- _Improvement_: Replaced thread unsafe workaround for Django < 1.11 with backported `get_form` implementation from Django 1.11. ([Issue #2])
- _Fix_: `get_exclude` now takes into accounts fields set by `exclude` on Django < 1.11 ([Issue #3])

## 1.9.0 - 2017-11-13
- Initial release

[1.9.2]: https://github.com/inueni/django-subadmin/compare/v1.9.1...v1.9.2
[1.9.1]: https://github.com/inueni/django-subadmin/compare/v1.9.0...v1.9.1
[Issue #2]: https://github.com/inueni/django-subadmin/issues/2
[Issue #3]: https://github.com/inueni/django-subadmin/issues/3
[Issue #4]: https://github.com/inueni/django-subadmin/issues/4