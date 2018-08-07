# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.template import loader
from django.views.generic.base import View
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.views.generic.edit import FormView, UpdateView, CreateView

from .models import (Task, Job, Run, Scalar, ScalarGroup, Curve, CurveGroup,
    Array, ArrayGroup, Scheduler, Unit, Reference)
from .forms import (NewTaskForm, NewJobForm, NewRunForm, NewScalarForm,
    NewScalarGroupForm, NewCurveGroupForm, NewCurveForm, NewArrayForm,
    NewArrayGroupForm, NewReferenceForm, NewSchedulerForm, NewUnitForm)

# @todo: The edit template is becomming generic enough that it can probably
# be moved out of the task dir.
EDIT_TEMPLATE = 'sinaweb/tasks/edit.html'
PLOT_TEMPLATE = 'sinaweb/plotly.html'

def index(request):
    template = loader.get_template('sinaweb/index.html')
    context = {'hello': "Hello, context world!"}
    return HttpResponse(template.render(context, request))

def groups_list(request):
    template = loader.get_template('sinaweb/groups/index.html')
    context = {}
    return HttpResponse(template.render(context, request))

class GroupNew(View):

    def get(self, request, *args, **kwargs):
        return HttpResponse(request)

class ScalarGroupNew(CreateView):
    template_name = EDIT_TEMPLATE
    form_class = NewScalarGroupForm
    success_url = '/sinaweb/groups/scalars'

    def form_valid(self, form):
        return super(ScalarGroupNew, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(ScalarGroupNew, self).get_context_data(**kwargs)
        context['title'] = "New Scalar Group"
        return context

class ScalarGroupEdit(UpdateView):
    template_name = EDIT_TEMPLATE
    model = ScalarGroup
    form_class = NewScalarGroupForm
    success_url = '/sinaweb/groups/scalars'

    def get_context_data(self, **kwargs):
        context = super(ScalarGroupEdit, self).get_context_data(**kwargs)
        context['title'] = "Edit Scalar Group"
        return context

class ScalarGroupList(ListView):
    model = ScalarGroup
    template_name = 'sinaweb/groups/list.html'

    def get_context_data(self, **kwargs):
        context = super(ScalarGroupList, self).get_context_data(**kwargs)
        context['title'] = "Scalar Groups"
        context['group'] = 'scalar'
        return context

class CurveGroupNew(CreateView):
    template_name = EDIT_TEMPLATE
    form_class = NewCurveGroupForm
    success_url = '/sinaweb/groups/curves'

    def form_valid(self, form):
        return super(CurveGroupNew, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(CurveGroupNew, self).get_context_data(**kwargs)
        context['title'] = "New Curve Group"
        return context

class CurveGroupEdit(UpdateView):
    template_name = EDIT_TEMPLATE
    model = CurveGroup
    form_class = NewCurveGroupForm
    success_url = '/sinaweb/groups/curves'

    def get_context_data(self, **kwargs):
        context = super(CurveGroupEdit, self).get_context_data(**kwargs)
        context['title'] = "Edit Curve Group"
        return context

class CurveGroupList(ListView):
    model = CurveGroup
    template_name = 'sinaweb/groups/list.html'

    def get_context_data(self, **kwargs):
        context = super(CurveGroupList, self).get_context_data(**kwargs)
        context['title'] = "Curve Groups"
        context['group'] = 'curve'
        return context

class CurveNew(CreateView):
    template_name = EDIT_TEMPLATE
    form_class = NewCurveForm

    def get_initial(self):
        run = self.kwargs.get('pk')
        return {'run':run}

    def get_success_url(self):
        return reverse('run_details', args=(self.kwargs['pk'],))

    def form_valid(self, form):
        return super(CurveNew, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(CurveNew, self).get_context_data(**kwargs)
        context['title'] = "New Curve"
        return context

class CurveEdit(UpdateView):
    template_name = EDIT_TEMPLATE
    model = Curve
    form_class = NewCurveForm

    def get_context_data(self, **kwargs):
        context = super(CurveEdit, self).get_context_data(**kwargs)
        context['title'] = "Edit Curve"
        return context

    def get_success_url(self):
        # This probably isn't the ideal way to redirect back to the run details
        # page as this requires making another query for the scalar (which
        # might already be accessable from within this class). I'll need to
        # revisit the logic here; however, for now this works for the purpose
        # of the demo.
        curve = Curve.objects.get(pk=self.kwargs["pk"])

        # Redirect back to the run details page with the run details id
        return reverse('run_details', args=(curve.run.id,))

class CurvePlot(DetailView):
    template_name = PLOT_TEMPLATE
    model = Curve

    def get_context_data(self, **kwargs):
        context = super(CurvePlot, self).get_context_data(**kwargs)
        context['title'] = "Plot Curve"
        return context

class ArrayGroupNew(CreateView):
    template_name = EDIT_TEMPLATE
    form_class = NewArrayGroupForm
    success_url = '/sinaweb/groups/arrays'

    def form_valid(self, form):
        return super(ArrayGroupNew, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(ArrayGroupNew, self).get_context_data(**kwargs)
        context['title'] = "New Array Group"
        return context

class ArrayGroupEdit(UpdateView):
    template_name = EDIT_TEMPLATE
    model = ArrayGroup
    form_class = NewArrayGroupForm
    success_url = '/sinaweb/groups/arrays'

    def get_context_data(self, **kwargs):
        context = super(ArrayGroupEdit, self).get_context_data(**kwargs)
        context['title'] = "Edit Array Group"
        return context

class ArrayGroupList(ListView):
    model = ArrayGroup
    template_name = 'sinaweb/groups/list.html'

    def get_context_data(self, **kwargs):
        context = super(ArrayGroupList, self).get_context_data(**kwargs)
        context['title'] = "Array Groups"
        context['group'] = 'array'
        return context

class ArrayNew(CreateView):
    template_name = EDIT_TEMPLATE
    form_class = NewArrayForm

    def get_initial(self):
        run = self.kwargs.get('pk')
        return {'run':run}

    def get_success_url(self):
        return reverse('run_details', args=(self.kwargs['pk'],))

    def form_valid(self, form):
        return super(ArrayNew, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(ArrayNew, self).get_context_data(**kwargs)
        context['title'] = "New Array"
        return context

class ArrayEdit(UpdateView):
    template_name = EDIT_TEMPLATE
    model = Array
    form_class = NewArrayForm

    def get_context_data(self, **kwargs):
        context = super(ArrayEdit, self).get_context_data(**kwargs)
        context['title'] = "Edit Array"
        return context

    def get_success_url(self):
        # This probably isn't the ideal way to redirect back to the run details
        # page as this requires making another query for the scalar (which
        # might already be accessable from within this class). I'll need to
        # revisit the logic here; however, for now this works for the purpose
        # of the demo.
        array = Array.objects.get(pk=self.kwargs["pk"])

        # Redirect back to the run details page with the run details id
        return reverse('run_details', args=(array.run.id,))

class SchedulerNew(CreateView):
    template_name = EDIT_TEMPLATE
    form_class = NewSchedulerForm
    success_url = '/sinaweb/groups/schedulers'

    def form_valid(self, form):
        return super(SchedulerNew, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(SchedulerNew, self).get_context_data(**kwargs)
        context['title'] = "New Scheduler"
        return context

class SchedulerEdit(UpdateView):
    template_name = EDIT_TEMPLATE
    model = Scheduler
    form_class = NewSchedulerForm
    success_url = '/sinaweb/groups/schedulers'

    def get_context_data(self, **kwargs):
        context = super(SchedulerEdit, self).get_context_data(**kwargs)
        context['title'] = "Edit Scheduler Group"
        return context

class SchedulerList(ListView):
    model = Scheduler
    template_name = 'sinaweb/groups/list.html'

    def get_context_data(self, **kwargs):
        context = super(SchedulerList, self).get_context_data(**kwargs)
        context['title'] = "Scheduler Groups"
        context['group'] = 'scheduler'
        return context

class UnitNew(CreateView):
    template_name = EDIT_TEMPLATE
    form_class = NewUnitForm
    success_url = '/sinaweb/groups/units'

    def form_valid(self, form):
        return super(UnitNew, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(UnitNew, self).get_context_data(**kwargs)
        context['title'] = "New Unit"
        return context

class UnitEdit(UpdateView):
    template_name = EDIT_TEMPLATE
    model = Unit
    form_class = NewUnitForm
    success_url = '/sinaweb/groups/units'

    def get_context_data(self, **kwargs):
        context = super(UnitEdit, self).get_context_data(**kwargs)
        context['title'] = "Edit Unit Group"
        return context

class UnitList(ListView):
    model = Unit
    template_name = 'sinaweb/groups/list.html'

    def get_context_data(self, **kwargs):
        context = super(UnitList, self).get_context_data(**kwargs)
        context['title'] = "Unit Groups"
        context['group'] = 'unit'
        return context

class ReferenceNew(CreateView):
    template_name = EDIT_TEMPLATE
    form_class = NewReferenceForm
    success_url = '/sinaweb/groups/references'

    def form_valid(self, form):
        return super(ReferenceNew, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(ReferenceNew, self).get_context_data(**kwargs)
        context['title'] = "New Reference"
        return context

class ReferenceList(ListView):
    model = Reference
    template_name = 'sinaweb/groups/references/list.html'

    def get_context_data(self, **kwargs):
        context = super(ReferenceList, self).get_context_data(**kwargs)
        context['title'] = "Reference Groups"
        return context

def task_new(request, pk=None):
    if not pk:
        title = "New Task"
    else:
        title = "New Subtask"
    if request.method == "POST":
        form = NewTaskForm(request.POST)
        if form.is_valid():
            post = form.save()

        if pk: # Adding a subtask
            return redirect('task_details', pk=pk)
        return redirect('tasks_list')
    else:
        form = NewTaskForm(initial={'parent_task':pk})
        context = {'title':title,'form':form}
        return render(request, EDIT_TEMPLATE, context)

def job_new(request, pk=None):
    title = "New Job"
    if request.method == "POST":
        form = NewJobForm(request.POST)
        if form.is_valid():
            form.save()
        return redirect('task_details', pk=pk)
    else:
        form = NewJobForm(initial={'task':pk})
        context = {'title':title,'form':form}
        return render(request, EDIT_TEMPLATE, context)

def run_new(request, pk=None):
    title = "New Run"
    if request.method == "POST":
        form = NewRunForm(request.POST)
        if form.is_valid():
            form.save()
        return redirect('job_details', pk=pk)
    else:
        form = NewRunForm(initial={'job':pk})
        context = {'title':title, 'form':form}
        return render(request, EDIT_TEMPLATE, context)

def scalar_new(request, pk=None):
    title = "New Scalar"
    if request.method == "POST":
        form = NewScalarForm(request.POST)
        if form.is_valid():
            form.save()
        return redirect('run_details', pk=pk)
    else:
        form = NewScalarForm(initial={'run':pk})
        context = {'title':title, 'form':form}
        return render(request, EDIT_TEMPLATE, context)

class ScalarEdit(UpdateView):
    template_name = EDIT_TEMPLATE
    model = Scalar
    form_class = NewScalarForm

    def get_context_data(self, **kwargs):
        context = super(ScalarEdit, self).get_context_data(**kwargs)
        context['title'] = "Edit Scalar"
        return context

    def get_success_url(self):
        # This probably isn't the ideal way to redirect back to the run details
        # page as this requires making another query for the scalar (which
        # might already be accessable from within this class). I'll need to
        # revisit the logic here; however, for now this works for the purpose
        # of the demo.
        scalar = Scalar.objects.get(pk=self.kwargs["pk"])

        # Redirect back to the run details page with the run details id
        return reverse('run_details', args=(scalar.run.id,))

class TasksList(ListView):
    model = Task
    template_name = 'sinaweb/tasks/list.html'

    def get_context_data(self, **kwargs):
        return super(TasksList, self).get_context_data(**kwargs)

    def get_queryset(self):
        return Task.objects.filter(parent_task=None)

class TaskEdit(UpdateView):
    template_name = EDIT_TEMPLATE
    model = Task
    form_class = NewTaskForm

    def get_success_url(self):
        if 'pk' in self.kwargs['pk']:
            return reverse('task_details', args=(self.kwargs['pk'],))
        else:
            return reverse('tasks_list')

    def get_context_data(self, **kwargs):
        context = super(TaskEdit, self).get_context_data(**kwargs)
        context['title'] = "Edit Task"
        return context

class TaskDetails(DetailView):
    model = Task
    template_name = 'sinaweb/tasks/details.html'

    def get_context_data(self, **kwargs):
        return super(TaskDetails, self).get_context_data(**kwargs)

class JobDetails(DetailView):
    model = Job
    template_name = 'sinaweb/job/details.html'

    def get_context_data(self, **kwargs):
        return super(JobDetails, self).get_context_data(**kwargs)

class JobEdit(UpdateView):
    template_name = EDIT_TEMPLATE
    model = Job
    form_class = NewJobForm

    def get_context_data(self, **kwargs):
        context = super(JobEdit, self).get_context_data(**kwargs)
        context['title'] = "Edit Job"
        return context

    def get_success_url(self):
        # This probably isn't the ideal way to redirect back to the run details
        # page as this requires making another query for the scalar (which
        # might already be accessable from within this class). I'll need to
        # revisit the logic here; however, for now this works for the purpose
        # of the demo.
        job = Job.objects.get(pk=self.kwargs["pk"])

        # Redirect back to the run details page with the run details id
        return reverse('task_details', args=(job.task.id,))

class RunDetails(DetailView):
    model = Run
    template_name = 'sinaweb/run/details.html'

    def get_context_data(self, **kwargs):
        return super(RunDetails, self).get_context_data(**kwargs)

class RunEdit(UpdateView):
    template_name = EDIT_TEMPLATE
    model = Run
    form_class = NewRunForm

    def get_context_data(self, **kwargs):
        context = super(RunEdit, self).get_context_data(**kwargs)
        context['title'] = "Edit Run"
        return context

    def get_success_url(self):
        # This probably isn't the ideal way to redirect back to the run details
        # page as this requires making another query for the scalar (which
        # might already be accessable from within this class). I'll need to
        # revisit the logic here; however, for now this works for the purpose
        # of the demo.
        run = Run.objects.get(pk=self.kwargs["pk"])

        # Redirect back to the run details page with the run details id
        return reverse('job_details', args=(run.job.id,))
