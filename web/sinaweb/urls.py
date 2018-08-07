"""SinaWeb URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import include, url
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from decorator_include import decorator_include

from . import views

urlpatterns = [
    # e.g., sinaweb/
    url(r'^$', login_required(views.index), name='index'),

    # e.g., sinaweb/tasks
    url(r'^tasks$', login_required(views.TasksList.as_view()), name='tasks_list'),

    # e.g., sinaweb/task/new
    url(r'^task/new$', login_required(views.task_new), name='task_new'),

    # e.g., sinaweb/task/edit/<task_pk>
    url(r'^task/edit/(?P<pk>[0-9]+)$',
        login_required(views.TaskEdit.as_view()),
        name='edit_task'
        ),

    # e.g., sinaweb/task/new/1 (for subtasks)
    url(r'^task/new/(?P<pk>[0-9]+)$', login_required(views.task_new), name='task_new'),

    # e.g., sinaweb/tasks/1
    url(r'^task/(?P<pk>[0-9]+)$',
        login_required(views.TaskDetails.as_view()),
        name='task_details'
        ),

    # e.g., sinaweb/task/new/<task_pk> (for subtasks)
    url(r'^task/(?P<pk>[0-9]+)/job/new$', login_required(views.job_new), name='job_new'),

    # e.g., sinaweb/job/1
    url(r'^job/(?P<pk>[0-9]+)$',
        login_required(views.JobDetails.as_view()),
        name='job_details'
        ),

    # e.g., sinaweb/job/edit/<job_pk>
    url(r'^job/edit/(?P<pk>[0-9]+)$',
        login_required(views.JobEdit.as_view()),
        name='job_edit'
        ),

    # e.g., sinaweb/job/new/1
    url(r'^job/new/(?P<pk>[0-9]+)$', login_required(views.run_new), name='run_new'),

    # e.g., sinaweb/run/1
    url(r'^run/(?P<pk>[0-9]+)$',
        login_required(views.RunDetails.as_view()),
        name='run_details'
        ),

    # e.g., sinaweb/run/edit/<run_pk>
    url(r'^run/edit/(?P<pk>[0-9]+)$',
        login_required(views.RunEdit.as_view()),
        name='run_edit'
        ),

    # e.g., sinaweb/scalar/new/<run_pk>
    url(r'^scalar/new/(?P<pk>[0-9]+)$',
        login_required(views.scalar_new),
        name='scalar_new'
        ),

    # e.g., sinaweb/scalar/edit/<scalar_pk>
    url(r'^scalar/edit/(?P<pk>[0-9]+)$',
        login_required(views.ScalarEdit.as_view()),
        name='scalar_edit'
        ),

    # e.g., sinaweb/curve/new/<run_pk>
    url(r'^curve/new/(?P<pk>[0-9]+)$',
        login_required(views.CurveNew.as_view()),
        name='curve_new'
        ),

    # e.g., sinaweb/curve/edit/<curve_pk>
    url(r'^curve/edit/(?P<pk>[0-9]+)$',
        login_required(views.CurveEdit.as_view()),
        name='curve_edit'
        ),

    # e.g., sinaweb/curve/plot/<curve_pk>
    url(r'^curve/plot/(?P<pk>[0-9]+)$',
        login_required(views.CurvePlot.as_view()),
        name='curve_plot'
        ),

    # e.g., sinaweb/array/new/<run_pk>
    url(r'^array/new/(?P<pk>[0-9]+)$',
        login_required(views.ArrayNew.as_view()),
        name='array_new'
        ),

    # e.g., sinaweb/array/edit/<array_pk>
    url(r'^array/edit/(?P<pk>[0-9]+)$',
        login_required(views.ArrayEdit.as_view()),
        name='array_edit'
        ),

    # e.g., sinaweb/groups
    url(r'^groups$', login_required(views.groups_list), name='groups_list'),

    # e.g., sinaweb/groups/scalars
    url(r'^groups/scalars$',
        login_required(views.ScalarGroupList.as_view()),
        name='scalar_group_list'
        ),

    # e.g., sinaweb/groups/scalar/edit/<run_pk>
    url(r'^groups/scalar/edit/(?P<pk>[0-9]+)$',
        login_required(views.ScalarGroupEdit.as_view()),
        name='scalar_group_edit'
        ),

    # e.g., sinaweb/groups/curves
    url(r'^groups/curves$',
        login_required(views.CurveGroupList.as_view()),
        name='curve_group_list'
        ),

    # e.g., sinaweb/curve/edit/<run_pk>
    url(r'^groups/curve/edit/(?P<pk>[0-9]+)$',
        login_required(views.CurveGroupEdit.as_view()),
        name='curve_group_edit'
        ),

    # e.g., sinaweb/groups/arrays
    url(r'^groups/arrays$',
        login_required(views.ArrayGroupList.as_view()),
        name='array_group_list'
        ),

    # e.g., sinaweb/groups/array/edit/<run_pk>
    url(r'^groups/array/edit/(?P<pk>[0-9]+)$',
        login_required(views.ArrayGroupEdit.as_view()),
        name='array_group_edit'
        ),

    # e.g., sinaweb/groups/schedulers
    url(r'^groups/schedulers$',
        login_required(views.SchedulerList.as_view()),
        name='scheduler_group_list'
        ),

    # e.g., sinaweb/groups/scheduler/edit/<run_pk>
    url(r'^groups/scheduler/edit/(?P<pk>[0-9]+)$',
        login_required(views.SchedulerEdit.as_view()),
        name='scheduler_edit'
        ),

    # e.g., sinaweb/groups/schedulers
    url(r'^groups/units$',
        login_required(views.UnitList.as_view()),
        name='unit_group_list'
        ),

    # e.g., sinaweb/unit/edit/<run_pk>
    url(r'^groups/unit/edit/(?P<pk>[0-9]+)$',
        login_required(views.UnitEdit.as_view()),
        name='unit_edit'
        ),

    # e.g., sinaweb/groups/references
    url(r'^groups/references$',
        login_required(views.ReferenceList.as_view()),
        name='reference_list'
        ),

    # e.g., sinaweb/groups/new
    url(r'^groups/new$',
        login_required(views.GroupNew.as_view()),
        name='group_new'
        ),

    # e.g., sinaweb/groups/scalar/new
    url(r'^groups/new/scalar$',
        login_required(views.ScalarGroupNew.as_view()),
        name='scalar_group_new'
        ),

    # e.g., sinaweb/groups/scalar/new
    url(r'^groups/new/curve$',
        login_required(views.CurveGroupNew.as_view()),
        name='curve_group_new'
        ),

    # e.g., sinaweb/groups/scalar/new
    url(r'^groups/new/array$',
        login_required(views.ArrayGroupNew.as_view()),
        name='array_group_new'
        ),

    # e.g., sinaweb/groups/scheduler/new
    url(r'^groups/new/scheduler$',
        login_required(views.SchedulerNew.as_view()),
        name='scheduler_group_new'
        ),

    # e.g., sinaweb/groups/unit/new
    url(r'^groups/new/unit$',
        login_required(views.UnitNew.as_view()),
        name='unit_group_new'
        ),

    # e.g., /groups/references/new
    url(r'^groups/new/references$',
        login_required(views.ReferenceNew.as_view()),
        name='reference_new'
        ),

    # e.g., admin/
    url(r'^admin/', decorator_include(login_required, admin.site.urls)),

    # e.g., login/ logout/
    url(r'^login/', auth_views.login, name='login'),
    url(r'^logout/', auth_views.logout, name='logout'),

    # e.g. any other page...
    #url(r'^', login_required(views.index), name='index'),
]
