from django import forms
from django.core.exceptions import ValidationError
from .models import Quote, Tag
from .services import get_or_create_source_by_name

class QuoteCreateForm(forms.ModelForm):
    """Форма для обычных пользователей"""
    source_name = forms.CharField(label="Источник (фильм/книга/автор)", max_length=255)

    class Meta:
        model = Quote
        fields = ["text", "weight"]
        widgets = {"text": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        txt = (cleaned.get("text") or "").strip()
        if not txt:
            raise ValidationError("Текст цитаты обязателен.")
        return cleaned

    def save(self, commit=True):
        source = get_or_create_source_by_name(self.cleaned_data["source_name"], user=self.user)
        quote: Quote = super().save(commit=False)
        quote.source = source
        quote.author = self.user
        if commit:
            quote.save()
        return quote


class ModeratorQuoteApproveForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        label="Теги",
        queryset=Tag.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Quote
        fields = ["weight", "tags"]
        widgets = {
            "weight": forms.NumberInput(attrs={"min": 1, "value": 1})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # подтягиваем все теги для выбора
        self.fields["tags"].queryset = Tag.objects.all()

        # проставляем дефолт для weight
        if self.instance and self.instance.weight:
            self.fields["weight"].initial = self.instance.weight
        else:
            self.fields["weight"].initial = 1

    def clean(self):
        cleaned_data = super().clean()
        tags = cleaned_data.get("tags")
        if not tags or len(tags) == 0:
            raise forms.ValidationError("Нужно выбрать хотя бы один тег.")
        return cleaned_data


