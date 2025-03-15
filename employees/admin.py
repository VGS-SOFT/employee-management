from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import TeamRequest, User, Team, Management, TimeRecord, Holiday, WorkSchedule, PersonalBreak, Status, Projects, Modules, Task, Manager, TeamTask, TaskResponse, MessageThread, Message, MessageRecipient, Notification, WorkLog, Ticket, TicketCategory, TicketPriority, TicketComment, TicketAttachment

class CustomUserAdmin(UserAdmin):
    list_display = ('name', 'email', 'phone', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('name', 'email', 'phone')
    ordering = ('email',)
    
    # Define the fieldsets for add/edit pages
    fieldsets = (
        (None, {'fields': ('email', 'phone', 'password')}),
        ('Personal Info', {'fields': ('name',)}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser')}),
    )
    
    # Define the fields for add page
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('name', 'email', 'phone', 'role', 'password1', 'password2'),
        }),
    )

class TimeRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'check_in', 'check_out', 'late_reason', 'calculate_total_hours', 'calculate_working_hours')
    list_filter = ('check_in', 'check_out')
    search_fields = ('user__email', 'user__phone', 'user__name')
    readonly_fields = ('created_at',)

class PersonalBreakAdmin(admin.ModelAdmin):
    list_display = ('time_record', 'check_out', 'check_in', 'reason', 'calculate_duration')
    list_filter = ('check_out', 'check_in')
    search_fields = ('time_record__user__email', 'time_record__user__phone', 'reason')
    readonly_fields = ('created_at',)

class TeamAdmin(admin.ModelAdmin):
    list_display = ('team_id', 'get_email', 'get_phone', 'department')
    search_fields = ('team_id', 'user__email', 'user__phone', 'department')
    list_filter = ('department',)

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'

    def get_phone(self, obj):
        return obj.user.phone
    get_phone.short_description = 'Phone'

class ManagementAdmin(admin.ModelAdmin):
    list_display = ('management_id', 'get_email', 'get_phone', 'department')
    search_fields = ('management_id', 'user__email', 'user__phone', 'department')
    list_filter = ('department',)

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'

    def get_phone(self, obj):
        return obj.user.phone
    get_phone.short_description = 'Phone'

@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_active')
    search_fields = ('name',)

@admin.register(Projects)
class ProjectsAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'is_active', 'created_by')
    list_filter = ('status', 'is_active')
    search_fields = ('name',)

@admin.register(Modules)
class ModulesAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'status', 'is_active', 'created_by')
    list_filter = ('project', 'status', 'is_active')
    search_fields = ('name', 'project__name')

# @admin.register(Task)
# class TaskAdmin(admin.ModelAdmin):
#     list_display = ('name', 'project', 'module', 'status', 'created_by', 'assigned_by')
#     list_filter = ('project', 'module', 'status', 'is_active')
#     search_fields = ('name', 'project__name', 'module__name')
#     filter_horizontal = ('assigned_to',)

# @admin.register(TaskResponse)
# class TaskResponseAdmin(admin.ModelAdmin):
#     list_display = ('task', 'team_member', 'status', 'created_at')
#     list_filter = ('status', 'created_at')
#     search_fields = ('task__name', 'team_member__user__name', 'description')

# @admin.register(MessageThread)
# class MessageThreadAdmin(admin.ModelAdmin):
#     list_display = ('subject', 'created_at', 'updated_at')
#     search_fields = ('subject',)

# @admin.register(Message)
# class MessageAdmin(admin.ModelAdmin):
#     list_display = ('thread', 'sender', 'message_type', 'created_at')
#     list_filter = ('message_type', 'created_at')
#     search_fields = ('thread__subject', 'sender__name', 'content')

# @admin.register(MessageRecipient)
# class MessageRecipientAdmin(admin.ModelAdmin):
#     list_display = ('message', 'recipient', 'is_read', 'read_at', 'deleted')
#     list_filter = ('is_read', 'deleted')
#     search_fields = ('message__content', 'recipient__name')

# @admin.register(Notification)
# class NotificationAdmin(admin.ModelAdmin):
#     list_display = ('recipient', 'type', 'title', 'is_read', 'created_at')
#     list_filter = ('type', 'is_read', 'created_at')
#     search_fields = ('recipient__name', 'title', 'message')

@admin.register(WorkLog)
class WorkLogAdmin(admin.ModelAdmin):
    list_display = ('task', 'team_member', 'start_time', 'end_time', 'status')
    list_filter = ('status', 'created_at')
    search_fields = ('task__name', 'team_member__user__name', 'description')

# Ticket System Admin
@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_id', 'subject', 'created_by', 'assigned_to', 'category', 'priority', 'status', 'created_at')
    list_filter = ('status', 'priority', 'category', 'created_at')
    search_fields = ('ticket_id', 'subject', 'description', 'created_by__user__name', 'assigned_to__user__name')
    readonly_fields = ('ticket_id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
@admin.register(TicketCategory)
class TicketCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_active', 'icon')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')

@admin.register(TicketPriority)
class TicketPriorityAdmin(admin.ModelAdmin):
    list_display = ('name', 'color_code', 'response_time', 'order')
    list_filter = ('name',)
    search_fields = ('name', 'response_time')
    ordering = ('order',)

@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'user', 'comment_preview', 'is_private', 'created_at')
    list_filter = ('is_private', 'created_at')
    search_fields = ('ticket__ticket_id', 'ticket__subject', 'user__name', 'comment')
    readonly_fields = ('created_at',)
    
    def comment_preview(self, obj):
        # Returns the first 50 characters of the comment
        return obj.comment[:50] + "..." if len(obj.comment) > 50 else obj.comment
    comment_preview.short_description = 'Comment Preview'

@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'filename', 'uploaded_by', 'file_size_display', 'content_type', 'uploaded_at')
    list_filter = ('content_type', 'uploaded_at')
    search_fields = ('ticket__ticket_id', 'ticket__subject', 'filename', 'uploaded_by__name')
    readonly_fields = ('uploaded_at', 'file_size')
    
    def file_size_display(self, obj):
        # Convert bytes to more readable format
        if obj.file_size < 1024:
            return f"{obj.file_size} bytes"
        elif obj.file_size < 1048576:
            return f"{obj.file_size/1024:.1f} KB"
        else:
            return f"{obj.file_size/1048576:.1f} MB"
    file_size_display.short_description = 'File Size'

# Register all models
admin.site.register(User, CustomUserAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(Management, ManagementAdmin)
admin.site.register(TimeRecord, TimeRecordAdmin)
admin.site.register(PersonalBreak, PersonalBreakAdmin)
admin.site.register(Manager)
# admin.site.register(Holiday)
# admin.site.register(WorkSchedule)
admin.site.register(TeamTask)
admin.site.register(TeamRequest)
