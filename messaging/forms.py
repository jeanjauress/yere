from django import forms


class MessageForm(forms.Form):
    body = forms.CharField(label="", max_length=2000,
                           widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Votre message…"}))

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if not body:
            raise forms.ValidationError("Le message est vide.")
        return body
