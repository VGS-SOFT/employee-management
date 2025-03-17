# employee_management/urls.py
from django.urls import path, include
from . import views
from .view import authentication_view, management_view

urlpatterns = [
    path("", views.go_to_login, name="go_to_login"),
    # Authentication URL's
    path(
        "auth/",
        include(
            [
                path("login/", authentication_view.login_view, name="login"),
                path("logout/", authentication_view.logout_view, name="logout"),
            ]
        ),
    ),
    # Management URLs.
    path(
        "management/",
        include(
            [
                path("", management_view.dashboard, name="management_dashboard"),
                # Employee details.
                path(
                    "all-employees", management_view.all_employees, name="all_employees"
                ),
                path(
                    "present-employees",
                    management_view.present_employees,
                    name="present_employees",
                ),
                path(
                    "employee/details/<str:team_id>/",
                    management_view.employee_details,
                    name="employee_details",
                ),
                # Project Details.
                path("all-projects", management_view.all_projects, name="all_projects"),
                path("add-project", management_view.add_project, name="add_project"),
                path(
                    "delete-projects/<int:id>",
                    management_view.delete_project,
                    name="delete_project",
                ),
                # Modules
                path("all-modules", management_view.all_modules, name="all_modules"),
                path(
                    "delete-modules/<int:id>",
                    management_view.delete_module,
                    name="delete_module",
                ),
                path("add-modules", management_view.add_module, name="add_module"),
                # Tasks
                path(
                    "team-task/<int:task_id>/details/",
                    management_view.admin_task_details,
                    name="admin_task_details",
                ),
                path(
                    "all-tasks-overview/",
                    management_view.management_view_all_tasks,
                    name="management_view_all_tasks",
                ),
                # worklog
                path(
                    "all-worklogs/",
                    management_view.management_view_all_worklogs,
                    name="management_view_all_worklogs",
                ),
                # Ticket system
                path(
                    "tickets/",
                    management_view.management_tickets,
                    name="management_tickets",
                ),
                path(
                    "tickets/<int:ticket_id>/",
                    management_view.management_ticket_detail,
                    name="management_ticket_detail",
                ),
                # path('tickets/<int:ticket_id>/assign/', views.assign_ticket, name='assign_ticket'),
                path(
                    "all-requests",
                    management_view.management_all_requests,
                    name="management_all_requests",
                ),
                path(
                    "process-request/<int:request_id>",
                    management_view.management_process_request,
                    name="management_process_request",
                ),
            ]
        ),
    ),
    # Team URLs
    path(
        "team/",
        include(
            [
                path("", views.team_dashboard, name="team_dashboard"),
                path("check-in-out/", views.check_in_out, name="check_in_out"),
                path("profile/", views.team_profile, name="team_profile"),
                path("profile/update/", views.update_profile, name="update_profile"),
                # Tasks
                path("all-tasks/", views.team_all_tasks, name="team_all_tasks"),
                path("tasks/", views.team_view_all_task, name="team_view_all_task"),
                path("add-tasks/", views.team_view_add_task, name="team_view_add_task"),
                path(
                    "task/<int:task_id>/update/",
                    views.add_task_response,
                    name="add_task_response",
                ),
                path("work-log/add/", views.add_work_log, name="add_work_log"),
                path("work-log/view/", views.view_work_logs, name="view_work_logs"),
                # Ticket system
                path("tickets/", views.team_tickets, name="team_tickets"),
                path("tickets/create/", views.create_ticket, name="create_ticket"),
                path(
                    "tickets/<int:ticket_id>/",
                    views.ticket_detail,
                    name="ticket_detail",
                ),
                path(
                    "requests/submit/",
                    views.team_submit_request,
                    name="team_submit_request",
                ),
                path(
                    "requests/view/",
                    views.team_view_requests,
                    name="team_view_requests",
                ),
            ]
        ),
    ),
]
