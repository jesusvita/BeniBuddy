from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.urls import reverse
from .models import Expense
from .forms import ExpenseForm
import calendar
from datetime import date, timedelta
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Sum


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
    }
    return render(request, 'expenses/expense_tracker.html', context)