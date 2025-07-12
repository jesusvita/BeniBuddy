from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.urls import reverse
from .models import Expense
from .forms import ExpenseForm
from decimal import Decimal
import calendar
from datetime import date, timedelta
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Sum
from django.views.decorators.http import require_http_methods, require_POST
from django.http import JsonResponse


@login_required
def expense_tracker_view(request, year=None, month=None):
    """
    Displays a monthly calendar for tracking expenses.

    Allows users to navigate between months, view existing expenses for each day,
    and add new expenses for a selected day via a modal form.

    Args:
        request: HttpRequest object.
        year (int, optional): The year to display. Defaults to the current year.
        month (int, optional): The month to display. Defaults to the current month.

    Returns:
        HttpResponse object rendering the expense tracker page.
    """
    today = timezone.now().date()
    current_year = year if year else today.year
    current_month = month if month else today.month

    # Ensure month and year are valid
    try:
        current_date_for_calendar = date(current_year, current_month, 1)
    except ValueError: # Invalid month/year
        current_year, current_month = today.year, today.month
        current_date_for_calendar = date(current_year, current_month, 1)

    
    cal = calendar.Calendar(firstweekday=6) # 0 is Monday, 6 is Sunday

    month_days = cal.monthdatescalendar(current_year, current_month)

    # Get expenses for the current user for the displayed month
    expenses_for_month = Expense.objects.filter(
        user=request.user,
        expense_date__year=current_year,
        expense_date__month=current_month
    ).order_by('expense_date', 'name')

    expenses_by_day = {d.day: [] for d in cal.itermonthdates(current_year, current_month) if d.month == current_month}
    for expense in expenses_for_month:
        if expense.expense_date.day in expenses_by_day:
            expenses_by_day[expense.expense_date.day].append(expense)

    # Calculate total monthly expenses
    total_monthly_expenses = expenses_for_month.aggregate(total=Sum('amount'))['total'] or 0.00

    # Find the current week and calculate its total expenses
    current_week_total = Decimal('0.00')
    current_week_start_date_str = None

    for week_of_dates in month_days:
        if today in week_of_dates:
            # Found the week containing today
            first_day_of_week = week_of_dates[0] # The first date object in the week list
            current_week_start_date_str = first_day_of_week.strftime("%b %d") # e.g., "Jun 03"

            for day_date_obj in week_of_dates:
                # Only sum expenses for days in the current month
                if day_date_obj.month == current_month:
                    day_s_expenses = expenses_by_day.get(day_date_obj.day, [])
                    for expense in day_s_expenses:
                        current_week_total += expense.amount
            break # Stop searching once the current week is found

    # Calculate total monthly expenses (This calculation remains)
    total_monthly_expenses = expenses_for_month.aggregate(total=Sum('amount'))['total'] or 0.00


    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        expense_date_str = request.POST.get('expense_date_selected')
        if form.is_valid() and expense_date_str:
            try:
                expense_actual_date = date.fromisoformat(expense_date_str)
                expense = form.save(commit=False)
                expense.user = request.user
                expense.expense_date = expense_actual_date
                expense.save()
                # Redirect to the same month view
                return redirect(reverse('expenses:expense_tracker', args=[current_year, current_month]))
            except ValueError:
                form.add_error(None, "Invalid date selected.")
    else:
        form = ExpenseForm()

    prev_month_date = current_date_for_calendar - timedelta(days=1)
    prev_month_year, prev_month_month = prev_month_date.year, prev_month_date.month

    # Calculate the first day of the next month
    days_in_current_month = calendar.monthrange(current_year, current_month)[1]
    next_month_first_day = current_date_for_calendar + timedelta(days=days_in_current_month)
    next_month_year, next_month_month = next_month_first_day.year, next_month_first_day.month

    expenses_by_day_serializable = {}
    for day_num, exp_list in expenses_by_day.items():
        expenses_by_day_serializable[str(day_num)] = [ # Ensure day_num is string for JS keys
            {
                'id': exp.id, # Add expense ID
                'name': exp.name,
                'amount': exp.amount, # DjangoJSONEncoder handles Decimal
                'category': exp.get_category_display() # Get the human-readable category name
            } for exp in exp_list
        ]
    expenses_by_day_json_for_template = json.dumps(expenses_by_day_serializable, cls=DjangoJSONEncoder)


    context = {
        'form': form,
        'month_days': month_days, # list of weeks, each week is list of date objects
        'current_month_name': current_date_for_calendar.strftime("%B"),
        'current_year': current_year,
        'current_month_numeric': current_month,
        'prev_month_year': prev_month_year,
        'prev_month_month': prev_month_month,
        'next_month_year': next_month_year,
        'next_month_month': next_month_month,
        'today_date': today,
        'expenses_by_day': expenses_by_day_serializable,  # dict: {day_num: [expense_obj, ...]}
        'total_monthly_expenses': total_monthly_expenses,
        'expenses_by_day_json_for_template': expenses_by_day_json_for_template,
        'current_week_total': current_week_total,
        'current_week_start_date_str': current_week_start_date_str,
        
    }
    return render(request, 'expenses/expense_tracker.html', context)

@login_required
@require_http_methods(["DELETE"]) # Or require_POST if you prefer POST for deletion
def delete_expense_view(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    if expense.user != request.user:
        return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)
    
    try:
        expense.delete()
        return JsonResponse({'status': 'success', 'message': 'Expense deleted successfully.'})
    except Exception as e:
        # Log the error e
        return JsonResponse({'status': 'error', 'message': 'Could not delete expense.'}, status=500)

@login_required
@require_POST
def edit_expense_view(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id, user=request.user)

    try:
        data = json.loads(request.body)
        name = data.get('name')
        amount = data.get('amount')
        category = data.get('category')

        if not name or not amount or not category:
            return JsonResponse({'status': 'error', 'message': 'Missing fields.'}, status=400)

        expense.name = name
        expense.amount = Decimal(amount)
        expense.category = category
        expense.save()

        return JsonResponse({'status': 'success', 'message': 'Expense updated successfully.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Failed to update expense.'}, status=500)

@require_POST
def expense_delete(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    expense.delete()
    messages.success(request, "Expense deleted successfully.")
    # Redirect back to the expense tracker page with year and month params
    # Adjust these params as needed to keep the user on the current calendar page
    year = request.GET.get('year') or expense.date.year
    month = request.GET.get('month') or expense.date.month
    return redirect('expenses:expense_tracker', year=year, month=month)
