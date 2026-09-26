import json
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib import admin
from django.contrib.admin.utils import quote
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from django.urls import reverse

from .testapp.models import (
    Child, Grandchild, Parent, RepeatedParentGrandchild, StringChild, StringParent,
    UnrelatedParentGrandchild,
)


class NestedAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser("admin", "admin@example.com", "password")
        cls.parent = Parent.objects.create(name="Parent")
        cls.other_parent = Parent.objects.create(name="Other")
        cls.child = Child.objects.create(parent=cls.parent, name="Existing")
        cls.grandchild = Grandchild.objects.create(child=cls.child, name="Grandchild")

    def setUp(self):
        self.client.force_login(self.user)

    def child_url(self, action, *args):
        return reverse(f"admin:testapp_parent_child_{action}", args=[self.parent.pk, *args])

    def grandchild_url(self, action, *args):
        return reverse(
            f"admin:testapp_parent_child_grandchild_{action}",
            args=[self.parent.pk, self.child.pk, *args],
        )

    def test_nested_views_and_templates_render(self):
        for url in (
            reverse("admin:testapp_parent_change", args=[self.parent.pk]),
            self.child_url("changelist"),
            self.child_url("add"),
            self.child_url("change", self.child.pk),
            self.grandchild_url("changelist"),
            self.grandchild_url("add"),
            self.grandchild_url("change", self.grandchild.pk),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Parent")

    def test_child_changelist_is_scoped_to_parent(self):
        Child.objects.create(parent=self.other_parent, name="Other child")
        response = self.client.get(self.child_url("changelist"))
        self.assertContains(response, "Existing")
        self.assertNotContains(response, "Other child")

    def test_child_creation_sets_parent(self):
        response = self.client.post(self.child_url("add"), {"name": "New", "_save": "Save"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Child.objects.filter(parent=self.parent, name="New").exists())

        viewer = get_user_model().objects.create_user("add-and-view", is_staff=True)
        child_type = ContentType.objects.get_for_model(Child)
        parent_type = ContentType.objects.get_for_model(Parent)
        viewer.user_permissions.add(
            Permission.objects.get(content_type=child_type, codename="add_child"),
            Permission.objects.get(content_type=child_type, codename="view_child"),
            Permission.objects.get(content_type=parent_type, codename="view_parent"),
        )
        self.client.force_login(viewer)
        response = self.client.post(self.child_url("add"), {"name": "Viewable", "_save": "Save"})
        self.assertRedirects(response, self.child_url("changelist"), fetch_redirect_response=False)
        self.assertTrue(Child.objects.filter(parent=self.parent, name="Viewable").exists())

    def test_nested_creation_with_reused_parent_field(self):
        add_url = reverse(
            "admin:testapp_parent_child_repeatedparentgrandchild_add",
            args=[self.parent.pk, self.child.pk],
        )
        response = self.client.get(add_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("parent", response.context["adminform"].form.fields)

        response = self.client.post(add_url, {"name": "Nested", "_save": "Save"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            RepeatedParentGrandchild.objects.filter(parent=self.child, name="Nested").exists()
        )

    def test_nested_form_preserves_unrelated_parent_field(self):
        unrelated_parent = StringParent.objects.create(id="unrelated", name="Unrelated")
        add_url = reverse(
            "admin:testapp_parent_child_unrelatedparentgrandchild_add",
            args=[self.parent.pk, self.child.pk],
        )
        response = self.client.get(add_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("parent", response.context["adminform"].form.fields)
        self.assertNotIn("child", response.context["adminform"].form.fields)

        response = self.client.post(
            add_url, {"parent": unrelated_parent.pk, "name": "Nested", "_save": "Save"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            UnrelatedParentGrandchild.objects.filter(
                child=self.child, parent=unrelated_parent, name="Nested"
            ).exists()
        )

    def test_child_change_responses(self):
        change_url = self.child_url("change", self.child.pk)
        destinations = {
            "_save": self.child_url("changelist"),
            "_continue": change_url,
            "_addanother": self.child_url("add"),
        }

        for button, destination in destinations.items():
            with self.subTest(button=button):
                name = f"Changed {button}"
                response = self.client.post(change_url, {"name": name, button: "1"})
                self.assertRedirects(response, destination, fetch_redirect_response=False)
                self.child.refresh_from_db()
                self.assertEqual(self.child.name, name)

        response = self.client.post(change_url, {"name": "Changed popup", "_popup": "1"})
        self.assertEqual(response.status_code, 200)
        popup_data = json.loads(response.context_data["popup_response_data"])
        self.assertEqual(popup_data["action"], "change")
        self.assertEqual(popup_data["value"], str(self.child.pk))

        child_admin = admin.site._registry[Parent].subadmin_instances[0]
        with patch.object(child_admin, "save_as", True), patch.object(child_admin, "save_as_continue", False):
            response = self.client.post(change_url, {"name": "Copied", "_saveasnew": "1"})
        self.assertRedirects(response, self.child_url("changelist"), fetch_redirect_response=False)
        self.assertTrue(Child.objects.filter(parent=self.parent, name="Copied").exists())

    def test_nested_filter_navigation(self):
        changelist_url = self.child_url("changelist")
        add_url = self.child_url("add")
        filters = "_changelist_filters=name%3DExisting&extra=1"

        response = self.client.get(f"{changelist_url}?name=Existing")
        self.assertContains(response, f'{add_url}?_changelist_filters=name%3DExisting')

        response = self.client.post(f"{add_url}?{filters}", {"name": "New", "_continue": "1"})
        self.assertEqual(response.status_code, 302)
        new_child = Child.objects.get(parent=self.parent, name="New")
        self.assertEqual(urlsplit(response["Location"]).path, self.child_url("change", new_child.pk))
        self.assertEqual(
            parse_qs(urlsplit(response["Location"]).query),
            {"_changelist_filters": ["name=Existing"], "extra": ["1"]},
        )

        change_url = self.child_url("change", new_child.pk)
        response = self.client.post(f"{change_url}?{filters}", {"name": "New", "_addanother": "1"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlsplit(response["Location"]).path, add_url)
        self.assertEqual(
            parse_qs(urlsplit(response["Location"]).query),
            {"_changelist_filters": ["name=Existing"], "extra": ["1"]},
        )

        viewer = get_user_model().objects.create_user("viewer", is_staff=True)
        child_type = ContentType.objects.get_for_model(Child)
        parent_type = ContentType.objects.get_for_model(Parent)
        viewer.user_permissions.add(
            Permission.objects.get(content_type=child_type, codename="view_child"),
            Permission.objects.get(content_type=parent_type, codename="view_parent"),
        )
        self.client.force_login(viewer)
        response = self.client.get(f'{self.child_url("change", self.child.pk)}?_changelist_filters=name%3DExisting')
        self.assertContains(response, f'href="{changelist_url}?name=Existing" class="closelink"')
        self.assertEqual(self.client.get(f"{changelist_url}?name=Existing").status_code, 200)

    def test_nested_views_require_ancestor_permissions(self):
        viewer = get_user_model().objects.create_user("ancestor-viewer", is_staff=True)
        parent_type = ContentType.objects.get_for_model(Parent)
        child_type = ContentType.objects.get_for_model(Child)
        grandchild_type = ContentType.objects.get_for_model(Grandchild)
        viewer.user_permissions.add(
            Permission.objects.get(content_type=grandchild_type, codename="view_grandchild")
        )
        self.client.force_login(viewer)

        url = self.grandchild_url("changelist")
        self.assertEqual(self.client.get(url).status_code, 403)
        with override_settings(SUBADMIN_USE_DIRECT_PARENT_LOOKUP=True):
            self.assertEqual(self.client.get(url).status_code, 403)

        viewer.user_permissions.add(
            Permission.objects.get(content_type=parent_type, codename="view_parent")
        )
        self.assertEqual(self.client.get(url).status_code, 403)

        viewer.user_permissions.add(
            Permission.objects.get(content_type=child_type, codename="view_child")
        )
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_child_delete_responses(self):
        response = self.client.post(self.child_url("delete", self.child.pk), {"post": "yes"})
        self.assertRedirects(response, self.child_url("changelist"), fetch_redirect_response=False)
        self.assertFalse(Child.objects.filter(pk=self.child.pk).exists())

        popup_child = Child.objects.create(parent=self.parent, name="Popup")
        response = self.client.post(
            self.child_url("delete", popup_child.pk),
            {"post": "yes", "_popup": "1"},
        )
        self.assertEqual(response.status_code, 200)
        popup_data = json.loads(response.context_data["popup_response_data"])
        self.assertEqual(popup_data["action"], "delete")
        self.assertEqual(popup_data["value"], str(popup_child.pk))
        self.assertFalse(Child.objects.filter(pk=popup_child.pk).exists())

    def test_bulk_delete_confirmation_has_parent_context(self):
        response = self.client.post(
            self.child_url("changelist"),
            {"action": "delete_selected", "_selected_action": [str(self.child.pk)]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["parent_instance"], self.parent)

    def test_string_primary_key_navigation(self):
        parent = StringParent.objects.create(id="parent_2Fid", name="String parent")
        child = StringChild.objects.create(id="child_2Fid", parent=parent, name="String child")
        parent_id = quote(parent.pk)
        child_id = quote(child.pk)
        parent_url = reverse("admin:testapp_stringparent_change", args=[parent_id])
        changelist_url = reverse("admin:testapp_stringparent_stringchild_changelist", args=[parent_id])
        add_url = reverse("admin:testapp_stringparent_stringchild_add", args=[parent_id])
        change_url = reverse(
            "admin:testapp_stringparent_stringchild_change", args=[parent_id, child_id]
        )
        history_url = reverse(
            "admin:testapp_stringparent_stringchild_history", args=[parent_id, child_id]
        )
        delete_url = reverse(
            "admin:testapp_stringparent_stringchild_delete", args=[parent_id, child_id]
        )

        self.assertContains(self.client.get(parent_url), changelist_url)
        changelist = self.client.get(changelist_url)
        self.assertContains(changelist, change_url)
        self.assertContains(changelist, add_url)
        change_form = self.client.get(change_url)
        self.assertContains(change_form, changelist_url)
        self.assertContains(change_form, history_url)
        self.assertContains(change_form, delete_url)
        self.assertEqual(self.client.get(history_url).status_code, 200)
        self.assertEqual(self.client.get(delete_url).status_code, 200)

        response = self.client.post(
            change_url, {"id": child.pk, "name": "Renamed", "_addanother": "1"}
        )
        self.assertRedirects(response, add_url, fetch_redirect_response=False)
        added_id = "added_2Fid"
        response = self.client.post(
            add_url, {"id": added_id, "name": "Added", "_continue": "1"}
        )
        added_url = reverse(
            "admin:testapp_stringparent_stringchild_change", args=[parent_id, quote(added_id)]
        )
        self.assertRedirects(response, added_url, fetch_redirect_response=False)
        self.assertTrue(StringChild.objects.filter(pk=added_id, parent=parent).exists())

        response = self.client.post(
            added_url, {"id": added_id, "name": "Added", "_save": "1"}
        )
        self.assertRedirects(response, changelist_url, fetch_redirect_response=False)
        response = self.client.post(delete_url, {"post": "yes"})
        self.assertRedirects(response, changelist_url, fetch_redirect_response=False)
