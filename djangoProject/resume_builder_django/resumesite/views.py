from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .models import Resume, Education, Experience, Skill, ResumeSkill
from .forms import ResumeForm, ExperienceFormSet, EducationFormSet, SkillFormSet
from django.views.generic.edit import FormView
from django.db import transaction

# --- Existing function-based views ---
def home(request):
	return render(request, 'home.html', {})

# --- Class-based CRUD views for Resume ---
class ResumeListView(LoginRequiredMixin, ListView):
    model = Resume
    template_name = 'resume_list.html'
    context_object_name = 'resumes'

    def get_queryset(self):
        return Resume.objects.filter(user=self.request.user)  # type: ignore

class ResumeDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Resume
    template_name = 'resume_detail.html'
    context_object_name = 'resume'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        resume = self.get_object()
        context['experiences'] = resume.experiences.all().order_by('-start_date')
        context['educations'] = resume.educations.all().order_by('-end_year')
        context['skills'] = [rs.skill.name for rs in resume.resume_skills.all()]
        return context

    def test_func(self):
        resume = self.get_object()
        return resume.user == self.request.user

class ResumeCreateView(LoginRequiredMixin, FormView):
    template_name = 'resume_form.html'
    form_class = ResumeForm
    success_url = reverse_lazy('resume-list')

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        experience_formset = ExperienceFormSet(queryset=Experience.objects.none(), prefix='experience')
        education_formset = EducationFormSet(queryset=Education.objects.none(), prefix='education')
        skill_formset = SkillFormSet(queryset=Skill.objects.none(), prefix='skill')
        return render(request, self.template_name, {
            'form': form,
            'experience_formset': experience_formset,
            'education_formset': education_formset,
            'skill_formset': skill_formset,
        })

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        experience_formset = ExperienceFormSet(request.POST, queryset=Experience.objects.none(), prefix='experience')
        education_formset = EducationFormSet(request.POST, queryset=Education.objects.none(), prefix='education')
        skill_formset = SkillFormSet(request.POST, queryset=Skill.objects.none(), prefix='skill')
        if form.is_valid() and experience_formset.is_valid() and education_formset.is_valid() and skill_formset.is_valid():
            with transaction.atomic():
                resume = form.save(commit=False)
                resume.user = request.user
                resume.save()
                # Save experiences
                for exp_form in experience_formset:
                    if exp_form.cleaned_data and not exp_form.cleaned_data.get('DELETE', False):
                        exp = exp_form.save(commit=False)
                        exp.resume = resume
                        exp.save()
                # Save educations
                for edu_form in education_formset:
                    if edu_form.cleaned_data and not edu_form.cleaned_data.get('DELETE', False):
                        edu = edu_form.save(commit=False)
                        edu.resume = resume
                        edu.save()
                # Save skills (add to Skill model and link to resume via ResumeSkill)
                for skill_form in skill_formset:
                    if skill_form.cleaned_data and not skill_form.cleaned_data.get('DELETE', False):
                        skill_name = skill_form.cleaned_data['name']
                        skill, created = Skill.objects.get_or_create(name=skill_name)
                        ResumeSkill.objects.get_or_create(resume=resume, skill=skill)
            return redirect(self.success_url)
        return render(request, self.template_name, {
            'form': form,
            'experience_formset': experience_formset,
            'education_formset': education_formset,
            'skill_formset': skill_formset,
        })

class ResumeUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Resume
    fields = ['title', 'summary', 'contact_email', 'contact_phone', 'contact_address']
    template_name = 'resume_form.html'
    success_url = reverse_lazy('resume-list')

    def test_func(self):
        resume = self.get_object()
        return resume.user == self.request.user

class ResumeDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Resume
    template_name = 'resume_confirm_delete.html'
    success_url = reverse_lazy('resume-list')

    def test_func(self):
        resume = self.get_object()
        return resume.user == self.request.user

# --- Education CRUD views ---
class EducationCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Education
    fields = ['school', 'degree', 'start_year', 'end_year', 'score']
    template_name = 'education_form.html'

    def form_valid(self, form):
        resume = get_object_or_404(Resume, pk=self.kwargs['resume_id'])
        form.instance.resume = resume
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('resume-detail', kwargs={'pk': self.kwargs['resume_id']})

    def test_func(self):
        resume = get_object_or_404(Resume, pk=self.kwargs['resume_id'])
        return resume.user == self.request.user

class EducationUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Education
    fields = ['school', 'degree', 'start_year', 'end_year', 'score']
    template_name = 'education_form.html'

    def get_success_url(self):
        return reverse_lazy('resume-detail', kwargs={'pk': self.object.resume.pk})

    def test_func(self):
        return self.get_object().resume.user == self.request.user

class EducationDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Education
    template_name = 'education_confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('resume-detail', kwargs={'pk': self.object.resume.pk})

    def test_func(self):
        return self.get_object().resume.user == self.request.user

# --- Experience CRUD views ---
class ExperienceCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Experience
    fields = ['job_title', 'company', 'start_date', 'end_date', 'description']
    template_name = 'experience_form.html'

    def form_valid(self, form):
        resume = get_object_or_404(Resume, pk=self.kwargs['resume_id'])
        form.instance.resume = resume
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('resume-detail', kwargs={'pk': self.kwargs['resume_id']})

    def test_func(self):
        resume = get_object_or_404(Resume, pk=self.kwargs['resume_id'])
        return resume.user == self.request.user

class ExperienceUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Experience
    fields = ['job_title', 'company', 'start_date', 'end_date', 'description']
    template_name = 'experience_form.html'

    def get_success_url(self):
        return reverse_lazy('resume-detail', kwargs={'pk': self.object.resume.pk})

    def test_func(self):
        return self.get_object().resume.user == self.request.user

class ExperienceDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Experience
    template_name = 'experience_confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('resume-detail', kwargs={'pk': self.object.resume.pk})

    def test_func(self):
        return self.get_object().resume.user == self.request.user
