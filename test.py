models_and_fields = [
            (TimeRecord, ['check_in', 'check_out', 'created_at']),
            (PersonalBreak, ['check_in', 'check_out', 'created_at']),
            (WorkLog, ['start_time', 'end_time', 'created_at']),
            (Ticket, ['created_at', 'resolved_at']),
            (TicketComment, ['created_at']),
            (Message, ['created_at']),
            (MessageRecipient, ['read_at']),
            (Notification, ['created_at']),
            (TeamRequest, ['created_at'])
        ]