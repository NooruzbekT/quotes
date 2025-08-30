from django.contrib.auth.forms import UserCreationForm
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Quote, Tag
from .forms import QuoteCreateForm
from .services import pick_weighted_random_quote, register_view, register_reaction, top_quotes
from django.contrib.auth import login
from django.urls import reverse
from django.db import IntegrityError
@require_http_methods(["GET"])
def home(request):
    quote = pick_weighted_random_quote()

    if quote:
        register_view(quote)

    context = {
        "quote": quote,
        "is_moderator": (
                request.user.is_authenticated
                and (request.user.is_staff or request.user.groups.filter(name="Moderator").exists())
        )
    }
    return render(request, "quotes/home.html", context)


@require_http_methods(["POST"])
def react(request, pk: int):
    action = request.POST.get("action")
    if action not in {"like", "dislike"}:
        return HttpResponseBadRequest("invalid action")

    quote = get_object_or_404(Quote, pk=pk)
    register_reaction(quote_id=quote.pk, action=action)
    # вернёмся на главную (можно заменить на HttpResponse для ajax)
    return redirect(request.META.get("HTTP_REFERER") or "quotes:home")


@login_required
@require_http_methods(["GET", "POST"])
def add_quote(request):
    if not request.user.is_authenticated:
        messages.info(request, "Чтобы добавить цитату, войдите или зарегистрируйтесь.")
        login_url = reverse("login")
        return redirect(f"{login_url}?next={request.get_full_path()}")

    if request.method == "POST":
        form = QuoteCreateForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                quote = form.save()
                messages.success(
                    request,
                    "Цитата отправлена на модерацию. После утверждения будет участвовать в выдаче.",
                )
                return redirect("quotes:home")
            except IntegrityError:
                messages.error(request, "Такая цитата уже существует.")
    else:
        form = QuoteCreateForm(user=request.user)
    return render(request, "quotes/add_quote.html", {"form": form})


@require_http_methods(["GET"])
def top10(request):
    tag_id = request.GET.get("tag")

    quotes = Quote.objects.filter(status=Quote.Status.APPROVED)

    if tag_id:
        quotes = quotes.filter(tags__id=tag_id)

    quotes = quotes.order_by("-likes")[:10]
    tags = Tag.objects.all()

    return render(
        request,
        "quotes/top10.html",
        {
            "quotes": quotes,
            "tags": tags,
            "selected_tag": int(tag_id) if tag_id else None,
        }
    )

@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("quotes:home")
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # авто-логин после регистрации
            return redirect("quotes:home")
    else:
        form = UserCreationForm()
    return render(request, "quotes/register.html", {"form": form})