# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

class Label(models.Model):
    name = models.CharField(max_length=8)
    icon = models.CharField(max_length=15)

    def __str__(self):
        return self.name

class Reference(models.Model):
    labels = models.ManyToManyField(Label, blank=True, null=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=250, blank=True, null=True)
    notes = models.CharField(max_length=250, blank=True, null=True)
    uri = models.CharField(max_length=500, blank=True, null=True)
    document_number = models.CharField(max_length=15)

    # Should eventually be its own table
    journal = models.CharField(max_length=350, blank=True, null=True)

    # Should eventually be its own table
    authors = models.CharField(max_length=350, blank=True, null=True)

    def __str__(self):
        return self.name

class Unit(models.Model):
    """
    Units is a reference table for keeping units of measure to represent any
    generic unit (such as meters, grams, etc.). Currently, intended to be used
    for the Scalar table; however, this should be general enough to be used in
    other places.
    """
    name = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=15)
    description = models.CharField(max_length=500, blank=True, null=True)
    notes = models.CharField(max_length=500, blank=True, null=True)

    def __str__(self):
        return "{0} ({1})".format(self.name, self.abbreviation)

class Scheduler(models.Model):
    """
    Scheduler is a reference table for representing scheduling tools to
    consistently track the scheduler that was used to submit a job (SLURM,
    MOAB, etc.)
    """
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=500, blank=True, null=True)
    is_active = models.BooleanField(blank=True, default=True)

    def __str__(self):
        return self.name

class InputDeck(models.Model):
    labels = models.ManyToManyField(Label, blank=True, null=True)
    name = models.CharField(max_length=25)
    description = models.CharField(max_length=250)
    notes = models.CharField(max_length=250, blank=True, null=True)
    author = models.CharField(max_length=10, blank=True, null=True)
    code = models.CharField(max_length=10, blank=True, null=True)
    labels = models.ManyToManyField(Label, blank=True, null=True)
    references = models.ManyToManyField(Reference, blank=True, null=True)
    contents = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Suite(models.Model):
    labels = models.ManyToManyField(Label, blank=True, null=True)
    name = models.CharField(max_length=25)
    description = models.CharField(max_length=250)
    notes = models.CharField(max_length=250, blank=True, null=True)
    labels = models.ManyToManyField(Label, blank=True, null=True)
    references = models.ManyToManyField(Reference, blank=True, null=True)
    visibility = models.CharField(max_length=10, blank=True, default='private')
    input_decks = models.ForeignKey(InputDeck, blank=True, null=True)

    def __str__(self):
        return self.name

class Workflow(models.Model):
    """Just start with a simple workflow model."""
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=250)
    notes = models.CharField(max_length=250, blank=True, null=True)
    labels = models.ManyToManyField(Label, blank=True, null=True)
    references = models.ManyToManyField(Reference, blank=True, null=True)
    suite = models.ForeignKey(Suite, blank=True, null=True)

    # The Workflow spec this workflow derived from. This is for exploring
    # concepts of being able to trace workflows from their source, and provide
    # the ability to derive workflows from other workflows.
    derived_from = models.ForeignKey("Workflow", blank=True, null=True)

    # Start with one file per workflow for now
    spec_file = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class TaskGroup(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=500, blank=True, null=True)
    notes = models.CharField(max_length=500)
    is_active = models.BooleanField(blank=True, default=True)

    def __str__(self):
        return self.name

class Task(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=250, blank=True, null=True)
    notes = models.CharField(max_length=250, default='')
    order = models.IntegerField(default=1)
    due_date = models.DateTimeField('date due', blank=True, null=True)
    created_by = models.CharField(max_length=25, blank=True, default='unknown')
    permissions = models.CharField(max_length=10, default='public')
    labels = models.ManyToManyField(Label, blank=True, null=True)
    references = models.ManyToManyField(Reference, blank=True, null=True)
    group = models.ManyToManyField(TaskGroup, blank=True, null=True)
    parent_task = models.ForeignKey(
                    "Task",
                    blank=True,
                    null=True
                    )

    def __str__(self):
        return self.name

class Job(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    jid = models.IntegerField(default=0)
    walltime = models.CharField(max_length=10, default='', null=True)
    partition = models.CharField(max_length=10, default='', null=True)
    nodes = models.IntegerField(default=1, null=True)
    bank = models.CharField(max_length=10, default='', null=True)
    output_dir = models.CharField(max_length=100, default='', null=True)
    notes = models.CharField(max_length=250, default='', null=True)
    references = models.ManyToManyField(Reference, blank=True, null=True)
    scheduler = models.ManyToManyField(Scheduler, blank=True, null=True)

    def __str__(self):
        return "{0} {1}".format(self.jid, self.name)

class Run(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=500, default='', null=True)
    termination_status = models.CharField(max_length=10, default='', null=True)
    code = models.CharField(max_length=10, default='', null=True)
    code_version = models.CharField(max_length=10, default='', null=True)
    run_by = models.CharField(max_length=10, default='', null=True)
    notes = models.CharField(max_length=500, default='', null=True)
    references = models.ManyToManyField(Reference, blank=True, null=True)

    def __str__(self):
        return self.name

class ScalarGroup(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=250)
    notes = models.CharField(max_length=250, null=True)
    parent_group = models.ForeignKey("ScalarGroup", blank=True, null=True)

    def __str__(self):
        return self.name

class Scalar(models.Model):
    run = models.ForeignKey(Run, on_delete=models.CASCADE)
    group = models.ForeignKey(ScalarGroup, blank=True, null=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    description = models.CharField(max_length=250, blank=True, null=True)
    value = models.CharField(max_length=10, blank=True, null=True)
    unit = models.ForeignKey(Unit, blank=True, null=True)
    label = models.CharField(max_length=10, blank=True, null=True)
    notes = models.CharField(max_length=250, blank=True, null=True)
    permissions = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.name

class CurveGroup(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=500)
    notes = models.CharField(max_length=500, null=True)
    parent_group = models.ForeignKey("ScalarGroup", blank=True, null=True)

    def __str__(self):
        return self.name

class Curve(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=500, blank=True, null=True)
    notes = models.CharField(max_length=500, blank=True, null=True)
    group = models.ForeignKey(CurveGroup, blank=True, null=True)
    label_x_axis = models.CharField(max_length=50, blank=True, null=True)
    label_y_axis = models.CharField(max_length=50, blank=True, null=True)
    run = models.ForeignKey(Run, on_delete=models.CASCADE)

    # Going to simplify this by assuming an Ultra file format to start with
    xy_pairs = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class ArrayGroup(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=500)
    notes = models.CharField(max_length=500, null=True)
    parent_group = models.ForeignKey("ScalarGroup", blank=True, null=True)
    unit = models.ForeignKey(Unit, blank=True, null=True)

    def __str__(self):
        return self.name

class Array(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=500, blank=True, null=True)
    notes = models.CharField(max_length=500, blank=True, null=True)
    group = models.ForeignKey(ArrayGroup, blank=True, null=True)
    run = models.ForeignKey(Run, on_delete=models.CASCADE)

    # Not sure yet the best wayt to store this, but for now just assume
    # comma seperated values (e.g. 1, 2, 3, 4, 5, etc.)
    values = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class WorkflowHistory(models.Model):
    """
    Tracks when a workflow has been run. This table stores the high-level
    metadata of the workflow as direved from the spec. The Workflow represents
    a defintion of a workflow and the WorkflowHistory tracks each time the
    workflow was run.
    """
    name = models.CharField(max_length=100)
    workflow = models.ForeignKey(Workflow)
    labels = models.ManyToManyField(Label, blank=True, null=True)
    references = models.ManyToManyField(Reference, blank=True, null=True)
    archive = models.BooleanField(blank=True, default=False)

    # States will eventually have a reference table
    state = models.CharField(max_length=8, blank=True, default='Queued')

    # Explore the concept of storing details of a Workflow with the Task table.
    # In this case, a Task should not exist until the workflow is run in which
    # the details of the workflow (including individual runs) will be stored in
    # the database.
    task = models.ForeignKey(Task, blank=True, null=True)

    def __str__(self):
        return self.name

class Publication(models.Model):
    task = models.ForeignKey(Task)
    labels = models.ManyToManyField(Label, blank=True, null=True)
    references = models.ManyToManyField(Reference, blank=True, null=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    description = models.CharField(max_length=250, blank=True, null=True)
    notes = models.CharField(max_length=250, blank=True, null=True)
    report_uri = models.CharField(max_length=500, blank=True, null=True)
    visibility = models.CharField(max_length=10, blank=True, default='private')

    # This will be eventually be a reference table of states.
    state = models.CharField(max_length=25, blank=True, default='In Review')

    def __str__(self):
        return self.name

class Approver(models.Model):
    publication = models.ForeignKey(Task)
    user = models.CharField(max_length=50)
    status = models.CharField(max_length=25, blank=True, default='Pending')

    # This may eventually turn into it's own table.
    comments = models.CharField(max_length=250, blank=True, null=True)
