import datetime

from django import forms

from .models import (Task, Job, Run, Scalar, ScalarGroup, CurveGroup, Curve,
 ArrayGroup, Array, Reference, Scheduler, Unit)


class NewTaskForm(forms.ModelForm):

    class Meta:
        model = Task
        fields = ('name', 'description', 'order', 'parent_task')

class NewJobForm(forms.ModelForm):

    class Meta:
        model = Job
        exclude = (id,)

class NewRunForm(forms.ModelForm):

    class Meta:
        model = Run
        exclude = (id,)

class NewScalarForm(forms.ModelForm):

    class Meta:
        model = Scalar
        exclude = (id,)

class NewScalarGroupForm(forms.ModelForm):

    class Meta:
        model = ScalarGroup
        exclude = (id,)

class NewCurveForm(forms.ModelForm):

    class Meta:
        model = Curve
        exclude = (id,)

class NewCurveGroupForm(forms.ModelForm):

    class Meta:
        model = CurveGroup
        exclude = (id,)

class NewArrayForm(forms.ModelForm):

    class Meta:
        model = Array
        exclude = (id,)

class NewArrayGroupForm(forms.ModelForm):

    class Meta:
        model = ArrayGroup
        exclude = (id,)

class NewReferenceForm(forms.ModelForm):

    class Meta:
        model = Reference
        exclude = (id,)

class NewSchedulerForm(forms.ModelForm):

    class Meta:
        model = Scheduler
        exclude = (id,)

class NewUnitForm(forms.ModelForm):

    class Meta:
        model = Unit
        exclude = (id,)
