document.addEventListener('DOMContentLoaded', () => {
  const calendarDays = document.querySelectorAll('.calendar-day');
  const expenseModal = document.getElementById('expense-modal');
  const formModal = document.getElementById('expense-form-modal');
  const expenseForm = document.getElementById('expense-form');
  const expenseDateInput = document.getElementById('expense-date-selected');
  const editingExpenseIdInput = document.getElementById('editing-expense-id'); // Corrected variable name

  // Access data passed from Django template
  const expensesByDayData = window.expensesByDayData || {};
  const categoryFieldId = window.formFieldIds ? window.formFieldIds.category : 'id_category'; // Default if not passed
  const nameFieldId = window.formFieldIds ? window.formFieldIds.name : 'id_name';
  const amountFieldId = window.formFieldIds ? window.formFieldIds.amount : 'id_amount';

  calendarDays.forEach(dayCell => {
    dayCell.addEventListener('click', () => {
      const dateStr = dayCell.dataset.date;
      expenseDateInput.value = dateStr;

      // Ensure dateStr is valid before creating Date object
      let dayNum = 'invalid';
      if (dateStr && dateStr.includes('-')) {
          try {
            dayNum = new Date(dateStr + 'T00:00:00').getDate().toString(); // Add time part for robust parsing
          } catch (e) {
            console.error("Invalid date string for Date object:", dateStr, e);
          }
      } else {
          console.error("Invalid or missing date string:", dateStr);
      }
      
      const expenses = expensesByDayData[dayNum] || [];

      renderExpenseList(expenses);
      expenseModal.classList.remove('hidden');
    });
  });

  function renderExpenseList(expenses) {
    const list = document.getElementById('modal-expense-list');
  list.innerHTML = ''; // clear previous

  if (!expenses.length) {
    document.getElementById('modal-no-expenses-message').classList.remove('hidden');
    return;
  } else {
    document.getElementById('modal-no-expenses-message').classList.add('hidden');
  }

  expenses.forEach(expense => {
    const li = document.createElement('li');
    li.className = 'flex justify-between items-center py-1';

    const span = document.createElement('span');
    span.className = 'truncate';
    span.title = `${expense.name}: $${expense.amount.toFixed(2)}`;
    span.textContent = `${expense.name} - $${expense.amount.toFixed(2)}`;

    const btnContainer = document.createElement('div');
    btnContainer.className = 'flex gap-2 ml-2';

    const editBtn = document.createElement('button');
    editBtn.className = 'edit-expense-btn text-primary hover:text-red-700';
    editBtn.dataset.expenseId = expense.id;
    editBtn.ariaLabel = `Edit ${expense.name} expense`;
    editBtn.textContent = '✎';
    // attach your edit handler here, e.g. editBtn.addEventListener('click', ...);

    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'delete-expense-btn text-red-600 hover:text-red-800';
    deleteBtn.dataset.expenseId = expense.id;
    deleteBtn.ariaLabel = `Delete ${expense.name} expense`;
    deleteBtn.textContent = '🗑';
    // attach your delete handler here

    btnContainer.appendChild(editBtn);
    btnContainer.appendChild(deleteBtn);

    li.appendChild(span);
    li.appendChild(btnContainer);

    list.appendChild(li);
  });
  }

  function openEditForm(li) {
    formModal.classList.remove('hidden');
    // For select, you might need to find the option with matching value if dataset.category is the display name
    document.getElementById(categoryFieldId).value = li.dataset.categoryValue || li.dataset.category; // Prefer value if available
    document.getElementById(nameFieldId).value = li.dataset.name;
    document.getElementById(amountFieldId).value = li.dataset.amount;
    if (editingExpenseIdInput) editingExpenseIdInput.value = li.dataset.expenseId;
  }

  document.getElementById('add-expense-button').addEventListener('click', () => {
    formModal.classList.remove('hidden');
    expenseForm.reset();
    if (editingExpenseIdInput) editingExpenseIdInput.value = '';
  });

  document.getElementById('close-modal-button').addEventListener('click', () => {
    expenseModal.classList.add('hidden');
  });

  document.getElementById('close-expense-form-modal').addEventListener('click', () => {
    formModal.classList.add('hidden');
  });

  // Handle re-opening modal on form errors
  if (window.djangoFormErrors && window.submittedExpenseDate) {
    expenseDateInput.value = window.submittedExpenseDate;
    formModal.classList.remove('hidden');
  }
});
