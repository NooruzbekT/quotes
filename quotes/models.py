from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


# --------- helpers ---------
def _collapse_spaces(s: str) -> str:
    return " ".join(s.split())


def normalize_source_name(name: str) -> str:
    return _collapse_spaces(name).strip().lower()


def normalize_quote_text(text: str) -> str:
    return _collapse_spaces(text).strip()


# --------- core models ---------
class Source(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    name = models.CharField(max_length=255, unique=False)
    # для анти-дубликатов источников используем нормализованное имя
    name_normalized = models.CharField(max_length=255, unique=True, db_index=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_sources",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_sources",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    # если модератор решил слить дубль в другой источник
    merged_into = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="merged_sources"
    )

    def clean(self):
        self.name = _collapse_spaces(self.name).strip()
        self.name_normalized = normalize_source_name(self.name)

    def save(self, *args, **kwargs):
        # чтобы нормализация гарантированно применялась
        self.clean()
        # если утвердили — фиксируем время
        if self.status == self.Status.APPROVED and self.approved_at is None:
            self.approved_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["name_normalized"]),
        ]


class Tag(models.Model):
    name = models.CharField(max_length=64, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Quote(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    text = models.TextField(unique=False)
    text_normalized = models.TextField(unique=True, db_index=True)
    source = models.ForeignKey(
        Source, on_delete=models.CASCADE, related_name="quotes"
    )

    weight = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Чем больше значение (1–10), тем чаще цитата будет показываться на главной.",
    )

    views = models.PositiveIntegerField(default=0, db_index=True)
    likes = models.PositiveIntegerField(default=0, db_index=True)
    dislikes = models.PositiveIntegerField(default=0)

    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True
    )

    tags = models.ManyToManyField(Tag, blank=True, related_name="quotes")

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quotes",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # нормализуем текст и заполняем text_normalized
        self.text = _collapse_spaces(self.text).strip()
        self.text_normalized = normalize_quote_text(self.text)

        if self.status == Quote.Status.APPROVED:
            if self.source.status != Source.Status.APPROVED:
                raise ValidationError("Нельзя утвердить цитату: её источник ещё не утверждён.")

        if self.status == self.Status.APPROVED and self.source_id:
            approved_qs = Quote.objects.filter(
                source_id=self.source_id, status=self.Status.APPROVED
            ).exclude(pk=self.pk)
            if approved_qs.count() >= 3:
                raise ValidationError("У этого источника уже есть 3 утверждённые цитаты.")

        

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.text[:60]}{'…' if len(self.text) > 60 else ''}"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["source", "status"]),
            models.Index(fields=["-likes", "-views", "-created_at"]),
        ]


class ModerationLog(models.Model):
    class Action(models.TextChoices):
        APPROVE = "approve", "Approve"
        REJECT = "reject", "Reject"

    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="moderation_logs")
    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="moderation_actions"
    )
    action = models.CharField(max_length=10, choices=Action.choices)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        who = self.moderator_id or "system"
        return f"{self.get_action_display()} • quote#{self.quote_id} • {who}"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action"]),
            models.Index(fields=["quote"]),
        ]
