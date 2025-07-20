from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column
import re
from django.core.exceptions import ValidationError
from .models import Resume, Experience, Education, Skill, ResumeSkill
from django.forms import modelformset_factory, BaseModelFormSet
import datetime

class ResumeForm(forms.ModelForm):
	class Meta:
		model = Resume
		fields = ['title', 'summary', 'contact_email', 'contact_phone', 'contact_address']
		widgets = {
			'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Resume Title'}),
			'summary': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Brief professional summary...'}),
			'contact_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
			'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone', 'pattern': r'^\\+?1?\\d{9,15}$', 'title': 'Enter a valid phone number (9-15 digits, may start with +)'}),
			'contact_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address'}),
		}
		help_texts = {
			'contact_phone': 'Enter a valid phone number (9-15 digits, may start with +).',
			'contact_email': 'Enter a valid email address.',
		}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.helper = FormHelper()
		self.helper.form_method = 'post'
		self.helper.layout = Layout(
			Row(
				Column('title', css_class='form-group col-md-6 mb-0'),
				Column('contact_email', css_class='form-group col-md-6 mb-0'),
			),
			Row(
				Column('contact_phone', css_class='form-group col-md-6 mb-0'),
				Column('contact_address', css_class='form-group col-md-6 mb-0'),
			),
			'summary',
			Submit('submit', 'Save Resume', css_class='btn-success')
		)

	def clean_contact_phone(self):
		phone = self.cleaned_data['contact_phone']
		if not re.match(r'^\+?1?\d{9,15}$', phone):
			raise ValidationError("Enter a valid phone number (9-15 digits, may start with +).")
		return phone

	def clean_contact_email(self):
		email = self.cleaned_data['contact_email']
		if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
			raise ValidationError("Enter a valid email address.")
		return email

class ExperienceForm(forms.ModelForm):
	class Meta:
		model = Experience
		fields = ['job_title', 'company', 'start_date', 'end_date', 'description']
		widgets = {
			'job_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Job Title'}),
			'company': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company'}),
			'start_date': forms.DateInput(attrs={'type': 'text', 'class': 'form-control flatpickr'}),
			'end_date': forms.DateInput(attrs={'type': 'text', 'class': 'form-control flatpickr'}),
			'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Describe your responsibilities and achievements...'}),
		}
		help_texts = {
			'job_title': 'Enter your job title (e.g., Software Engineer).',
			'company': 'Enter the company name where you worked.',
			'start_date': 'Enter the start date in YYYY-MM-DD format (e.g., 2023-01-15).',
			'end_date': 'Enter the end date in YYYY-MM-DD format (e.g., 2024-05-30), or leave blank if still employed.',
			'description': 'Describe your responsibilities and achievements in this role.',
		}

	def clean(self):
		cleaned_data = super().clean()
		# Only validate if not marked for deletion
		if self.cleaned_data.get('DELETE', False):
			return cleaned_data
		start_date = cleaned_data.get('start_date')
		end_date = cleaned_data.get('end_date')
		if start_date and end_date and end_date < start_date:
			raise ValidationError('End date cannot be before start date.')
		return cleaned_data

class EducationForm(forms.ModelForm):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if not self.fields['start_year'].initial:
			self.fields['start_year'].initial = 2015
		if not self.fields['end_year'].initial:
			self.fields['end_year'].initial = 2016

	class Meta:
		model = Education
		fields = ['school', 'degree', 'start_year', 'end_year', 'score']
		widgets = {
			'school': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'School Name'}),
			'degree': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Degree'}),
			'start_year': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Start Year', 'min': 1900, 'max': 2100}),
			'end_year': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'End Year', 'min': 1900, 'max': 2100}),
			'score': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Score (optional)'}),
		}

	def clean(self):
		cleaned_data = super().clean()
		# Only validate if not marked for deletion
		if self.cleaned_data.get('DELETE', False):
			return cleaned_data
		start_year = cleaned_data.get('start_year')
		end_year = cleaned_data.get('end_year')
		current_year = datetime.datetime.now().year
		if start_year and (start_year < 1900 or start_year > current_year):
			raise ValidationError('Start year must be between 1900 and the current year.')
		if end_year and (end_year < 1900 or end_year > current_year + 1):
			raise ValidationError('End year must be between 1900 and next year.')
		if start_year and end_year and end_year < start_year:
			raise ValidationError('End year cannot be before start year.')
		return cleaned_data

class SkillForm(forms.ModelForm):
	class Meta:
		model = Skill
		fields = ['name']
		widgets = {
			'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Skill'}),
		}

# Custom BaseModelFormSet to skip validation for forms marked for deletion
class BaseSkipDeleteFormSet(BaseModelFormSet):
	def clean(self):
		if any(self.errors):
			return
		for form in self.forms:
			if self.can_delete and self._should_delete_form(form):
				continue
			if hasattr(form, 'clean'):
				form.clean()

ExperienceFormSet = modelformset_factory(
	Experience, form=ExperienceForm, extra=3, can_delete=True,
	formset=BaseSkipDeleteFormSet,
	widgets={'DELETE': forms.CheckboxInput(attrs={'class': 'form-check-input'})},
)
EducationFormSet = modelformset_factory(
	Education, form=EducationForm, extra=3, can_delete=True,
	formset=BaseSkipDeleteFormSet,
	widgets={'DELETE': forms.CheckboxInput(attrs={'class': 'form-check-input'})},
)
SkillFormSet = modelformset_factory(
	Skill, form=SkillForm, extra=3, can_delete=True,
	formset=BaseSkipDeleteFormSet,
	widgets={'DELETE': forms.CheckboxInput(attrs={'class': 'form-check-input'})},
)
# CertificationFormSet can be added similarly if you have a Certification model