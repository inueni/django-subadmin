# Changelog

## [2.0.1] - 2020-04-12
 - _Fix_: Properly validate unique_together. (Issue #7)

## [2.0.0] - 2020-02-27
 - **BREAKING**: This release no longer supports Python 2 and requires Django version 2.0 and up.
 - Python 3 compatibility

## [1.9.3] - 2020-02-27
- Updated README.md with legacy version info.
- Remove `pandoc` dev dependency as PyPI now supports Markdown natively.

## [1.9.2] - 2017-11-21
- _Fix_: setup.py is now python2 compatible. ([Issue #4])

## [1.9.1] - 2017-11-18
- _Improvement_: Replaced thread unsafe workaround for Django < 1.11 with backported `get_form` implementation from Django 1.11. ([Issue #2])
- _Fix_: `get_exclude` now takes into accounts fields set by `exclude` on Django < 1.11. ([Issue #3])

## 1.9.0 - 2017-11-13
- Initial release

[2.0.0]: https://github.com/inueni/django-subadmin/compare/v1.9.3...v2.0.0
[1.9.3]: https://github.com/inueni/django-subadmin/compare/v1.9.2...v1.9.3
[1.9.2]: https://github.com/inueni/django-subadmin/compare/v1.9.1...v1.9.2
[1.9.1]: https://github.com/inueni/django-subadmin/compare/v1.9.0...v1.9.1
[Issue #2]: https://github.com/inueni/django-subadmin/issues/2
[Issue #3]: https://github.com/inueni/django-subadmin/issues/3
[Issue #4]: https://github.com/inueni/django-subadmin/issues/4