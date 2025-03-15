# employee_management/urls.py
from django.urls import path, include
from . import views

urlpatterns = [
    path("", views.go_to_login, name="go_to_login"),
    path(
        "auth/",
        include(
            [
                path("login/", views.login_view, name="login"),
                path("logout/", views.logout_view, name="logout"),
            ]
        ),
    ),
    # Management URLs.
    path(
        "management/",
        include(
            [
                path("", views.management_dashboard, name="management_dashboard"),
                path("all-employees", views.all_employees, name="all_employees"),
                path(
                    "present-employees",
                    views.present_employees,
                    name="present_employees",
                ),
                path('employee/details/<str:team_id>/', views.employee_details, name='employee_details'),
                # Projects
                path("all-projects", views.all_projects, name="all_projects"),
                path("add-projects", views.add_projects, name="add_projects"),
                path("delete-projects/<int:id>", views.delete_project, name="delete_project"),
                # Modules
                path("all-modules", views.all_modules, name="all_modules"),
                path("delete-modules/<int:id>", views.delete_module, name="delete_module"),
                path("add-modules", views.add_modules, name="add_modules"),
                # Tasks
                path("all-tasks", views.all_tasks, name="all_tasks"),
                path("delete-task/<int:id>", views.delete_task, name="delete_task"),
                path("add-tasks", views.add_tasks, name="add_tasks"),
                path('task/<int:task_id>/details/', views.task_details, name='task_details'),
                path('task/<int:task_id>/edit/', views.edit_task, name='edit_task'),
                path('team-task/<int:task_id>/details/', 
                     views.admin_task_details, 
                     name='admin_task_details'),
                path('all-tasks-overview/', 
                     views.management_view_all_tasks, 
                     name='management_view_all_tasks'),
                path('all-worklogs/', 
                     views.management_view_all_worklogs, 
                     name='management_view_all_worklogs'),
                path('add-team-task/', 
                     views.add_team_task, 
                     name='management_add_team_task'),
                # Ticket system
                path('tickets/', views.management_tickets, name='management_tickets'),
                path('tickets/<int:ticket_id>/', views.management_ticket_detail, name='management_ticket_detail'),
                # path('tickets/<int:ticket_id>/assign/', views.assign_ticket, name='assign_ticket'),
                path("all-requests", views.management_all_requests, name="management_all_requests"),
                path("process-request/<int:request_id>", views.management_process_request, name="management_process_request"),
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
                path('task/<int:task_id>/update/', views.add_task_response, name='add_task_response'),
                path("work-log/add/", views.add_work_log, name="add_work_log"),
                path("work-log/view/", views.view_work_logs, name="view_work_logs"),
                # Ticket system
                path("tickets/", views.team_tickets, name="team_tickets"),
                path("tickets/create/", views.create_ticket, name="create_ticket"),
                path("tickets/<int:ticket_id>/", views.ticket_detail, name="ticket_detail"),
                path("requests/submit/", views.team_submit_request, name="team_submit_request"),
                path("requests/view/", views.team_view_requests, name="team_view_requests"),
            ]
        ),
    ),
    # Management URLs
    # path("management/", views.management_dashboard, name="management_dashboard"),
    # path("management/add-employee/", views.add_employee, name="add_employee"),
    # path(
    #     "management/time-records/",
    #     views.manage_time_records,
    #     name="manage_time_records",
    # ),
    # path(
    #     "management/time-records/<int:record_id>/edit/",
    #     views.edit_time_record,
    #     name="edit_time_record",
    # ),
    # # Team Member URLs
    # path("team/", views.team_dashboard, name="team_dashboard"),
    # path("team/check-in/", views.check_in, name="check_in"),
    # path("team/check-out/", views.check_out, name="check_out"),
    # path("team/schedule/", views.view_schedule, name="view_schedule"),
    
    # Messaging URLs
    # path('messages/', views.messages_inbox, name='messages_inbox'),
    # path('messages/sent/', views.sent_messages, name='sent_messages'),
    # path('messages/compose/', views.compose_message, name='compose_message'),
    # path('messages/thread/<int:thread_id>/', views.view_thread, name='view_thread'),
    
    # Notification URLs
    # path('notifications/', views.notifications_list, name='notifications'),
    # path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
]
