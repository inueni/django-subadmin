import json
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from .testapp.models import Child, Grandchild, Parent


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
        viewer.user_permissions.add(
            Permission.objects.get(content_type=child_type, codename="add_child"),
            Permission.objects.get(content_type=child_type, codename="view_child"),
        )
        self.client.force_login(viewer)
        response = self.client.post(self.child_url("add"), {"name": "Viewable", "_save": "Save"})
        self.assertRedirects(response, self.child_url("changelist"), fetch_redirect_response=False)
        self.assertTrue(Child.objects.filter(parent=self.parent, name="Viewable").exists())

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
        viewer.user_permissions.add(Permission.objects.get(content_type=child_type, codename="view_child"))
        self.client.force_login(viewer)
        response = self.client.get(f'{self.child_url("change", self.child.pk)}?_changelist_filters=name%3DExisting')
        self.assertContains(response, f'href="{changelist_url}?name=Existing" class="closelink"')
        self.assertEqual(self.client.get(f"{changelist_url}?name=Existing").status_code, 200)

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
