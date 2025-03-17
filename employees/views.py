# employee_management/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from datetime import datetime, timedelta, time
from calendar import monthrange
from django.db.models import Sum, F, ExpressionWrapper, fields
from django.db.models.functions import ExtractMonth, ExtractYear

from employees.view.management_view import get_status_display
from .models import (
    TicketAttachment,
    User,
    Team,
    TimeRecord,
    Holiday,
    WorkSchedule,
    PersonalBreak,
    Management,
    Projects,
    Status,
    Modules,
    Task,
    TaskResponse,
    MessageThread,
    Message,
    MessageRecipient,
    Notification,
    TeamTask,
    Manager,
    WorkLog,
    Ticket,
    TicketCategory,
    TicketPriority,
    TicketComment,
    TeamRequest,
)
from django.core.paginator import Paginator
from django.http import HttpResponsePermanentRedirect, JsonResponse
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.db.models import Q
from django.utils.formats import date_format
from django.db.models import Count
import json


# Common Views
def go_to_login(request):
    return HttpResponsePermanentRedirect(reverse("login"))


@login_required
def manage_time_records(request):
    """View for managing time records"""
    if request.user.role != "MANAGEMENT":
        messages.error(request, "Access denied. Management privileges required.")
        return redirect("team_dashboard")

    # Get filters from request
    user_id = request.GET.get("user")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    # Base query
    records = TimeRecord.objects.select_related("user").all()

    # Apply filters
    if user_id:
        records = records.filter(user_id=user_id)
    if start_date:
        records = records.filter(check_in__date__gte=start_date)
    if end_date:
        records = records.filter(check_in__date__lte=end_date)

    # Paginate results
    paginator = Paginator(records.order_by("-check_in"), 20)
    page = request.GET.get("page")
    records = paginator.get_page(page)

    context = {
        "records": records,
        "team_members": User.objects.filter(role="TEAM"),
    }

    return render(request, "employee_management/manage_time_records.html", context)


@login_required
def edit_time_record(request, record_id):
    """View for editing individual time records"""
    if request.user.role != "MANAGEMENT":
        messages.error(request, "Access denied. Management privileges required.")
        return redirect("team_dashboard")

    record = get_object_or_404(TimeRecord, id=record_id)

    if request.method == "POST":
        try:
            # Update record
            record.check_in = datetime.strptime(
                request.POST.get("check_in"), "%Y-%m-%dT%H:%M"
            )
            check_out = request.POST.get("check_out")
            if check_out:
                record.check_out = datetime.strptime(check_out, "%Y-%m-%dT%H:%M")

            record.notes = request.POST.get("notes", "")
            record.mark_modified(request.user)
            record.full_clean()  # Validate the record
            record.save()

            messages.success(request, "Time record updated successfully")
            return redirect("manage_time_records")

        except Exception as e:
            messages.error(request, f"Error updating record: {str(e)}")

    # Check if user is management
    if request.user.role != "MANAGEMENT":
        messages.error(request, "Only management users can create projects.")
        return redirect("dashboard")

    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        status_id = request.POST.get("status")

        if not name:
            messages.error(request, "Project name is required.")
            return redirect("all_projects")

        try:
            status = Status.objects.get(id=status_id)
            management_user = User.objects.get(email=request.user.email)
            management = Management.objects.get(user=management_user)

            Projects.objects.create(
                name=name,
                description=description,
                status=status,
                created_by=management,
            )
            messages.success(request, "Project created successfully!")
            return redirect("all_projects")

        except Status.DoesNotExist:
            messages.error(request, "Invalid status selected.")
            return redirect("add_project")
        except Exception as e:
            messages.error(request, f"Error creating project: {str(e)}")
            return redirect("add_project")

    # For GET request
    statuses = Status.objects.filter(is_active=True)
    context = {"statuses": statuses}
    return render(request, "admins/add_projects.html", context)

    context = {"record": record}
    return render(request, "employee_management/edit_time_record.html", context)


@login_required
def add_modules(request):
    # Check if user is management
    if request.user.role != "MANAGEMENT":
        messages.error(request, "Only management users can create modules.")
        return redirect("dashboard")

    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        status_id = request.POST.get("status")
        project_id = request.POST.get("project")

        if not name:
            messages.error(request, "module name is required.")
            return redirect("all_modules")

        try:
            status = Status.objects.get(id=status_id)
            project = Projects.objects.get(id=project_id)
            management_user = User.objects.get(email=request.user.email)
            management = Management.objects.get(user=management_user)

            Modules.objects.create(
                name=name,
                description=description,
                status=status,
                project=project,
                created_by=management,
            )
            messages.success(request, "module created successfully!")
            return redirect("all_modules")

        except Status.DoesNotExist:
            messages.error(request, "Invalid status selected.")
            return redirect("add_modules")
        except Exception as e:
            messages.error(request, f"Error creating module: {str(e)}")
            return redirect("add_modules")

    # For GET request
    statuses = Status.objects.filter(is_active=True)
    projects = Projects.objects.filter(is_active=True)
    context = {"statuses": statuses, "projects": projects}
    return render(request, "admins/add_modules.html", context)


@login_required
def all_tasks(request):
    if request.user.role != "MANAGEMENT":
        logout(request)
        messages.error(request, "Only management users can delete projects.")
        return redirect("login")

    try:
        data = Task.objects.filter(is_active=True)
        context = {"data": data}
        return render(request, "admins/all_tasks.html", context)
    except Exception as es:
        print("Error while fetching the data from the all_tasks\n\n", es)
        return redirect("all_tasks")


@login_required
def delete_task(request, id: int):
    if request.user.role != "MANAGEMENT":
        logout(request)
        messages.error(request, "Only management users can delete tasks.")
        return redirect("login")

    try:
        task = get_object_or_404(Task, id=id)
        task.delete()
        messages.success(request, "task deleted successfully")
    except Exception as e:
        print(f"Error while deleting the task: {e}")
        messages.error(request, "An error occurred while deleting the task.")

    return redirect("all_tasks")


@login_required
def add_tasks(request):
    # Ensure only management users can create tasks
    if request.user.role != "MANAGEMENT":
        messages.error(request, "Only management users can create tasks.")
        return redirect("dashboard")

    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        status_id = request.POST.get("status")
        project_id = request.POST.get("project")
        module_id = request.POST.get("module")
        assigned_team_ids = request.POST.getlist("assigned_to")

        if not name:
            messages.error(request, "Task name is required.")
            return redirect("add_tasks")

        try:
            status = Status.objects.get(id=status_id, is_active=True)
            project = Projects.objects.get(id=project_id, is_active=True)
            module = Modules.objects.get(id=module_id, is_active=True)

            # Ensure module belongs to the selected project
            if module.project != project:
                messages.error(
                    request, "Selected module does not belong to the selected project."
                )
                return redirect("add_tasks")

            management_user = User.objects.get(email=request.user.email)
            management = Management.objects.get(user=management_user)

            # Create task with logged-in user as creator and assigner
            task = Task.objects.create(
                name=name,
                description=description,
                status=status,
                project=project,
                module=module,
                created_by=management,
                assigned_by=management,
            )

            # Assign team members (ManyToManyField)
            if assigned_team_ids:
                team_members = Team.objects.filter(id__in=assigned_team_ids)
                task.assigned_to.set(team_members)

            messages.success(request, "Task created successfully!")
            return redirect("all_tasks")

        except Status.DoesNotExist:
            messages.error(request, "Invalid status selected.")
        except Projects.DoesNotExist:
            messages.error(request, "Invalid project selected.")
        except Modules.DoesNotExist:
            messages.error(request, "Invalid module selected.")
        except Management.DoesNotExist:
            messages.error(request, "You are not a registered management user.")
        except Exception as e:
            messages.error(request, f"Error creating task: {str(e)}")

        return redirect("add_tasks")

    # GET request: Send necessary details for form
    statuses = Status.objects.filter(is_active=True)
    projects = Projects.objects.filter(is_active=True)
    modules = Modules.objects.filter(is_active=True)
    teams = Team.objects.all()  # Fetch all team members

    context = {
        "statuses": statuses,
        "projects": projects,
        "modules": modules,
        "teams": teams,  # Send team members to the template
    }

    return render(request, "admins/add_tasks.html", context)


# Team Member Views
@login_required
def team_dashboard(request):
    if request.user.role != "TEAM":
        logout(request)
        messages.error(request, "Access denied. Team privileges required.")
        return redirect("login")

    # Get today's record
    today = timezone.localtime().date()
    today_record = TimeRecord.objects.filter(
        user=request.user, check_in__date=today
    ).first()

    # Get attendance history
    attendance_history = TimeRecord.objects.filter(user=request.user).order_by(
        "-check_in"
    )  # Most recent first

    # Calculate duration for each record
    for record in attendance_history:
        if record.check_out:
            duration = record.check_out - record.check_in
            hours = duration.seconds // 3600
            minutes = (duration.seconds % 3600) // 60
            record.duration = f"{hours:02d}:{minutes:02d}"
        else:
            record.duration = "Active"

    context = {
        "today_record": today_record,
        "attendance_history": attendance_history,
    }
    return render(request, "team/team_dashboard.html", context)


@never_cache
def check_in_out(request):
    if request.method == "POST":
        identifier = request.POST.get("identifier")
        action = request.POST.get("action")
        reason = request.POST.get("reason", "").strip()  # Strip to remove whitespace

        user = User.objects.filter(
            Q(email=identifier) | Q(phone=identifier) | Q(team__team_id=identifier)
        ).first()

        if not user:
            messages.error(request, "User not found")
            return redirect("login")

        today = timezone.now().date()
        current_time = timezone.now()

        # Get today's time record
        time_record = TimeRecord.objects.filter(user=user, check_in__date=today).first()

        # Check if user is trying to check in through the action value
        if request.method == "POST" and request.POST.get("action") == "checkin":
            # Check for pending checkouts before allowing check-in
            pending_checkout = TimeRecord.objects.filter(
                user=user, check_in__lt=timezone.now().date(), check_out__isnull=True
            ).first()

            if pending_checkout:
                # Instead of redirecting right away, add an error message that will be displayed
                messages.error(
                    request,
                    "You have an incomplete check-out from a previous day. Please submit a request before checking in.",
                )
                # We'll add a special parameter to indicate this error
                return redirect(f"{reverse('login')}?pending_checkout=true")

            # Always require reason for check-in
            if not reason:
                messages.error(request, "Please provide a reason for check-in")
                return redirect("login")

            TimeRecord.objects.create(
                user=user, check_in=current_time, late_reason=reason
            )
            messages.success(request, "Successfully checked in")

        elif action == "checkout":
            if not time_record:
                messages.error(request, "Must check in first")
                return redirect("login")

            # Check for open personal breaks
            open_break = PersonalBreak.objects.filter(
                time_record=time_record, check_out__isnull=False, check_in__isnull=True
            ).first()

            if open_break:
                messages.error(
                    request, "Must complete personal break before checking out"
                )
                return redirect("login")

            # Get the team instance for the current user
            try:
                team = Team.objects.get(user=time_record.user)

                # Check if at least one worklog exists for current date
                has_worklog = WorkLog.objects.filter(
                    team_member=team, start_time__date=timezone.now().date()
                ).exists()

                if not has_worklog:
                    messages.error(
                        request, "Please add at least one work log before checking out"
                    )
                    return redirect("login")

            except Team.DoesNotExist:
                messages.error(request, "Team member profile not found")
                return redirect("login")

            # No reason required for checkout
            time_record.check_out = current_time
            time_record.save()
            messages.success(request, "Successfully checked out")

        elif action in ["break_out", "break_in"]:
            if not time_record:
                messages.error(request, "Must check in first")
                return redirect("login")

            # Check if already checked out for the day
            if time_record.check_out:
                messages.error(
                    request, "Cannot take personal breaks after checking out"
                )
                return redirect("login")

            if action == "break_out":
                # Check if already on break
                existing_break = PersonalBreak.objects.filter(
                    time_record=time_record,
                    check_out__isnull=False,
                    check_in__isnull=True,
                ).first()

                if existing_break:
                    messages.error(request, "Already on break")
                    return redirect("login")

                # Require reason for personal break out
                if not reason:
                    messages.error(
                        request, "Please provide a reason for personal break"
                    )
                    return redirect("login")

                PersonalBreak.objects.create(
                    time_record=time_record, check_out=current_time, reason=reason
                )
                messages.success(request, "Personal break started")

            else:  # break_in
                # Find open break
                open_break = PersonalBreak.objects.filter(
                    time_record=time_record,
                    check_out__isnull=False,
                    check_in__isnull=True,
                ).first()

                if not open_break:
                    messages.error(request, "No active break found")
                    return redirect("login")

                # No reason required for personal break in
                open_break.check_in = current_time
                open_break.save()
                messages.success(request, "Personal break ended")

        return redirect("login")

    return redirect("login")


@login_required
def view_schedule(request):
    """View for employees to see their work schedule"""
    if request.user.role != "TEAM":
        return redirect("management_dashboard")

    schedule = (
        request.user.work_schedules.first()
        or WorkSchedule.objects.filter(is_default=True).first()
    )
    upcoming_holidays = Holiday.objects.filter(
        date__gte=timezone.now().date()
    ).order_by("date")[:5]

    context = {
        "schedule": schedule,
        "upcoming_holidays": upcoming_holidays,
    }

    return render(request, "employee_management/view_schedule.html", context)


@login_required
def team_all_tasks(request):
    user_email = request.user
    user_obj = User.objects.filter(email=user_email).first()
    team_member = Team.objects.get(user=user_obj)
    tasks = (
        Task.objects.filter(assigned_to=team_member)
        .exclude(status__name="completed")
        .values(
            "id",
            "name",
            "description",
            "module__name",
            "project__name",
            "status__name",
            "assigned_by__user__name",
            "created_on",
        )
    )
    context = {"data": tasks}
    return render(request, "team/tasks.html", context)


@login_required
def team_view_all_task(request):
    if request.user.role != "TEAM":
        return redirect("management_dashboard")
    data = TeamTask.objects.filter(is_active=True)
    context = {"data": data}
    return render(request, "team/tasks.html", context)


@login_required
def team_view_add_task(request):
    if request.method == "POST":
        try:
            # Get form data
            name = request.POST.get("name")
            description = request.POST.get("description")
            project_id = request.POST.get("project")
            module_id = request.POST.get("module")
            status_id = request.POST.get("status")
            manager_id = request.POST.get("manager")

            # Create the task
            TeamTask.objects.create(
                name=name,
                description=description,
                project_id=project_id,
                module_id=module_id,
                status_id=status_id,
                manager_id=manager_id,  # This should be a User UUID
                created_by=Team.objects.get(user=request.user),
            )

            messages.success(request, "Task created successfully!")
            return redirect("team_view_all_task")

        except Exception as e:
            messages.error(request, f"Error creating task: {str(e)}")
            return redirect("team_view_add_task")

    # For GET request
    statuses = Status.objects.filter(is_active=True)
    projects = Projects.objects.filter(is_active=True)
    managers = Manager.objects.filter(is_active=True)

    context = {
        "statuses": statuses,
        "projects": projects,
        "managers": managers,
    }
    return render(request, "team/add-task.html", context)


# Helper Functions
def calculate_late_arrivals(attendance_queryset):
    """Calculate late arrivals based on work schedules"""
    late_arrivals = 0
    for record in attendance_queryset:
        schedule = (
            record.user.work_schedules.first()
            or WorkSchedule.objects.filter(is_default=True).first()
        )
        if schedule and record.check_in.time() > schedule.start_time:
            late_arrivals += 1
    return late_arrivals


@login_required
def add_task_response(request, task_id):
    if request.user.role != "TEAM":
        messages.error(request, "Only team members can update tasks")
        return redirect("login")

    task = get_object_or_404(Task, id=task_id)
    team_member = Team.objects.get(user=request.user)

    # Verify team member is assigned to this task
    if team_member not in task.assigned_to.all():
        messages.error(request, "You are not assigned to this task")
        return redirect("team_all_tasks")

    if request.method == "POST":
        status = get_object_or_404(Status, id=request.POST.get("status"))
        description = request.POST.get("description")

        TaskResponse.objects.create(
            task=task, team_member=team_member, status=status, description=description
        )

        messages.success(request, "Task update submitted successfully")
        return redirect("team_all_tasks")

    statuses = Status.objects.filter(is_active=True)
    context = {
        "task": task,
        "statuses": statuses,
        "previous_responses": TaskResponse.objects.filter(
            task=task, team_member=team_member
        ).order_by("-created_at"),
    }
    return render(request, "team/add_task_response.html", context)


@login_required
def task_details(request, task_id):
    if request.user.role != "MANAGEMENT":
        messages.error(request, "Access denied. Management privileges required.")
        return redirect("login")

    task = get_object_or_404(Task, id=task_id)
    task_responses = TaskResponse.objects.filter(task=task).order_by("-created_at")

    context = {
        "task": task,
        "task_responses": task_responses,
    }
    return render(request, "admins/task_details.html", context)


@login_required
def edit_task(request, task_id):
    if request.user.role != "MANAGEMENT":
        messages.error(request, "Access denied. Management privileges required.")
        return redirect("login")

    task = get_object_or_404(Task, id=task_id)

    if request.method == "POST":
        # Get form data
        name = request.POST.get("name")
        description = request.POST.get("description")
        status = get_object_or_404(Status, id=request.POST.get("status"))
        project = get_object_or_404(Projects, id=request.POST.get("project"))
        module = get_object_or_404(Modules, id=request.POST.get("module"))
        assigned_to = request.POST.getlist("assigned_to")

        # Update task
        task.name = name
        task.description = description
        task.status = status
        task.project = project
        task.module = module
        task.save()

        # Update assigned team members
        task.assigned_to.clear()
        for team_id in assigned_to:
            team = get_object_or_404(Team, id=team_id)
            task.assigned_to.add(team)

        messages.success(request, "Task updated successfully")
        return redirect("task_details", task_id=task.id)

    context = {
        "task": task,
        "statuses": Status.objects.filter(is_active=True),
        "projects": Projects.objects.filter(is_active=True),
        "modules": Modules.objects.filter(is_active=True),
        "teams": Team.objects.filter(user__is_active=True),
    }
    return render(request, "admins/edit_task.html", context)


@login_required
def messages_inbox(request):
    # Get all message threads where user is a recipient
    threads = (
        MessageThread.objects.filter(messages__recipients=request.user)
        .distinct()
        .order_by("-updated_at")
    )

    # Add has_unread property to threads
    for thread in threads:
        thread.has_unread = MessageRecipient.objects.filter(
            message__thread=thread, recipient=request.user, is_read=False
        ).exists()

    context = {
        "threads": threads,
    }
    return render(request, "messaging/inbox.html", context)


@login_required
def sent_messages(request):
    # Get all threads where user is the sender of any message
    threads = (
        MessageThread.objects.filter(messages__sender=request.user)
        .distinct()
        .order_by("-updated_at")
    )

    # Add recipient info to threads
    for thread in threads:
        last_message = thread.messages.latest("created_at")
        thread.recipient_count = last_message.recipients.count()
        thread.recipient_list = last_message.recipients.all()[
            :3
        ]  # Get first 3 recipients
        thread.has_more_recipients = last_message.recipients.count() > 3
        thread.last_message = last_message

        # Check if any replies
        thread.has_replies = thread.messages.exclude(sender=request.user).exists()

    context = {
        "threads": threads,
    }
    return render(request, "messaging/sent.html", context)


@login_required
def compose_message(request):
    if request.user.role != "MANAGEMENT":
        messages.error(request, "You don't have permission to access this page")
        return redirect("messages_inbox")

    if request.method == "POST":
        subject = request.POST.get("subject")
        content = request.POST.get("content")
        message_type = request.POST.get("message_type")

        if not subject or not content:
            messages.error(request, "Please fill in all required fields")
            return redirect("compose_message")

        # Create message thread
        thread = MessageThread.objects.create(subject=subject)

        # Create the message
        message = Message.objects.create(
            thread=thread,
            sender=request.user,
            content=content,
            message_type=message_type,
        )

        # Handle different recipient types
        if message_type == "ALL":
            # Send to all team members
            recipients = User.objects.filter(role="TEAM")
        else:  # INDIVIDUAL
            recipient_ids = request.POST.getlist("individual_recipients")
            if not recipient_ids:
                messages.error(request, "Please select at least one recipient")
                return redirect("compose_message")
            recipients = User.objects.filter(id__in=recipient_ids, role="TEAM")

        if not recipients.exists():
            messages.error(request, "No valid recipients found")
            return redirect("compose_message")

        # Create message recipients and notifications
        for recipient in recipients:
            MessageRecipient.objects.create(message=message, recipient=recipient)

            Notification.objects.create(
                recipient=recipient,
                type="MESSAGE",
                title=f"New Message: {subject}",
                message=f"You have a new message from {request.user.name}",
            )

        messages.success(request, "Message sent successfully")
        return redirect("messages_inbox")

    context = {
        "users": User.objects.filter(role="TEAM").order_by("name"),
    }
    return render(request, "messaging/compose.html", context)


@login_required
def view_thread(request, thread_id):
    thread = get_object_or_404(MessageThread, id=thread_id)

    # Verify user has access to this thread
    if (
        not Message.objects.filter(thread=thread)
        .filter(Q(sender=request.user) | Q(recipients=request.user))
        .exists()
    ):
        messages.error(request, "You don't have permission to view this conversation")
        return redirect("messages_inbox")

    # Mark messages as read
    MessageRecipient.objects.filter(
        message__thread=thread, recipient=request.user, is_read=False
    ).update(is_read=True, read_at=timezone.now())

    if request.method == "POST":
        content = request.POST.get("content")
        if not content:
            messages.error(request, "Reply cannot be empty")
            return redirect("view_thread", thread_id=thread_id)

        # Create reply
        message = Message.objects.create(
            thread=thread,
            sender=request.user,
            content=content,
            message_type="INDIVIDUAL",
        )

        # Add all participants as recipients (except sender)
        participants = set()
        for msg in thread.messages.all():
            participants.add(msg.sender)
            participants.update(msg.recipients.all())

        for recipient in participants:
            if recipient != request.user:
                MessageRecipient.objects.create(message=message, recipient=recipient)

                Notification.objects.create(
                    recipient=recipient,
                    type="MESSAGE",
                    title=f"New Reply: {thread.subject}",
                    message=f"{request.user.name} replied to the conversation",
                )

        return redirect("view_thread", thread_id=thread_id)

    context = {
        "thread": thread,
    }
    return render(request, "messaging/view_message.html", context)


@login_required
def notifications_list(request):
    notifications = Notification.objects.filter(recipient=request.user)
    unread_count = notifications.filter(is_read=False).count()

    context = {"notifications": notifications, "unread_count": unread_count}
    return render(request, "notifications/all.html", context)


@login_required
def mark_notification_read(request, notification_id):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request method"})

    notification = get_object_or_404(
        Notification, id=notification_id, recipient=request.user
    )
    notification.is_read = True
    notification.save()
    return JsonResponse({"status": "success"})


def get_notification_context(request):
    """Helper function to get notification context for the dropdown"""
    notifications = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).order_by("-created_at")[:5]

    return {"notifications": notifications, "unread_count": notifications.count()}


@login_required
def get_modules_for_project(request):
    project_id = request.GET.get("project_id")
    if not project_id:
        return JsonResponse({"modules": []})

    modules = Modules.objects.filter(project_id=project_id, is_active=True).values(
        "id", "name"
    )

    return JsonResponse({"modules": list(modules)})


@login_required
def add_work_log(request):
    if request.user.role != "TEAM":
        messages.error(request, "Access denied. Team member privileges required.")
        return redirect("login")

    try:
        team_member = Team.objects.get(user=request.user)

        if request.method == "POST":
            task_id = request.POST.get("task")
            log_date = request.POST.get("log_date")
            start_time = request.POST.get("start_time")
            endtime = request.POST.get("end_time")
            status_id = request.POST.get("status")
            description = request.POST.get("description")

            # Combine date and time
            start_datetime = datetime.strptime(
                f"{log_date} {start_time}", "%Y-%m-%d %H:%M"
            )
            end_datetime = datetime.strptime(f"{log_date} {endtime}", "%Y-%m-%d %H:%M")

            # Validate end time is after start time
            if end_datetime <= start_datetime:
                messages.error(request, "End time must be after start time")
                return redirect("add_work_log")

            WorkLog.objects.create(
                task_id=task_id,
                team_member=team_member,
                start_time=start_datetime,
                end_time=end_datetime,
                status_id=status_id,
                description=description,
            )

            messages.success(request, "Work log added successfully!")
            return redirect("view_work_logs")

        # For GET request
        tasks = TeamTask.objects.filter(
            created_by=team_member, is_active=True
        ).select_related("project", "module")

        statuses = Status.objects.filter(is_active=True)

        context = {
            "tasks": tasks,
            "statuses": statuses,
        }
        return render(request, "team/add_work_log.html", context)

    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect("team_dashboard")


@login_required
def view_work_logs(request):
    if request.user.role != "TEAM":
        messages.error(request, "Access denied. Team member privileges required.")
        return redirect("login")

    try:
        team_member = Team.objects.get(user=request.user)
        work_logs = (
            WorkLog.objects.filter(team_member=team_member)
            .select_related("task", "task__project", "task__module", "status")
            .order_by("-created_at")
        )

        context = {
            "work_logs": work_logs,
        }
        return render(request, "team/view_work_logs.html", context)

    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect("team_dashboard")


@login_required
def add_team_task(request):
    if request.user.role not in ["TEAM", "MANAGEMENT"]:
        messages.error(request, "Access denied.")
        return redirect("login")

    try:
        # Get the creator based on role
        if request.user.role == "TEAM":
            creator = Team.objects.get(user=request.user)
        else:  # MANAGEMENT
            creator = request.user

        if request.method == "POST":
            project_id = request.POST.get("project")
            module_id = request.POST.get("module")
            name = request.POST.get("name")
            description = request.POST.get("description")
            manager_id = request.POST.get("manager")
            status_id = request.POST.get("status")

            # Create the task
            task = TeamTask.objects.create(
                project_id=project_id,
                module_id=module_id,
                name=name,
                description=description,
                manager_id=manager_id,
                status_id=status_id,
                created_by=creator if request.user.role == "TEAM" else None,
                created_by_management=(
                    creator if request.user.role == "MANAGEMENT" else None
                ),
            )

            messages.success(request, "Task created successfully!")

            # Redirect based on role
            if request.user.role == "TEAM":
                return redirect("view_team_tasks")
            else:
                return redirect("management_view_all_tasks")

        # Get data for form
        projects = Projects.objects.filter(is_active=True)
        modules = Modules.objects.filter(is_active=True)
        managers = User.objects.filter(role="MANAGEMENT", is_active=True)
        statuses = Status.objects.filter(is_active=True)

        context = {
            "projects": projects,
            "modules": modules,
            "managers": managers,
            "statuses": statuses,
            "is_management": request.user.role == "MANAGEMENT",
        }

        return render(request, "team/add_team_task.html", context)

    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect(
            "team_dashboard" if request.user.role == "TEAM" else "management_dashboard"
        )


@login_required
def employee_details(request, team_id):
    if request.user.role != "MANAGEMENT":
        messages.error(request, "Access denied. Management privileges required.")
        return redirect("login")

    try:
        team = get_object_or_404(Team, team_id=team_id)
        employee = team.user

        # Get date range
        current_date = timezone.now()
        start_date_str = request.GET.get("start_date")
        end_date_str = request.GET.get("end_date")

        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                start_date = current_date.replace(day=1).date()
                end_date = current_date.date()
        else:
            month_offset = int(request.GET.get("month_offset", 0))
            target_date = current_date - timedelta(days=month_offset * 30)
            start_date = target_date.replace(day=1).date()
            _, last_day = monthrange(target_date.year, target_date.month)
            end_date = target_date.replace(day=last_day).date()

        # Get holidays
        holidays = set(
            Holiday.objects.filter(
                date__range=[start_date, end_date], is_working_day=False
            ).values_list("date", flat=True)
        )

        # Calculate working days
        working_dates = []
        current = start_date
        while current <= end_date:
            # Skip Sundays and holidays
            if current.weekday() != 6 and current not in holidays:
                # For Saturdays, check if it's even week
                if current.weekday() == 5:
                    week_number = (current.day - 1) // 7 + 1
                    if week_number % 2 == 0:  # Even week Saturday
                        working_dates.append(current)
                else:
                    working_dates.append(current)  # Monday to Friday
            current += timedelta(days=1)

        total_working_days = len(working_dates)
        working_dates_set = set(working_dates)

        # Get attendance records
        attendance_records = []
        total_hours_missed = timedelta()
        present_dates = set()
        late_days = 0
        half_days = 0
        full_days = present_count = 0

        monthly_attendance = (
            TimeRecord.objects.filter(
                user=employee, check_in__date__range=[start_date, end_date]
            )
            .select_related("user")
            .prefetch_related("breaks")
        )

        for record in monthly_attendance:
            date = record.check_in.date()
            if date in working_dates_set:
                duration = timedelta()
                if record.check_out:
                    duration = record.check_out - record.check_in

                    # Subtract break durations
                    breaks = record.breaks.filter(check_in__isnull=False)
                    break_duration = sum(
                        (b.check_in - b.check_out).total_seconds() for b in breaks
                    )
                    duration = duration - timedelta(seconds=break_duration)

                    # Calculate attendance status
                    hours_worked = duration.total_seconds() / 3600
                    status = "Present"

                    if hours_worked < 3.5:
                        status = "Absent"
                    elif hours_worked < 6:
                        status = "Half Day"
                        half_days += 1
                    else:
                        full_days += 1
                        present_count += 1

                    if (
                        record.check_in.time()
                        > datetime.strptime("10:15", "%H:%M").time()
                    ):
                        late_days += 1

                    attendance_records.append(
                        {
                            "date": date,
                            "day": date.strftime("%A"),
                            "check_in": record.check_in.strftime("%I:%M %p"),
                            "check_out": record.check_out.strftime("%I:%M %p"),
                            "duration": f"{int(hours_worked):02d}:{int((hours_worked % 1) * 60):02d}",
                            "status": status,
                            "is_late": record.check_in.time()
                            > datetime.strptime("10:15", "%H:%M").time(),
                        }
                    )
                else:
                    # Handle case where check_out is None (still checked in)
                    attendance_records.append(
                        {
                            "date": date,
                            "day": date.strftime("%A"),
                            "check_in": record.check_in.strftime("%I:%M %p"),
                            "check_out": "-",
                            "duration": "In Progress",
                            "status": "Present",
                            "is_late": record.check_in.time()
                            > datetime.strptime("10:15", "%H:%M").time(),
                        }
                    )
                present_dates.add(date)

        # Calculate absent dates (exclude future dates)
        today = timezone.now().date()
        absent_dates = [
            {"date": date, "day": date.strftime("%A"), "reason": "No attendance record"}
            for date in working_dates_set - present_dates
            if date <= today  # Only include dates up to today
        ]

        # Recalculate attendance summary excluding future dates
        total_working_days = len([date for date in working_dates if date <= today])

        # Calculate weekend dates
        weekend_dates = {"sundays": [], "saturdays": []}

        current = start_date
        while current <= end_date:
            if current.weekday() == 6:  # Sunday
                weekend_dates["sundays"].append(current)
            elif current.weekday() == 5:  # Saturday
                week_number = (current.day - 1) // 7 + 1
                weekend_dates["saturdays"].append(
                    {
                        "date": current,
                        "is_working": week_number % 2
                        == 0,  # Even week Saturdays are working
                    }
                )
            current += timedelta(days=1)

        context = {
            "employee": employee,
            "team_details": {"team_id": team.team_id, "department": team.department},
            "attendance_summary": {
                "total_working_days": total_working_days,
                "present_days": present_count,
                "absent_days": len(absent_dates),
                "half_days": half_days,
                "late_days": late_days,
                "attendance_percentage": (
                    round((present_count / total_working_days * 100), 2)
                    if total_working_days > 0
                    else 0
                ),
            },
            "attendance_records": attendance_records,
            "absent_dates": sorted(absent_dates, key=lambda x: x["date"]),
            "date_range": {
                "start": start_date,
                "end": end_date,
                "current_period": f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}",
            },
            "weekend_dates": weekend_dates,
        }

        return render(request, "admins/employee_details.html", context)

    except Exception as e:
        messages.error(request, f"Error loading employee details: {str(e)}")
        return redirect("all_employees")


@login_required
def team_profile(request):
    """View for team members to see their profile and summary information"""
    if request.user.role != "TEAM":
        messages.error(request, "Access denied. Team member privileges required.")
        return redirect("login")

    try:
        # Get team profile
        team = get_object_or_404(Team, user=request.user)

        # Get today's attendance record
        today = timezone.now().date()
        today_record = TimeRecord.objects.filter(
            user=request.user, check_in__date=today
        ).first()

        # Check if on break
        on_break = False
        current_break = None
        if today_record:
            current_break = PersonalBreak.objects.filter(
                time_record=today_record, check_out__isnull=False, check_in__isnull=True
            ).first()
            on_break = current_break is not None

        # Calculate today's working hours if checked in
        working_hours = None
        total_break_time = timedelta()

        if today_record:
            end_time = today_record.check_out or timezone.now()
            total_duration = end_time - today_record.check_in

            # Calculate total break time
            breaks = PersonalBreak.objects.filter(
                time_record=today_record, check_in__isnull=False
            )

            for break_record in breaks:
                break_duration = break_record.check_in - break_record.check_out
                total_break_time += break_duration

            # Get current break time if on break
            if current_break:
                current_break_duration = timezone.now() - current_break.check_out
                total_break_time += current_break_duration

            # Calculate working hours
            working_duration = total_duration - total_break_time
            hours = working_duration.seconds // 3600
            minutes = (working_duration.seconds % 3600) // 60
            working_hours = f"{hours:02d}:{minutes:02d}"

        # Get recent time records (last 3 days excluding today)
        recent_records = TimeRecord.objects.filter(
            user=request.user, check_in__date__lt=today
        ).order_by("-check_in")[:3]

        # Format the time records for display
        time_records = []
        for record in recent_records:
            if record.check_out:
                duration = record.check_out - record.check_in
                hours = duration.seconds // 3600
                minutes = (duration.seconds % 3600) // 60

                # Get breaks for this record
                breaks = PersonalBreak.objects.filter(
                    time_record=record, check_in__isnull=False
                )
                total_break_mins = sum(
                    ((break_obj.check_in - break_obj.check_out).seconds // 60)
                    for break_obj in breaks
                )

                time_records.append(
                    {
                        "date": record.check_in.date(),
                        "check_in": record.check_in.strftime("%I:%M %p"),
                        "check_out": record.check_out.strftime("%I:%M %p"),
                        "duration": f"{hours}h {minutes}m",
                        "break_count": breaks.count(),
                        "break_duration": f"{total_break_mins}m",
                    }
                )

        # Get current tasks
        tasks = (
            Task.objects.filter(assigned_to=team, is_active=True)
            .exclude(status__name__in=["completed", "Completed"])
            .select_related("project", "module", "status")
            .order_by("created_on")[:4]
        )  # Get 4 most recent tasks

        # Get work schedule
        schedule = (
            WorkSchedule.objects.filter(employees=request.user).first()
            or WorkSchedule.objects.filter(is_default=True).first()
        )

        next_holiday = (
            Holiday.objects.filter(date__gte=timezone.now().date())
            .order_by("date")
            .first()
        )

        # Get weekly hours
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        weekly_records = TimeRecord.objects.filter(
            user=request.user,
            check_in__date__range=[week_start, week_end],
            check_out__isnull=False,
        )

        total_weekly_hours = 0
        for record in weekly_records:
            duration = record.check_out - record.check_in
            # Subtract breaks
            record_breaks = PersonalBreak.objects.filter(
                time_record=record, check_in__isnull=False
            )
            break_time = sum((b.check_in - b.check_out).seconds for b in record_breaks)
            total_weekly_hours += (duration.seconds - break_time) / 3600

        # Target hours (assuming 8 hours per day, 5 days a week)
        target_hours = 40

        context = {
            "team": team,
            "today_record": today_record,
            "on_break": on_break,
            "working_hours": working_hours,
            "time_records": time_records,
            "tasks": tasks,
            "schedule": schedule,
            "next_holiday": next_holiday,
            "weekly_hours": {
                "logged": round(total_weekly_hours, 1),
                "target": target_hours,
                "percentage": (
                    min(round((total_weekly_hours / target_hours) * 100), 100)
                    if target_hours > 0
                    else 0
                ),
            },
        }

        return render(request, "team/team_profile.html", context)

    except Exception as e:
        messages.error(request, f"Error loading profile: {str(e)}")
        return redirect("team_dashboard")


@login_required
def update_profile(request):
    if request.method == "POST":
        team_member = request.user.team_member

        # Handle profile image upload
        if "profile_image" in request.FILES:
            team_member.profile_image = request.FILES["profile_image"]

        # Update phone number
        if "phone" in request.POST:
            team_member.phone = request.POST["phone"]

        team_member.save()
        messages.success(request, "Profile updated successfully!")

    return redirect("team_profile")


@login_required
def team_tickets(request):
    """View for team members to see their tickets"""
    if request.user.role != "TEAM":
        messages.error(request, "Access denied. Team member privileges required.")
        return redirect("login")

    try:
        team = get_object_or_404(Team, user=request.user)

        # Get all tickets created by this team member
        tickets = Ticket.objects.filter(created_by=team).select_related(
            "category", "priority", "assigned_to"
        )

        # Filter tickets by status if provided
        status_filter = request.GET.get("status")
        if status_filter:
            tickets = tickets.filter(status=status_filter)

        # Get ticket categories and priorities for the filter options
        categories = TicketCategory.objects.filter(is_active=True)
        priorities = TicketPriority.objects.all()

        context = {
            "tickets": tickets,
            "categories": categories,
            "priorities": priorities,
            "status_choices": Ticket.TICKET_STATUS_CHOICES,
            "current_filter": status_filter,
        }

        return render(request, "team/tickets.html", context)

    except Exception as e:
        messages.error(request, f"Error loading tickets: {str(e)}")
        return redirect("team_dashboard")


@login_required
def create_ticket(request):
    """View for team members to create a new ticket"""
    if request.user.role != "TEAM":
        messages.error(request, "Access denied. Team member privileges required.")
        return redirect("login")

    try:
        team = get_object_or_404(Team, user=request.user)

        if request.method == "POST":
            subject = request.POST.get("subject")
            description = request.POST.get("description")
            category_id = request.POST.get("category")
            priority_id = request.POST.get("priority")

            if not all([subject, description, category_id, priority_id]):
                messages.error(request, "All fields are required.")
                return redirect("create_ticket")

            # Create the ticket
            ticket = Ticket.objects.create(
                created_by=team,
                category_id=category_id,
                priority_id=priority_id,
                subject=subject,
                description=description,
                status="NEW",
            )

            # Handle file attachments
            for file in request.FILES.getlist("attachments"):
                TicketAttachment.objects.create(
                    ticket=ticket,
                    uploaded_by=request.user,
                    file=file,
                    filename=file.name,
                    file_size=file.size,
                    content_type=file.content_type,
                )

            messages.success(
                request, f"Ticket {ticket.ticket_id} has been created successfully."
            )
            return redirect("ticket_detail", ticket_id=ticket.id)

        # GET request - show the form
        categories = TicketCategory.objects.filter(is_active=True)
        priorities = TicketPriority.objects.all().order_by("order")

        context = {
            "categories": categories,
            "priorities": priorities,
        }

        return render(request, "team/create_ticket.html", context)

    except Exception as e:
        messages.error(request, f"Error creating ticket: {str(e)}")
        return redirect("team_tickets")


@login_required
def ticket_detail(request, ticket_id):
    """View for viewing a ticket and its history"""
    try:
        # Determine which related model to check based on user role
        if request.user.role == "TEAM":
            team = get_object_or_404(Team, user=request.user)
            ticket = get_object_or_404(
                Ticket.objects.select_related("category", "priority", "assigned_to"),
                id=ticket_id,
                created_by=team,
            )
        elif request.user.role == "MANAGEMENT":
            management = get_object_or_404(Management, user=request.user)
            ticket = get_object_or_404(
                Ticket.objects.select_related("category", "priority", "created_by"),
                id=ticket_id,
            )
        else:
            messages.error(request, "Access denied.")
            return redirect("login")

        # Get comments - for management, show all comments. For team, hide private comments
        if request.user.role == "MANAGEMENT":
            comments = ticket.comments.select_related("user").all()
        else:
            comments = ticket.comments.select_related("user").filter(is_private=False)

        # Get attachments
        attachments = ticket.attachments.select_related("uploaded_by").all()

        # Add comment if POST request
        if request.method == "POST":
            comment_text = request.POST.get("comment")
            is_private = request.POST.get("is_private", "") == "on"

            if comment_text:
                TicketComment.objects.create(
                    ticket=ticket,
                    user=request.user,
                    comment=comment_text,
                    is_private=is_private,
                )

                messages.success(request, "Comment added successfully.")
                return redirect("ticket_detail", ticket_id=ticket.id)

        # For management, include the ability to update status
        if request.user.role == "MANAGEMENT" and request.method == "POST":
            new_status = request.POST.get("status")
            old_status = ticket.status

            ticket.status = new_status

            # If resolved or closed, add resolution timestamp
            if new_status in ["RESOLVED", "CLOSED"] and old_status not in [
                "RESOLVED",
                "CLOSED",
            ]:
                ticket.resolved_at = timezone.now()

                # Add resolution notes if provided
                resolution_notes = request.POST.get("resolution_notes", "")
                if resolution_notes:
                    ticket.resolution_notes = resolution_notes

            ticket.save()

            # Add a system comment about the status change
            TicketComment.objects.create(
                ticket=ticket,
                user=request.user,
                comment=f"Status changed from {get_status_display(old_status)} to {get_status_display(new_status)}",
                is_private=True,
            )

            messages.success(
                request, f"Ticket status updated to {get_status_display(new_status)}"
            )

        context = {
            "ticket": ticket,
            "comments": comments,
            "attachments": attachments,
            "status_choices": Ticket.TICKET_STATUS_CHOICES,
            "is_management": request.user.role == "MANAGEMENT",
        }

        return render(request, "team/ticket_detail.html", context)

    except Exception as e:
        messages.error(request, f"Error viewing ticket: {str(e)}")
        if request.user.role == "TEAM":
            return redirect("team_tickets")
        else:
            return redirect("management_dashboard")


@login_required
def team_submit_request(request):
    # Get pending checkout if any
    pending_checkout = None

    if request.user.role == "TEAM":
        # Check for incomplete checkout
        try:
            pending_checkout = TimeRecord.objects.filter(
                user=request.user, check_out__isnull=True
            ).latest("check_in")
        except TimeRecord.DoesNotExist:
            pending_checkout = None

    if request.method == "POST":
        # Extract form data
        date = request.POST.get("date")
        check_in = "check_in" in request.POST
        check_in_time = request.POST.get("check_in_time") if check_in else None
        check_out = "check_out" in request.POST
        check_out_time = request.POST.get("check_out_time") if check_out else None
        explanation = request.POST.get("explanation")

        # Validate input
        if not (check_in or check_out):
            messages.error(
                request, "You must select at least one: Check-in or Check-out"
            )
            return render(
                request,
                "employees/submit_request.html",
                {
                    "pending_checkout": pending_checkout,
                    "today": timezone.now(),
                },
            )

        if (check_in and not check_in_time) or (check_out and not check_out_time):
            messages.error(request, "Please provide time for all selected options")
            return render(
                request,
                "employees/submit_request.html",
                {
                    "pending_checkout": pending_checkout,
                    "today": timezone.now(),
                },
            )

        # Create request
        team_request = TeamRequest(
            user=request.user,
            date=date,
            check_in=check_in,
            check_in_time=check_in_time,
            check_out=check_out,
            check_out_time=check_out_time,
            explanation=explanation,
        )
        team_request.save()

        # Notify management
        managers = User.objects.filter(role="MANAGEMENT")
        for manager in managers:
            Notification.objects.create(
                recipient=manager,
                type="SYSTEM",
                title="New Team Request",
                message=f"{request.user.name} has submitted a new request for {date}",
            )

        messages.success(request, "Your request has been submitted successfully")
        return redirect("team_view_requests")

    # GET request
    return render(
        request,
        "employees/submit_request.html",
        {
            "pending_checkout": pending_checkout,
            "today": timezone.now(),
        },
    )


@login_required
def team_view_requests(request):
    """View for team members to see their submitted requests"""
    # Ensure user is a team member
    if request.user.role != "TEAM":
        messages.error(request, "You don't have permission to access this page")
        return redirect("management_dashboard")

    # Get all requests for this user
    user_requests = TeamRequest.objects.filter(user=request.user).order_by(
        "-created_at"
    )

    return render(
        request,
        "employees/team_view_requests.html",
        {
            "user_requests": user_requests,
        },
    )
