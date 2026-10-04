from rest_framework import status
from rest_framework.test import APITestCase

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from apps.blog.models import Category, Comment, Post, Tag

User = get_user_model()


class BlogModelTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            email="student@example.com",
            password="StudentPassword123!",
            first_name="Test",
            last_name="Student",
        )
        self.category = Category.objects.create(name="Study", slug="study")
        self.post = Post.objects.create(
            author=self.user,
            title="My first post",
            slug="my-first-post",
            body="Learning Django.",
            category=self.category,
        )

    def test_post_defaults_and_tags(self) -> None:
        self.assertEqual(self.post.status, Post.Status.DRAFT)
        self.assertIsNotNone(self.post.created_at)
        self.assertIsNotNone(self.post.updated_at)
        self.assertFalse(self.post.tags.exists())
        tag = Tag.objects.create(name="Django", slug="django")
        self.post.tags.add(tag)
        self.assertIn(self.post, tag.posts.all())
        tag.delete()
        self.assertTrue(Post.objects.filter(pk=self.post.pk).exists())

    def test_category_deletion_keeps_post(self) -> None:
        self.category.delete()
        self.post.refresh_from_db()
        self.assertIsNone(self.post.category)

    def test_post_deletion_removes_comments(self) -> None:
        comment = Comment.objects.create(
            post=self.post, author=self.user, body="Nice post."
        )
        self.post.delete()
        self.assertFalse(Comment.objects.filter(pk=comment.pk).exists())

    def test_user_deletion_removes_posts_and_comments(self) -> None:
        other_user = User.objects.create_user(
            email="other@example.com",
            password="StudentPassword123!",
            first_name="Other",
            last_name="Student",
        )
        other_post = Post.objects.create(
            author=other_user, title="Other post", slug="other", body="Hello."
        )
        comment = Comment.objects.create(
            post=other_post, author=self.user, body="My comment."
        )
        post_id = self.post.pk
        self.user.delete()
        self.assertFalse(Post.objects.filter(pk=post_id).exists())
        self.assertFalse(Comment.objects.filter(pk=comment.pk).exists())
        self.assertTrue(Post.objects.filter(pk=other_post.pk).exists())

    def test_names_and_slugs_are_unique(self) -> None:
        for model in (Category, Tag):
            model.objects.get_or_create(name="Python", slug="python")
            for duplicate in (
                {"name": "Python", "slug": "another-slug"},
                {"name": "Another name", "slug": "python"},
            ):
                with self.subTest(model=model.__name__, duplicate=duplicate):
                    with self.assertRaises(IntegrityError), transaction.atomic():
                        model.objects.create(**duplicate)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Post.objects.create(
                author=self.user,
                title="Duplicate slug",
                slug=self.post.slug,
                body="Hello.",
            )


class BlogAPITests(APITestCase):
    def setUp(self) -> None:
        self.author = User.objects.create_user(
            email="author@example.com",
            password="StudentPassword123!",
            first_name="Post",
            last_name="Author",
        )
        self.reader = User.objects.create_user(
            email="reader@example.com",
            password="StudentPassword123!",
            first_name="Post",
            last_name="Reader",
        )
        self.post = Post.objects.create(
            author=self.author,
            title="Published post",
            slug="published-post",
            body="Hello world.",
            status=Post.Status.PUBLISHED,
        )
        self.draft = Post.objects.create(
            author=self.author,
            title="Draft post",
            slug="draft-post",
            body="Work in progress.",
        )
        self.comment = Comment.objects.create(
            post=self.post, author=self.reader, body="Nice post."
        )

    def test_public_reads_hide_drafts(self) -> None:
        response = self.client.get(reverse("post-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([post["id"] for post in response.data], [self.post.pk])
        response = self.client.get(reverse("post-detail", args=[self.draft.pk]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        response = self.client.get(reverse("comment-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], self.comment.pk)

    def test_only_author_can_see_draft(self) -> None:
        self.client.force_authenticate(self.reader)
        response = self.client.get(reverse("post-detail", args=[self.draft.pk]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.client.force_authenticate(self.author)
        response = self.client.get(reverse("post-detail", args=[self.draft.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anonymous_cannot_create_post_or_comment(self) -> None:
        for endpoint in ("post-list", "comment-list"):
            with self.subTest(endpoint=endpoint):
                response = self.client.post(reverse(endpoint), {}, format="json")
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_post_uses_authenticated_author(self) -> None:
        self.client.force_authenticate(self.author)
        response = self.client.post(
            reverse("post-list"),
            {
                "author": self.reader.pk,
                "title": "Created by API",
                "slug": "created-by-api",
                "body": "My post.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["author"], self.author.pk)
        self.assertEqual(response.data["status"], Post.Status.DRAFT)

    def test_post_owner_can_update_and_delete(self) -> None:
        self.client.force_authenticate(self.author)
        url = reverse("post-detail", args=[self.post.pk])
        response = self.client.patch(
            url,
            {"title": "Updated title", "author": self.reader.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, "Updated title")
        self.assertEqual(self.post.author_id, self.author.pk)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Comment.objects.filter(pk=self.comment.pk).exists())

    def test_other_user_cannot_change_post(self) -> None:
        self.client.force_authenticate(self.reader)
        url = reverse("post-detail", args=[self.post.pk])
        response = self.client.patch(url, {"title": "Wrong"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_comment_uses_authenticated_author(self) -> None:
        self.client.force_authenticate(self.reader)
        response = self.client.post(
            reverse("comment-list"),
            {
                "post": self.post.pk,
                "author": self.author.pk,
                "body": "My new comment.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["author"], self.reader.pk)

    def test_comment_owner_can_update_and_delete(self) -> None:
        self.client.force_authenticate(self.reader)
        url = reverse("comment-detail", args=[self.comment.pk])
        response = self.client.patch(
            url, {"body": "Updated.", "author": self.author.pk}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.body, "Updated.")
        self.assertEqual(self.comment.author_id, self.reader.pk)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_other_user_cannot_change_comment(self) -> None:
        self.client.force_authenticate(self.author)
        url = reverse("comment-detail", args=[self.comment.pk])
        response = self.client.patch(url, {"body": "Wrong"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_comment_on_draft_even_as_author(self) -> None:
        self.client.force_authenticate(self.author)
        response = self.client.post(
            reverse("comment-list"),
            {"post": self.draft.pk, "body": "Draft comment."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("post", response.data)

    def test_comments_are_hidden_when_post_becomes_draft(self) -> None:
        self.post.status = Post.Status.DRAFT
        self.post.save()
        response = self.client.get(reverse("comment-list"))
        self.assertEqual(response.data, [])
        self.client.force_authenticate(self.reader)
        url = reverse("comment-detail", args=[self.comment.pk])
        response = self.client.patch(url, {"body": "Hidden"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_comment_cannot_move_to_another_post(self) -> None:
        self.draft.status = Post.Status.PUBLISHED
        self.draft.save()
        self.client.force_authenticate(self.reader)
        response = self.client.patch(
            reverse("comment-detail", args=[self.comment.pk]),
            {"post": self.draft.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.post_id, self.post.pk)

    def test_categories_and_tags_require_staff_for_writes(self) -> None:
        for basename in ("category", "tag"):
            with self.subTest(resource=basename):
                self.client.force_authenticate(user=None)
                url = reverse(f"{basename}-list")
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                payload = {"name": "Python", "slug": "python"}
                response = self.client.post(url, payload, format="json")
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
                self.reader.is_staff = False
                self.client.force_authenticate(self.reader)
                response = self.client.post(url, payload, format="json")
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
                self.reader.is_staff = True
                response = self.client.post(url, payload, format="json")
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                detail_url = reverse(f"{basename}-detail", args=[response.data["id"]])
                response = self.client.patch(
                    detail_url, {"name": "Django"}, format="json"
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                response = self.client.delete(detail_url)
                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
