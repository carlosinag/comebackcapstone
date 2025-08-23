from django import forms
from .models import Bill, Payment, ServiceType

class BillForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = ['discount']

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'payment_method', 'payment_date', 'reference_number']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'reference_number': forms.TextInput(attrs={'placeholder': 'Enter reference number'}),
        }

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError("Payment amount must be greater than zero.")
        return amount

    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        reference_number = cleaned_data.get('reference_number')
        
        # Require reference number for GCash and Bank Transfer
        if payment_method in ['GCASH', 'BANK'] and not reference_number:
            raise forms.ValidationError({
                'reference_number': 'Reference number is required for GCash and Bank Transfer payments.'
            })
        
        # Clear reference number for cash payments
        if payment_method == 'CASH':
            cleaned_data['reference_number'] = ''
        
        return cleaned_data 