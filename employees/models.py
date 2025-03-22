# employee_management/models.py
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.utils import timezone
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils.timezone import now
import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver


class CustomUserManager(BaseUserManager):
    def create_user(self, email=None, phone=None, password=None, **extra_fields):
        if not (email or phone):
            raise ValueError("Either email or phone is required")

        user = self.model(
            email=self.normalize_email(email) if email else None,
            phone=phone,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "ADMIN")
        return self.create_user(email, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Base user model for authentication and role management
    """

    ROLE_CHOICES = (
        ("TEAM", "Team"),
        ("MANAGEMENT", "Management"),
        ("ADMIN", "Admin"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["role"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email or self.phone or str(self.id)


class Team(models.Model):
    """
    Model for team members with specific fields and ID format
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    team_id = models.CharField(max_length=10, unique=True)
    department = models.CharField(max_length=100, blank=True)
    emergency_contact = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.team_id:
            last_team = Team.objects.order_by("-team_id").first()
            if last_team:
                last_num = int(last_team.team_id[3:])
                new_num = last_num + 1
            else:
                new_num = 1
            self.team_id = f"VGS{new_num:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.name}"


class Management(models.Model):
    """
    Model for management members with specific fields and ID format
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    management_id = models.CharField(max_length=10, unique=True)
    department = models.CharField(max_length=100, blank=True)
    emergency_contact = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.management_id:
            last_management = Management.objects.order_by("-management_id").first()
            if last_management:
                last_num = int(last_management.management_id[3:])
                new_num = last_num + 1
            else:
                new_num = 1
            self.management_id = f"VGS{new_num}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.name}"


class TimeRecord(models.Model):
    """
    Model to track daily regular check-in and check-out times
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    check_in = models.DateTimeField()
    check_out = models.DateTimeField(null=True, blank=True)
    late_reason = models.TextField(
        null=True, blank=True, help_text="Required if check-in after 10:15 AM"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-check_in"]

    def save(self, *args, **kwargs):
        if not self.pk:  # Only check on creation
            today = timezone.now().date()
            existing_record = TimeRecord.objects.filter(
                user=self.user, check_in__date=today
            ).exists()

            if existing_record:
                raise ValidationError("Already checked in today")

        super().save(*args, **kwargs)

    def calculate_total_hours(self):
        """Calculate total hours including breaks"""
        if self.check_in and self.check_out:
            duration = self.check_out - self.check_in
            return round(duration.total_seconds() / 3600, 2)
        return None

    def calculate_working_hours(self):
        """Calculate actual working hours excluding breaks"""
        if self.check_in and self.check_out:
            total_duration = (self.check_out - self.check_in).total_seconds()

            # Calculate total break time
            breaks = PersonalBreak.objects.filter(
                time_record=self, check_in__isnull=False, check_out__isnull=False
            )

            total_break_time = sum(
                (break_record.check_in - break_record.check_out).total_seconds()
                for break_record in breaks
            )

            working_duration = total_duration - total_break_time
            return round(working_duration / 3600, 2)
        return None

    def clean(self):
        if self.check_out and self.check_out < self.check_in:
            raise ValidationError("Check-out time cannot be earlier than check-in time")

        # Check if late check-in requires reason
        if self.check_in.time() > timezone.datetime.strptime("10:15", "%H:%M").time():
            if not self.late_reason:
                raise ValidationError("Reason is required for check-in after 10:15 AM")


class PersonalBreak(models.Model):
    """
    Model to track personal breaks during work hours
    """

    time_record = models.ForeignKey(
        TimeRecord, on_delete=models.CASCADE, related_name="breaks"
    )
    check_out = models.DateTimeField()
    check_in = models.DateTimeField(null=True, blank=True)
    reason = models.TextField(help_text="Reason for personal break is required")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-check_out"]

    def clean(self):
        # Ensure there's an active TimeRecord
        if not self.time_record or not self.time_record.check_in:
            raise ValidationError(
                "Must have regular check-in before taking personal break"
            )

        if self.check_in:
            if self.check_in < self.check_out:
                raise ValidationError(
                    "Personal check-in time must be after check-out time"
                )

            # Ensure break is within work day
            if self.check_out < self.time_record.check_in or (
                self.time_record.check_out
                and self.check_in > self.time_record.check_out
            ):
                raise ValidationError(
                    "Personal break must be within regular work hours"
                )

    def calculate_duration(self):
        """Calculate break duration in hours"""
        if self.check_in and self.check_out:
            duration = self.check_in - self.check_out
            return round(duration.total_seconds() / 3600, 2)
        return None


class Holiday(models.Model):
    """
    Model to track holidays and non-working days.
    Useful for time calculation and reporting.
    """

    date = models.DateField(unique=True, help_text="Date of the holiday")

    name = models.CharField(
        max_length=100, help_text="Name or description of the holiday"
    )

    is_working_day = models.BooleanField(
        default=False, help_text="Whether employees are expected to work on this day"
    )

    class Meta:
        ordering = ["date"]
        verbose_name = "Holiday"
        verbose_name_plural = "Holidays"

    def __str__(self):
        return f"{self.name} ({self.date})"


class WorkSchedule(models.Model):
    """
    Model to define working hours for different departments or individuals.
    Useful for tracking overtime and schedule adherence.
    """

    department = models.CharField(
        max_length=100,
        blank=True,
        help_text="Department this schedule applies to (blank for all)",
    )

    start_time = models.TimeField(help_text="Expected start time of the work day")

    end_time = models.TimeField(help_text="Expected end time of the work day")

    is_default = models.BooleanField(
        default=False, help_text="Whether this is the default schedule"
    )

    # Many-to-many relationship with employees
    employees = models.ManyToManyField(
        User,
        blank=True,
        related_name="work_schedules",
        help_text="Employees assigned to this schedule",
    )

    class Meta:
        verbose_name = "Work Schedule"
        verbose_name_plural = "Work Schedules"

    def __str__(self):
        if self.department:
            return f"{self.department} Schedule ({self.start_time}-{self.end_time})"
        return f"Default Schedule ({self.start_time}-{self.end_time})"

    def save(self, *args, **kwargs):
        if self.is_default:
            # Ensure only one default schedule exists
            WorkSchedule.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class Punches(models.Model):
    emp_id = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    punch_in = models.DateTimeField(default=now)
    punch_out = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.emp_id} - {self.punch_in} to {self.punch_out or 'Not yet punched out'}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:  # only when user is created, not updated
        if instance.role == "TEAM":
            Team.objects.create(user=instance)
        elif instance.role == "MANAGEMENT":
            Management.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if instance.role == "TEAM":
        Team.objects.get_or_create(user=instance)
    elif instance.role == "MANAGEMENT":
        Management.objects.get_or_create(user=instance)


class Status(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Statuses"

    def __str__(self):
        return self.name


class Projects(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.ForeignKey(Status, on_delete=models.PROTECT)
    created_by = models.ForeignKey("Management", on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    edited_on = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Projects"

    def __str__(self):
        return self.name


class Modules(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    project = models.ForeignKey(Projects, on_delete=models.CASCADE)
    status = models.ForeignKey(Status, on_delete=models.PROTECT)
    created_by = models.ForeignKey("Management", on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    edited_on = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Modules"

    def __str__(self):
        return f"{self.project.name} - {self.name}"


# Helper function.
def get_default_status():
    """Retrieve the default 'planned' status ID, or return None if not found."""
    try:
        return Status.objects.get(name="planned").id
    except ObjectDoesNotExist:
        return None  # Prevent crashes if 'planned' does not exist


class Task(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    project = models.ForeignKey(Projects, on_delete=models.CASCADE)
    module = models.ForeignKey(Modules, on_delete=models.CASCADE)
    status = models.ForeignKey(
        Status, on_delete=models.PROTECT, default=get_default_status
    )
    assigned_to = models.ManyToManyField("Team", blank=True)
    created_by = models.ForeignKey(
        "Management", on_delete=models.PROTECT, related_name="created_tasks"
    )
    assigned_by = models.ForeignKey(
        "Management", on_delete=models.PROTECT, related_name="tasks_assigned"
    )
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    edited_on = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Tasks"

    def __str__(self):
        return f"{self.project.name} - {self.module.name} - {self.name}"

    def clean(self):
        # Validate module belongs to project
        if self.module and self.project and self.module.project != self.project:
            raise ValidationError(
                {"module": "Selected module does not belong to the selected project"}
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class TaskResponse(models.Model):
    """
    Model to track team member responses/updates to assigned tasks
    """

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="responses")
    team_member = models.ForeignKey(Team, on_delete=models.CASCADE)
    status = models.ForeignKey(Status, on_delete=models.PROTECT)
    description = models.TextField(help_text="Describe your progress or updates")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.task.name} - {self.team_member.user.name} - {self.created_at}"


class MessageThread(models.Model):
    """Model to handle message threads/conversations"""

    subject = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.subject


class Message(models.Model):
    MESSAGE_TYPES = (
        ("INDIVIDUAL", "Individual Message"),
        ("TEAM", "Team Message"),
        ("MANAGEMENT", "Management Message"),
        ("ALL", "Broadcast Message"),
    )

    thread = models.ForeignKey(
        MessageThread, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_messages"
    )
    recipients = models.ManyToManyField(
        User, related_name="received_messages", through="MessageRecipient"
    )
    content = models.TextField()
    message_type = models.CharField(
        max_length=20, choices=MESSAGE_TYPES, default="INDIVIDUAL"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender.name} - {self.thread.subject}"


class MessageRecipient(models.Model):
    """Through model to track message status for each recipient"""

    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        unique_together = ["message", "recipient"]


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ("TASK_UPDATE", "Task Update"),
        ("MESSAGE", "New Message"),
        ("SYSTEM", "System Notification"),
    )

    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    related_task = models.ForeignKey(
        Task, on_delete=models.CASCADE, null=True, blank=True
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.type} - {self.title}"


class Manager(models.Model):
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True, blank=True, null=True)

    def __str__(self):
        return self.name


class TeamTask(models.Model):
    team_task_id = models.CharField(max_length=10, unique=True)
    project = models.ForeignKey(Projects, on_delete=models.CASCADE)
    module = models.ForeignKey(Modules, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField()
    manager = models.ForeignKey(Manager, on_delete=models.CASCADE, related_name='managed_team_tasks')
    status = models.ForeignKey(Status, on_delete=models.CASCADE)
    created_by = models.ForeignKey(Team, on_delete=models.CASCADE, null=True, blank=True)
    created_by_management = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='created_team_tasks')
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.team_task_id:
            # Generate task ID based on creator type
            prefix = 'MGT' if self.created_by_management else 'TM'
            last_task = TeamTask.objects.order_by('-id').first()
            last_id = int(last_task.team_task_id[3:]) if last_task else 0
            self.team_task_id = f"{prefix}{str(last_id + 1).zfill(7)}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.team_task_id} - {self.name}"


class WorkLog(models.Model):
    task = models.ForeignKey(TeamTask, on_delete=models.CASCADE)
    team_member = models.ForeignKey(Team, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.ForeignKey(Status, on_delete=models.CASCADE)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.team_member.user.name} - {self.task.name} - {self.start_time.date()}"

    class Meta:
        ordering = ['-created_at']


class Ticket(models.Model):
    """
    Model for team members to raise support tickets or requests
    """
    TICKET_STATUS_CHOICES = (
        ('NEW', 'New'),
        ('ASSIGNED', 'Assigned'),
        ('IN_PROGRESS', 'In Progress'),
        ('ON_HOLD', 'On Hold'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
        ('REOPENED', 'Reopened'),
    )
    
    ticket_id = models.CharField(max_length=15, unique=True, editable=False)
    created_by = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='created_tickets')
    assigned_to = models.ForeignKey(Management, on_delete=models.SET_NULL, 
                                  null=True, blank=True, related_name='assigned_tickets')
    category = models.ForeignKey('TicketCategory', on_delete=models.PROTECT)
    priority = models.ForeignKey('TicketPriority', on_delete=models.PROTECT)
    subject = models.CharField(max_length=100)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=TICKET_STATUS_CHOICES, default='NEW')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolution_notes = models.TextField(blank=True, null=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            # Generate ticket ID (e.g., TKT-2023-0001)
            year = timezone.now().year
            last_ticket = Ticket.objects.filter(
                ticket_id__startswith=f'TKT-{year}-'
            ).order_by('-ticket_id').first()
            
            if last_ticket:
                # Extract number from last ticket ID and increment
                last_num = int(last_ticket.ticket_id.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.ticket_id = f'TKT-{year}-{new_num:04d}'
        
        # If status is changed to RESOLVED and resolved_at is not set, update it
        if self.status == 'RESOLVED' and not self.resolved_at:
            self.resolved_at = timezone.now()
            
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.ticket_id} - {self.subject}"
    
    class Meta:
        ordering = ['-created_at']


class TicketCategory(models.Model):
    """
    Categories for organizing tickets (e.g., IT Support, HR, Facilities)
    """
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class")
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Ticket Categories"


class TicketPriority(models.Model):
    """
    Priority levels for tickets (e.g., Low, Medium, High, Critical)
    """
    name = models.CharField(max_length=30)
    color_code = models.CharField(max_length=10, help_text="Hex color code (e.g., #FF0000 for red)")
    response_time = models.CharField(max_length=50, blank=True, 
                                   help_text="Expected response time for this priority level")
    order = models.PositiveSmallIntegerField(default=0, help_text="Display order (lower numbers shown first)")
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Ticket Priorities"
        ordering = ['order']


class TicketComment(models.Model):
    """
    Comments and updates on tickets
    """
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_private = models.BooleanField(default=False, 
                                    help_text="Private comments are only visible to management")
    
    def __str__(self):
        return f"Comment on {self.ticket.ticket_id} by {self.user.name}"
    
    class Meta:
        ordering = ['created_at']


class TicketAttachment(models.Model):
    """
    File attachments for tickets
    """
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to='ticket_attachments/%Y/%m/')
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    content_type = models.CharField(max_length=100)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.filename


class TeamRequest(models.Model):
    """
    General-purpose request model for team members to submit any type of request
    """
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_requests')
    date = models.DateField(help_text="Date for this request")
    check_in = models.BooleanField(default=False, help_text="Request for check-in")
    check_in_time = models.TimeField(null=True, blank=True, help_text="Requested check-in time")
    check_out = models.BooleanField(default=False, help_text="Request for check-out")
    check_out_time = models.TimeField(null=True, blank=True, help_text="Requested check-out time")
    explanation = models.TextField(help_text="Please explain your request")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    
    # For approvals
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='reviewed_requests')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        if self.check_in and self.check_out:
            return f"{self.user.name} - {self.date} (Check-in/out)"
        elif self.check_in:
            return f"{self.user.name} - {self.date} (Check-in)"
        elif self.check_out:
            return f"{self.user.name} - {self.date} (Check-out)"
        else:
            return f"{self.user.name} - {self.date} (Other request)"
    
    class Meta:
        ordering = ['-created_at']


class CalendarDay(models.Model):
    """
    Model to manage different types of days in the calendar
    """
    date = models.DateField(unique=True)
    day_type = models.CharField(
        max_length=20,
        choices=[
            ('WORKING', 'Working Day'),
            ('HOLIDAY', 'Holiday'),
            ('FESTIVAL', 'Festival'),
            ('SPECIAL_WORKING', 'Special Working Day'),
            ('HALF_DAY', 'Half Day'),
        ],
        default='WORKING'
    )
    description = models.CharField(max_length=200, blank=True)
    is_saturday_working = models.BooleanField(
        default=False,
        help_text="Whether this Saturday is a working day"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date']
        verbose_name = 'Calendar Day'
        verbose_name_plural = 'Calendar Days'

    def __str__(self):
        return f"{self.date} - {self.get_day_type_display()}"
