from django.shortcuts import render, redirect, get_object_or_404
from .forms import *
from django.contrib.auth.models import Group, User
from django.contrib.auth import authenticate, login, logout
from .models import *
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .decorators import allowed_users
from django.core.mail import send_mail
from django.conf import settings
from django.utils.dateparse import parse_date
from datetime import datetime
import csv
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.utils import get_column_letter

import openpyxl
import pandas as pd

# Create your views here.

def loginPage(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if user.groups.filter(name='manager').exists():
                return redirect('manager')
            elif user.groups.filter(name='supervisor').exists():
                return redirect('supervisor')
            elif user.groups.filter(name='client').exists():
                return redirect('client')
            else:
                messages.info(request, 'Username or Password is incorrect')

        else:
            messages.info(request, 'Username or Password is incorrect')
    return render(request, 'login.html')

@login_required(login_url='login')
def logoutUser(request):
    logout(request)
    return redirect('login') 


def registerPage(request):   
    form = CreateUserForm()
    
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')

            group = Group.objects.get(name='client')
            user.groups.add(group)
            Member.objects.create(
                user=user,
                )

            messages.success(request,'Account was created for ' + username )

            return redirect('register')

    context = {'form':form}
    return render(request, 'register.html', context)


@login_required(login_url='login')
@allowed_users(allowed_roles=['client'])
def clientDashboard(request):
    return render(request, 'client.html')


@login_required(login_url='login')
@allowed_users(allowed_roles=['supervisor'])
def supervisorDashboard(request):
    return render(request, 'supervisor.html')


@login_required(login_url='login')
@allowed_users(allowed_roles=['manager'])
def managerDashboard(request):
    return render(request, 'manager.html')



def send_mail_to_user_and_supervisors(user_email, subject, message):
    # Get the email addresses of users in the 'supervisor' group
    supervisor_group = Group.objects.get(name='supervisor')
    supervisor_emails = User.objects.filter(groups=supervisor_group).values_list('email', flat=True)

    # Combine the user_email and supervisor emails into a single recipient list
    recipient_list = [user_email] + list(supervisor_emails)  # Only send to the user and supervisors

    # Send the email
    send_mail(
        subject,            # Subject of the email
        message,            # Body of the email
        settings.EMAIL_HOST_USER,  # From email (should be your configured email)
        recipient_list,     # List of recipient emails
        fail_silently=False  # If True, suppress exceptions (set to False for debugging)
    )




@login_required(login_url='login')
@allowed_users(allowed_roles=['client'])
def create_ptw_form(request):
    if request.method == 'POST':
        form = PTWSubmissionForm(request.POST)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.user = request.user
            submission.save()

            # Construct the email message
            subject = "New PTW Form Submission"
            message = f"""
            A user has submitted a PTW form.

            Details of the form:
            -------------------
            User: {request.user.get_full_name()} ({request.user.email})
            Location: {submission.location}
            Date Started: {submission.start_datetime}
            Description: {submission.work_description}

            You can view the form details in the admin panel.
            """

            # Send the email to the signed-in user and supervisors
            send_mail_to_user_and_supervisors(submission.user.email, subject, message)

            return redirect('form_list')
    else:
        form = PTWSubmissionForm()
    return render(request, 'ptw.html', {'form':form})



@login_required(login_url='login')
@allowed_users(allowed_roles=['client','supervisor','manager'])
def form_list(request):
    submissions = PTWForm.objects.none()

    if request.user.is_authenticated:
        # Check user roles and filter submissions accordingly
        if request.user.groups.filter(name='client').exists():
            # Clients can only see their own submissions
            submissions = PTWForm.objects.filter(user=request.user)
        elif request.user.groups.filter(name='manager').exists():
            submissions = PTWForm.objects.filter(status__in=['awaiting_supervisor', 'awaiting_manager', 'approved'])

        elif request.user.groups.filter(name='supervisor').exists():
            submissions = PTWForm.objects.all()

    return render(request, 'form_list.html', {
        'submissions': submissions,
    })


@login_required(login_url='login')
@allowed_users(allowed_roles=['client'])
def edit_form(request, pk):
    submission = get_object_or_404(PTWForm, pk=pk)
    if request.method == 'POST':
        form = PTWSubmissionForm(request.POST, instance=submission)
        if form.is_valid():
            form.save()
            return redirect('form_list')  # Redirect to the list view after updating
    else:
        form = PTWSubmissionForm(instance=submission)
    return render(request, 'edit_form.html', {'form': form, 'submission': submission})


@login_required(login_url='login')
@allowed_users(allowed_roles=['client'])
def delete_form(request, pk):
    # Fetch the FormSubmission object or return a 404 if it doesn't exist
    submission = get_object_or_404(PTWForm, pk=pk)
    
    # Delete the submission
    submission.delete()

    # Redirect to the form list page after deletion
    return redirect('form_list')


@login_required(login_url='login')

def view_form(request, pk):
    # Get the form submission by its primary key (pk)
    submission = get_object_or_404(PTWForm, pk=pk)

    # Pass the form submission to the template for rendering
    return render(request, 'view_form.html', {'submission': submission})



@login_required(login_url='login')
@allowed_users(allowed_roles=['supervisor'])
def approve_supervisor(request, pk):
    submission = get_object_or_404(PTWForm, pk=pk)
    if submission.status == 'pending':
        submission.status = 'awaiting_supervisor'  # Change status to 'awaiting supervisor approval'
        submission.save()
    return redirect('form_list')


@login_required(login_url='login')
@allowed_users(allowed_roles=['supervisor'])
def disapprove_supervisor(request, pk):
    submission = get_object_or_404(PTWForm, pk=pk)
    
    if request.user.groups.filter(name='supervisor').exists():  # Check if the user is a supervisor
        submission.status = 'disapproved'  # Change the status to 'disapproved'
        submission.save()  # Save the updated status
    return redirect('form_list')

# View to approve a submission (Manager Approval)
@login_required(login_url='login')
@allowed_users(allowed_roles=['manager'])
def approve_manager(request, pk):
    submission = get_object_or_404(PTWForm, pk=pk)
    if submission.status == 'awaiting_supervisor':
        submission.status = 'approved'
        submission.save()

        subject = "PTW Form Approved"
        message = f"Dear {submission.user.get_full_name()},\n\nYour PTW form located at '{submission.location}' has been approved by the manager.\n\nThank you."

        send_mail_to_user_and_supervisors(submission.user.email, subject, message)
    return redirect('form_list')


@login_required(login_url='login')
@allowed_users(allowed_roles=['manager'])
def disapprove_manager(request, pk):
    submission = get_object_or_404(PTWForm, pk=pk)

    if request.user.groups.filter(name='manager').exists(): 
        submission.status = 'disapproved' 
        submission.save()  
    return redirect('form_list')



def create_nhis_form(request):
    if request.method == 'POST':
        form = NHISSubmissionForm(request.POST)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.user = request.user
            submission.save()

            subject = "New PTW Form Submission"
            message = f"""
            A user has submitted a NHIS form.

            Details of the form:
            -------------------
            User: {request.user.get_full_name()} ({request.user.email})
            Location: {submission.location}
            Date Started: {submission.date}
            Observation: {submission.observation}

            You can view the form details in the admin panel.
            """

            # Send the email to the signed-in user and supervisors
            send_mail_to_user_and_supervisors(submission.user.email, subject, message)
            return redirect('nhis_list')
    else:
        form = NHISSubmissionForm()
    return render(request, 'nhis.html', {'form':form})


def nhis_list(request):
    submissions = NHISForm.objects.none()

    if request.user.is_authenticated:
        # Check user roles and filter submissions accordingly
        if request.user.groups.filter(name='client').exists():
            # Clients can only see their own submissions
            submissions = NHISForm.objects.filter(user=request.user)
        elif request.user.groups.filter(name='manager').exists():
            submissions = NHISForm.objects.filter(status__in=['awaiting_supervisor', 'awaiting_manager', 'closed'])

        elif request.user.groups.filter(name='supervisor').exists():
            submissions = NHISForm.objects.all()

    return render(request, 'nhis_list.html', {
        'submissions': submissions,
    })


@login_required(login_url='login')
@allowed_users(allowed_roles=['supervisor'])
def approve_nhis_supervisor(request, pk):
    submission = get_object_or_404(NHISForm, pk=pk)
    if submission.status == 'open':
        submission.status = 'awaiting_supervisor'  # Change status to 'awaiting supervisor approval'
        submission.save()
    return redirect('nhis_list')


@login_required(login_url='login')
@allowed_users(allowed_roles=['supervisor'])
def disapprove_nhis_supervisor(request, pk):
    submission = get_object_or_404(NHISForm, pk=pk)
    
    if request.user.groups.filter(name='supervisor').exists():  # Check if the user is a supervisor
        submission.status = 'denied'  # Change the status to 'disapproved'
        submission.save()  # Save the updated status
    return redirect('nhis_list')

# View to approve a submission (Manager Approval)
@login_required(login_url='login')
@allowed_users(allowed_roles=['manager'])
def approve_nhis_manager(request, pk):
    submission = get_object_or_404(NHISForm, pk=pk)
    if submission.status == 'awaiting_supervisor':
        submission.status = 'closed' 
        submission.save()

        subject = "NHIS Form Approved"
        message = f"Dear {submission.user.get_full_name()},\n\nYour NHIS form located at '{submission.location}', \n\n Dated  '{submission.date}' has been approved by the manager.\n\nThank you."

        send_mail_to_user_and_supervisors(submission.user.email, subject, message)
    return redirect('nhis_list')


@login_required(login_url='login')
@allowed_users(allowed_roles=['manager'])
def disapprove_nhis_manager(request, pk):
    submission = get_object_or_404(NHISForm, pk=pk)

    if request.user.groups.filter(name='manager').exists(): 
        submission.status = 'denied' 
        submission.save()  
    return redirect('nhis_list')




@login_required(login_url='login')
@allowed_users(allowed_roles=['client'])
def edit_nhis_form(request, pk):
    submission = get_object_or_404(NHISForm, pk=pk)
    if request.method == 'POST':
        form = NHISSubmissionForm(request.POST, instance=submission)
        if form.is_valid():
            form.save()
            return redirect('nhis_list')  # Redirect to the list view after updating
    else:
        form = NHISSubmissionForm(instance=submission)
    return render(request, 'edit_nhis_form.html', {'form': form, 'submission': submission})


@login_required(login_url='login')
@allowed_users(allowed_roles=['client'])
def delete_nhis_form(request, pk):
    # Fetch the FormSubmission object or return a 404 if it doesn't exist
    submission = get_object_or_404(NHISForm, pk=pk)
    
    # Delete the submission
    submission.delete()

    # Redirect to the form list page after deletion
    return redirect('nhis_list')


@login_required(login_url='login')
def view_nhis_form(request, pk):
    # Get the form submission by its primary key (pk)
    submission = get_object_or_404(NHISForm, pk=pk)

    # Pass the form submission to the template for rendering
    return render(request, 'view_nhis_form.html', {'submission': submission})




@login_required
@allowed_users(allowed_roles=['admin', 'supervisor'])
def form_report(request):
    start_date = None
    end_date = None

    # Get the date range parameters from the request
    if 'startDate' in request.GET and 'endDate' in request.GET:
        start_date = request.GET.get('startDate')
        end_date = request.GET.get('endDate')

    # Parse the dates if they exist
    start_date = parse_date(start_date) if start_date else None
    end_date = parse_date(end_date) if end_date else None

    print(f"Start date: {start_date}, End date: {end_date}")

    # Initialize report_data to None initially
    report_data = []

    pie_chart_data_form_type = {'NHIS': 0, 'PTW': 0}
    pie_chart_data_status = {
        'approved': 0,
        'pending': 0,
        'disapproved': 0,
        'awaiting_manager': 0,
        'awaiting_supervisor': 0,
        'open': 0,
        'closed': 0,
        'denied': 0,
    }

    # If a valid date range is provided, filter and fetch the data
    if start_date or end_date:
        # Fetch NHIS form submissions within the date range
        nhis_submissions = NHISForm.objects.all()
        if start_date and end_date:
            nhis_submissions = nhis_submissions.filter(date_submitted__range=[start_date, end_date])
        elif start_date:
            nhis_submissions = nhis_submissions.filter(date_submitted__gte=start_date)
        elif end_date:
            nhis_submissions = nhis_submissions.filter(date_submitted__lte=end_date)

        # Fetch PTW form submissions within the date range
        ptw_submissions = PTWForm.objects.all()
        if start_date and end_date:
            ptw_submissions = ptw_submissions.filter(date_submitted__range=[start_date, end_date])
        elif start_date:
            ptw_submissions = ptw_submissions.filter(date_submitted__gte=start_date)
        elif end_date:
            ptw_submissions = ptw_submissions.filter(date_submitted__lte=end_date)

        # Combine both form submissions into one list
        
        for submission in nhis_submissions:
            report_data.append({
                'form_type': 'NHIS',
                'form_id': submission.id,
                'date_submitted': submission.date_submitted.strftime('%Y-%m-%d'),
                'user': submission.user.get_full_name(),
                'location': submission.location,
                'status': submission.status,
            })

        for submission in ptw_submissions:
            report_data.append({
                'form_type': 'PTW',
                'form_id': submission.id,
                'date_submitted': submission.date_submitted.strftime('%Y-%m-%d'),
                'user': submission.user.get_full_name(),
                'location': submission.location,
                'status': submission.status,
            })

        

        for submission in report_data:
            pie_chart_data_form_type[submission['form_type']] += 1
            pie_chart_data_status[submission['status']] += 1

    else:
        pie_chart_data_form_type = None
        pie_chart_data_status = None

    

    if 'export' in request.GET:
        return export_to_excel(report_data)

    # Return data to template for display
    return render(request, 'report.html', {
        'start_date': start_date,
        'end_date': end_date,
        'total_nhis': len(nhis_submissions) if report_data else 0,
        'total_ptw': len(ptw_submissions) if report_data else 0,
        'report_data': report_data,
        'pie_chart_data_form_type': pie_chart_data_form_type,
        'pie_chart_data_status': pie_chart_data_status,
    })


def export_to_excel(report_data):
    if not report_data:
        print("No data to export!")
        return HttpResponse("No data to export", status=400)
    # Create a workbook and add a sheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Form Report"
    
    # Define the headers for the Excel sheet
    headers = ['Form Type', 'Form ID', 'Date Submitted', 'User', 'Location', 'Status']
    ws.append(headers)

    # Add the report data to the sheet
    for data in report_data:
        ws.append([
            data['form_type'],
            data['form_id'],
            data['date_submitted'],
            data['user'],
            data['location'],
            data['status'],
        ])

    # Set the response for downloading the Excel file
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="form_report_{datetime.now().strftime("%Y%m%d%H%M%S")}.xlsx"'

    # Save the workbook to the response
    wb.save(response)

    return response

