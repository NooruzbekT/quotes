import random
from typing import List, Optional
from django.db.models import F, QuerySet
from .models import Quote, Source, Tag, normalize_source_name


def get_or_create_source_by_name(name: str, user=None) -> Source:
    norm = normalize_source_name(name)
    src = Source.objects.filter(name_normalized=norm).first()
    if src:
        return src
    return Source.objects.create(
        name=name.strip(),
        name_normalized=norm,
        status=Source.Status.PENDING,
        created_by=user,
    )


def ensure_tags(raw: str) -> List[Tag]:
    if not raw:
        return []
    items = [t.strip() for t in raw.replace(";", ",").split(",")]
    items = [t for t in items if t]
    out = []
    for name in items:
        tag, _ = Tag.objects.get_or_create(name=name)
        out.append(tag)
    return out


def approved_quotes_qs() -> QuerySet[Quote]:
    return Quote.objects.select_related("source", "author")\
        .prefetch_related("tags")\
        .filter(status=Quote.Status.APPROVED, source__status=Source.Status.APPROVED)


def pick_weighted_random_quote(qs: Optional[QuerySet[Quote]] = None) -> Optional[Quote]:
    qs = qs if qs is not None else approved_quotes_qs()
    ids_weights = list(qs.values_list("id", "weight"))
    if not ids_weights:
        return None
    ids, weights = zip(*ids_weights)
    chosen_id = random.choices(population=ids, weights=weights, k=1)[0]
    return qs.get(id=chosen_id)


def register_view(quote: Quote) -> None:
    Quote.objects.filter(pk=quote.pk).update(views=F("views") + 1)
    quote.views += 1


def register_reaction(quote_id: int, action: str) -> None:
    if action == "like":
        Quote.objects.filter(pk=quote_id).update(likes=F("likes") + 1)
    elif action == "dislike":
        Quote.objects.filter(pk=quote_id).update(dislikes=F("dislikes") + 1)


def top_quotes(limit: int = 10) -> QuerySet[Quote]:
    return approved_quotes_qs().order_by("-likes", "-views", "-created_at")[:limit]
