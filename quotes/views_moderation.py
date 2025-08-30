from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from .models import Quote, Source, ModerationLog, Tag, normalize_source_name
from .forms import ModeratorQuoteApproveForm

User = get_user_model()

def is_moderator(u):
    return u.is_authenticated and (u.is_staff or u.groups.filter(name="Moderator").exists())

@user_passes_test(is_moderator)
def queue(request):
    """О модерации: цитаты (draft) и источники (pending)."""
    quotes_qs = (
        Quote.objects
        .select_related("source", "author")
        .prefetch_related("tags")
        .filter(status=Quote.Status.DRAFT)
    )
    sources_qs = Source.objects.filter(status=Source.Status.PENDING)

    queue_items = [
        (q, ModeratorQuoteApproveForm(instance=q, prefix=f"q{q.id}"))
        for q in quotes_qs
    ]

    context = {
        "queue_items": queue_items,
        "sources": sources_qs,
        "all_sources": Source.objects.filter(status=Source.Status.APPROVED).only("name").order_by("name"),
    }
    return render(request, "quotes/moderation_queue.html", context)

@user_passes_test(is_moderator)
@require_http_methods(["POST"])
@transaction.atomic
def approve_quote(request, pk: int):
    quote = get_object_or_404(Quote, pk=pk)

    form = ModeratorQuoteApproveForm(
        request.POST, instance=quote, prefix=f"q{quote.id}"
    )

    if not form.is_valid():
        detail = "; ".join(f"{k}: {', '.join(v)}" for k, v in form.errors.items())
        messages.error(request, f"Ошибка валидации формы модератора: {detail or 'проверьте поля'}")
        return redirect("quotes:moderation_queue")

    q = form.save(commit=False)
    q.status = Quote.Status.APPROVED
    try:

        q.full_clean()
        q.save()
        form.save_m2m()
    except ValidationError as e:
        messages.error(request, "; ".join(e.messages))
        return redirect("quotes:moderation_queue")
    except IntegrityError:
        messages.error(request, "Нельзя сохранить: нарушено ограничение уникальности. ")
        return redirect("quotes:moderation_queue")

    ModerationLog.objects.create(
        quote=q, moderator=request.user, action=ModerationLog.Action.APPROVE
    )
    messages.success(request, "Цитата утверждена.")
    return redirect("quotes:moderation_queue")



@user_passes_test(is_moderator)
@require_http_methods(["POST"])
@transaction.atomic
def reject_quote(request, pk: int):
    quote = get_object_or_404(Quote, pk=pk)
    reason = request.POST.get("reason", "")
    quote.status = Quote.Status.REJECTED
    quote.save()
    ModerationLog.objects.create(
        quote=quote, moderator=request.user, action=ModerationLog.Action.REJECT, reason=reason
    )
    messages.info(request, "Цитата отклонена.")
    return redirect("quotes:moderation_queue")

@user_passes_test(is_moderator)
@require_http_methods(["POST"])
def approve_source(request, pk: int):
    s = get_object_or_404(Source, pk=pk)
    s.status = Source.Status.APPROVED
    s.approved_by = request.user
    s.save()
    messages.success(request, "Источник утверждён.")
    return redirect("quotes:moderation_queue")

@user_passes_test(is_moderator)
@require_http_methods(["POST"])
def reject_source(request, pk: int):
    s = get_object_or_404(Source, pk=pk)
    s.status = Source.Status.REJECTED
    s.approved_by = request.user
    s.save()
    messages.info(request, "Источник отклонён.")
    return redirect("quotes:moderation_queue")

@user_passes_test(is_moderator)
@require_http_methods(["POST"])
@transaction.atomic
def merge_source(request, pk: int):
    s = get_object_or_404(Source, pk=pk)
    target_name = (request.POST.get("target_name") or "").strip()
    if not target_name:
        messages.error(request, "Укажите корректное название целевого источника.")
        return redirect("quotes:moderation_queue")


    norm = normalize_source_name(target_name)

    target, created = Source.objects.get_or_create(
        name_normalized=norm,
        defaults=dict(
            name=target_name,
            status=Source.Status.APPROVED,
            approved_by=request.user,
        ),
    )

    if target.pk == s.pk:
        messages.error(request, "Нельзя объединить источник сам с собой.")
        return redirect("quotes:moderation_queue")

    approved_in_target = Quote.objects.filter(
        source=target, status=Quote.Status.APPROVED
    ).count()
    approved_to_move = Quote.objects.filter(
        source=s, status=Quote.Status.APPROVED
    ).count()
    if approved_in_target + approved_to_move > 3:
        messages.error(
            request,
            "Нельзя объединить: в целевом источнике окажется больше 3 утверждённых цитат."
        )
        return redirect("quotes:moderation_queue")

    Quote.objects.filter(source=s).update(source=target)

    Source.objects.filter(merged_into=s).update(merged_into=target)

    s.merged_into = target
    s.status = Source.Status.REJECTED
    s.approved_by = request.user
    s.save(update_fields=["merged_into", "status", "approved_by"])

    messages.success(
        request,
        f"Источник «{s.name}» объединён с «{target.name}». "
        f"{'Создан новый источник.' if created else 'Использован существующий.'}"
    )
    return redirect("quotes:moderation_queue")

@user_passes_test(is_moderator)
def users(request):
    """Список всех пользователей + их цитаты."""
    users_qs = User.objects.all().order_by("-date_joined")

    quotes_qs = (
        Quote.objects
        .select_related("author", "source")
        .only("id", "author_id", "text", "status", "created_at", "source_id")
        .order_by("-created_at")
    )

    quotes_by_author = {}
    for q in quotes_qs:
        quotes_by_author.setdefault(q.author_id, []).append(q)

    users_data = [(u, quotes_by_author.get(u.id, [])) for u in users_qs]

    return render(
        request,
        "quotes/moderation_users.html",
        {"users_data": users_data},
    )


@user_passes_test(is_moderator)
@require_http_methods(["POST"])
def add_tag(request):
    name = (request.POST.get("name") or "").strip()
    if not name:
        messages.error(request, "Название тега не может быть пустым.")
    else:
        Tag.objects.get_or_create(name=name)
        messages.success(request, f"Тег «{name}» добавлен.")
    return redirect("quotes:moderation_queue")