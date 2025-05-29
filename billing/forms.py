from django import forms
from .models import Bill, Payment, ServiceType

class BillForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = ['service', 'subtotal', 'discount', 'tax', 'notes', 'due_date']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['service'].queryset = ServiceType.objects.filter(is_active=True)

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'payment_method', 'payment_date', 'reference_number', 'notes', 'created_by']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError("Payment amount must be greater than zero.")
        return amount 