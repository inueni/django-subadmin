from django.contrib.auth import get_user_model
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

    def test_bulk_delete_confirmation_has_parent_context(self):
        response = self.client.post(
            self.child_url("changelist"),
            {"action": "delete_selected", "_selected_action": [str(self.child.pk)]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["parent_instance"], self.parent)
