from services import (send_email, 
    draft_email, 
    reply_to_email,
    smart_reply_to_mail,
    search_emails, 
    draft_email, 
    smart_reply_to_mail,
    search_emails
    # forward_email,
    # reply_to_email,
    # send_email_with_attachment,
    # send_email_with_multiple_attachments,
    # get_email_analysis_by_date,
    # get_email_analysis_by_message_id,
    # manual_analyze_date_range,
    # get_analysis_stats
    )

# print("Starting email test...")
# try:
#     res = send_email("bhanuteja4498@gmail.com", "Hello", "HI from MCP")
#     print("Result:", res)
# except Exception as e:
#     print("Error:", str(e))
#     import traceback
#     traceback.print_exc()
# print("Test completed.")

# Testing draft_email function
def test_draft_email():
    print("Starting draft email test...")
    try:
        res = draft_email("bhanuteja4498@gmail.com", "Draft Subject", "This is a draft email body.")
        print("Draft Result:", res)
    except Exception as e:
        print("Draft Error:", str(e))
        import traceback
        traceback.print_exc()
    print("Draft test completed.")

def test_forward_email():
    print("Starting forward email test...")
    try:
        # Replace 'your_message_id_here' with an actual message ID to test
        res = forward_email("1994ee9167978836","bhanuteja4498@gmail.com", "Forwarding this email.")
        print("Forward Result:", res)
    except Exception as e:
        print("Forward Error:", str(e))
        import traceback
        traceback.print_exc()
    print("Forward test completed.")

def test_reply_to_email():
    print("Starting reply to email test...")
    try:
        # Replace 'your_message_id_here' with an actual message ID to test
        res = reply_to_email("1994ee9167978836", "This is a reply to your email.")
        print("Reply Result:", res)
    except Exception as e:
        print("Reply Error:", str(e))
        import traceback
        traceback.print_exc()
    print("Reply test completed.")

def test_smart_reply_to_mail():
    print("Starting smart reply with AI test...")
    try:
        # Replace 'your_message_id_here' with an actual message ID to test
        res = smart_reply_to_mail("1994f09df431f7f1", "casual reply")
        print("Smart Reply Result:", res)
    except Exception as e:
        print("Smart Reply Error:", str(e))
        import traceback
        traceback.print_exc()
    print("Smart reply test completed.")

test_draft_email()