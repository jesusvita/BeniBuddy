document.addEventListener('DOMContentLoaded', () => {
    // --- Get Add Tip Modal elements ---
    const modal = document.getElementById('addTipModal');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const cancelModalBtn = document.getElementById('cancelModalBtn');
    const modalTipDateInput = document.getElementById('modalTipDate');
    const addTipForm = document.getElementById('addTipForm');
    // Get new add form inputs (optional, only needed if you want to manipulate them directly)
    // const modalCashMadeInput = document.getElementById('modalCashMade');
    // const modalHoursWorkedInput = document.getElementById('modalHoursWorked');
    // const modalTipNoteInput = document.getElementById('modalTipNote'); // Added note field

    // --- Function to open the Add Tip modal ---
    function openModal(date) {
      if (!modal || !modalTipDateInput || !addTipForm) return;
      modalTipDateInput.value = date;
      modal.classList.remove('hidden');
      addTipForm.reset(); // Resets all fields including new ones
      // Optionally set default focus
      const amountInput = document.getElementById('modalTipAmount');
      if (amountInput) amountInput.focus();
    }

    // --- Function to close the Add Tip modal ---
    function closeModal() {
      if (!modal) return;
      modal.classList.add('hidden');
    }

    // --- Event listeners for closing the Add Tip modal ---
    if (closeModalBtn) {
      closeModalBtn.addEventListener('click', closeModal);
    }
    if (cancelModalBtn) {
      cancelModalBtn.addEventListener('click', closeModal);
    }
    if (modal) {
      modal.addEventListener('click', (event) => {
        if (event.target === modal) {
          closeModal();
        }
      });
    }

    // --- Handle Add Tip Form Submission via AJAX ---
    if (addTipForm) {
      addTipForm.addEventListener('submit', (event) => {
        event.preventDefault();

        // --- START: Default empty numeric inputs to 0 ---
        const amountInput = document.getElementById('modalTipAmount');
        const gratuityInput = document.getElementById('modalTipGratuity');
        const cashMadeInput = document.getElementById('modalCashMade');
        const hoursWorkedInput = document.getElementById('modalHoursWorked');

        // Amount is required, but this handles if it's somehow submitted empty
        if (amountInput && amountInput.value.trim() === '') {
            amountInput.value = '0';
        }
        // Gratuity, Cash, and Hours are often optional, so default them if empty
        if (gratuityInput && gratuityInput.value.trim() === '') {
            gratuityInput.value = '0';
        }
        if (cashMadeInput && cashMadeInput.value.trim() === '') {
            cashMadeInput.value = '0';
        }
        if (hoursWorkedInput && hoursWorkedInput.value.trim() === '') {
            hoursWorkedInput.value = '0';
        }
        // --- END: Default empty numeric inputs to 0 ---

        // FormData automatically picks up all named fields, including the new ones
        const formData = new FormData(addTipForm);
        const url = addTipForm.action;
        const csrfTokenInput = addTipForm.querySelector('input[name="csrfmiddlewaretoken"]');

        if (!csrfTokenInput) {
            console.error('CSRF token input not found!');
            alert('Error: Could not submit form. Security token missing.');
            return;
        }
        const csrfToken = csrfTokenInput.value;

        const submitButton = addTipForm.querySelector('button[type="submit"]');
        if (submitButton) submitButton.disabled = true;

        fetch(url, {
          method: 'POST',
          body: formData, // Includes date, amount, gratuity, cash_made, hours_worked, note
          headers: {
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest',
          },
        })
        .then(response => {
            if (!response.ok) {
                if (response.status === 400) {
                    return response.json().then(data => {
                        // Pass the errors object which might contain validation errors for new fields
                        throw { validationErrors: data.errors };
                    });
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
          if (data.status === 'success') {
            closeModal();
            location.reload(); // Reload to see the updated calendar/totals
          } else {
            alert(data.message || 'An unexpected error occurred.');
            console.error('Server indicated failure:', data);
          }
        })
        .catch(error => {
          console.error('Error submitting form:', error);
          if (error.validationErrors) {
            let errorMessages = "Please correct the following errors:\n";
            // Display validation errors for all fields, including new ones
            for (const field in error.validationErrors) {
              errorMessages += `\n${field}: ${error.validationErrors[field].join(', ')}`;
            }
            alert(errorMessages);
          } else {
            alert('Could not save tip. Please check your connection and try again.');
          }
        })
        .finally(() => {
            if (submitButton) submitButton.disabled = false;
        });
      });
    } else {
        console.error('Add tip form not found.');
    }

    // --- Get Edit Modal Elements ---
    const editModal = document.getElementById('editTipModal');
    const closeEditModalBtn = document.getElementById('closeEditModalBtn'); 
    const openNewShiftModalBtn = document.getElementById('openNewShiftModalBtn');
    const editTipForm = document.getElementById('editTipForm');
    const editModalTipDateInput = document.getElementById('editModalTipDate');
    const editModalTipAmountInput = document.getElementById('editModalTipAmount');
    const editModalTipGratuityInput = document.getElementById('editModalTipGratuity');
    const editModalTipNoteInput = document.getElementById('editModalTipNote');
    const deleteTipLink = document.getElementById('deleteTipLink');
    // START: Get new edit form inputs
    const editModalCashMadeInput = document.getElementById('editModalCashMade');
    const editModalHoursWorkedInput = document.getElementById('editModalHoursWorked');
    // END: Get new edit form inputs

    // --- Get Add New Shift Modal Elements ---
    const addNewShiftModal = document.getElementById('addNewShiftModal');
    const closeAddNewShiftModalBtn = document.getElementById('closeAddNewShiftModalBtn');
    const cancelAddNewShiftBtn = document.getElementById('cancelAddNewShiftBtn');
    const addNewShiftForm = document.getElementById('addNewShiftForm');
    const newShiftAmountInput = document.getElementById('newShiftAmount');
    const newShiftGratuityInput = document.getElementById('newShiftGratuity');
    const newShiftCashMadeInput = document.getElementById('newShiftCashMade');
    const newShiftHoursWorkedInput = document.getElementById('newShiftHoursWorked');
    const newShiftNoteInput = document.getElementById('newShiftNote');
    const saveNewShiftBtn = document.getElementById('saveNewShiftBtn');
    let originalEditTipData = null;
    // --- Function to open the Edit Modal ---
    function openEditModal(tipData) {
        // Ensure all required elements exist, including the new ones
        if (!editModal || !editTipForm || !deleteTipLink || !editModalCashMadeInput || !editModalHoursWorkedInput) {
            console.error("One or more edit modal elements not found!");
            return;
        }

        originalEditTipData = JSON.parse(JSON.stringify(tipData))

        let datePart = tipData.date;
        if (datePart && datePart.includes('T')) { // Handle potential datetime format from JSON
            datePart = datePart.split('T')[0];
        }
        editModalTipDateInput.value = datePart;
        editModalTipAmountInput.value = tipData.amount;
        editModalTipGratuityInput.value = tipData.gratuity != null ? tipData.gratuity : ''; 

        // START: Populate new fields
        // Ensure your backend view sends these fields in the JSON response!
        editModalCashMadeInput.value = tipData.cash_made != null ? tipData.cash_made : '';
        editModalHoursWorkedInput.value = tipData.hours_worked != null ? tipData.hours_worked : '';
        editModalTipNoteInput.value = tipData.note || ''; // Handle null/undefined - moved here for consistency
        // END: Populate new fields

        const editUrl = `/edit-tip/${tipData.id}/`; // Make sure this URL pattern exists in urls.py
        editTipForm.action = editUrl;

        const deleteUrl = `/delete-tip/${tipData.id}/`; // Make sure this URL pattern exists in urls.py
        deleteTipLink.href = deleteUrl; // Set href for the delete link

        editModal.classList.remove('hidden');
        // Optionally set focus
        if (editModalTipAmountInput) editModalTipAmountInput.focus();
    }

    // --- Function to close the Edit Modal ---
    function closeEditModal() {
        if (!editModal) return;
        originalEditTipData = null;
        editModal.classList.add('hidden');
    }

    // --- Add event listeners for closing the Edit Modal ---
    if (closeEditModalBtn) {
        closeEditModalBtn.addEventListener('click', closeEditModal);
    }
    // Note: The old cancelEditModalBtn listener is implicitly removed as the button ID changed or the button itself was repurposed.
    if (editModal) {
        editModal.addEventListener('click', (event) => {
        if (event.target === editModal) {
            closeEditModal();
        }
        });
    }

    // --- Handle "Save Changes" Form Submission via AJAX ---
    if (editTipForm) {
        editTipForm.addEventListener('submit', (event) => {
            event.preventDefault();

            
            // This is for the "Save Changes" button (id="saveChangesEditBtn", type="submit")
            const formData = new FormData(editTipForm);
            const url = editTipForm.action;
            const csrfTokenInput = editTipForm.querySelector('input[name="csrfmiddlewaretoken"]');

            if (!csrfTokenInput) {
                console.error('CSRF token input not found in edit form!');
                alert('Error: Could not submit form. Security token missing.');
                return;
            }
            const csrfToken = csrfTokenInput.value;

            const submitButton = document.getElementById('saveChangesEditBtn');
            if (submitButton) submitButton.disabled = true;

            fetch(url, {
                method: 'POST',
                body: formData, // Includes date, amount, gratuity, cash_made, hours_worked, note
                headers: {
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
                },
            })
            .then(response => {
                if (!response.ok) {
                    if (response.status === 400) {
                        return response.json().then(data => {
                            // Pass the errors object which might contain validation errors for new fields
                            throw { validationErrors: data.errors };
                        });
                    }
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                closeEditModal();
                location.reload(); // Reload to see updated calendar/totals
                } else {
                alert(data.message || 'An unexpected error occurred while saving.');
                console.error('Server indicated failure:', data);
                }
            })
            .catch(error => {
                console.error('Error submitting edit form:', error);
                if (error.validationErrors) {
                let errorMessages = "Please correct the following errors:\n";
                 // Display validation errors for all fields, including new ones
                for (const field in error.validationErrors) {
                    errorMessages += `\n${field}: ${error.validationErrors[field].join(', ')}`;
                }
                alert(errorMessages);
                } else {
                alert('Could not save changes. Please check your connection and try again.');
                }
            })
            .finally(() => {
                if (submitButton) submitButton.disabled = false;
            });
        });
    } else {
        console.error('Edit tip form not found.');
    }

    // --- Function to open the Add New Shift Modal ---
    function openAddNewShiftModal() {
        if (!addNewShiftModal || !editModal) return;
        addNewShiftForm.reset(); // Clear previous entries
        editModal.classList.add('hidden'); // Hide the edit modal
        addNewShiftModal.classList.remove('hidden');
        if(newShiftAmountInput) newShiftAmountInput.focus();
    }

    // --- Function to close the Add New Shift Modal ---
    function closeAddNewShiftModal() {
        if (!addNewShiftModal || !editModal) return;
        addNewShiftModal.classList.add('hidden');
        if (originalEditTipData) { // Only re-show edit modal if it was meant to be open
            editModal.classList.remove('hidden'); 
        }
    }

    // --- Event listener for "New Shift" button in Edit Modal ---
    if (openNewShiftModalBtn) {
        openNewShiftModalBtn.addEventListener('click', () => {
            if (!originalEditTipData) {
                alert('Error: Original tip data not found. Please reopen the edit window.');
                console.error('originalEditTipData is null when trying to open new shift modal.');
                return;
            }
            openAddNewShiftModal();
        });
    }

    // --- Event listeners for closing the Add New Shift Modal ---
    if (closeAddNewShiftModalBtn) {
        closeAddNewShiftModalBtn.addEventListener('click', closeAddNewShiftModal);
    }
    if (cancelAddNewShiftBtn) {
        cancelAddNewShiftBtn.addEventListener('click', closeAddNewShiftModal);
    }
    if (addNewShiftModal) {
        addNewShiftModal.addEventListener('click', (event) => {
            if (event.target === addNewShiftModal) {
                closeAddNewShiftModal();
            }
        });
    }

    // --- Handle "Add New Shift" Form Submission ---
    if (addNewShiftForm) {
        addNewShiftForm.addEventListener('submit', (event) => {
            event.preventDefault();

            if (!originalEditTipData) {
                alert('Error: Original tip data is missing. Cannot save new shift.');
                closeAddNewShiftModal(); // Close this modal
                // editModal might still be hidden, or user might be confused.
                // Consider if editModal should be re-shown or if an error forces a full modal close.
                return;
            }
            
            const csrfTokenInput = editTipForm.querySelector('input[name="csrfmiddlewaretoken"]'); // Get token from main edit form
            if (!csrfTokenInput) {
                console.error('CSRF token input not found in edit form for Add New Shift!');
                alert('Error: Could not submit form. Security token missing.');
                return;
            }
            const csrfToken = csrfTokenInput.value;
            const url = editTipForm.action; // Use the same URL as edit

            const additionalAmount = parseFloat(newShiftAmountInput.value) || 0;
            const additionalGratuity = parseFloat(newShiftGratuityInput.value) || 0;
            const additionalCash = parseFloat(newShiftCashMadeInput.value) || 0;
            const additionalHours = parseFloat(newShiftHoursWorkedInput.value) || 0;
            const additionalNote = newShiftNoteInput.value.trim();
            
            const totalAmount = (parseFloat(originalEditTipData.amount) || 0) + additionalAmount;
            const totalGratuity = (parseFloat(originalEditTipData.gratuity) || 0) + additionalGratuity;
            const totalCash = (parseFloat(originalEditTipData.cash_made) || 0) + additionalCash;
            const totalHours = (parseFloat(originalEditTipData.hours_worked) || 0) + additionalHours;

            let combinedNote = originalEditTipData.note || "";
            if (additionalNote) {
                if (combinedNote) {
                    combinedNote += "\n--- Second Shift ---\n" + additionalNote;
                } else {
                    combinedNote = "--- Second Shift ---\n" + additionalNote;
                }
            }
            const date = originalEditTipData.date.split('T')[0]; 

            const formData = new FormData();
            formData.append('csrfmiddlewaretoken', csrfToken); // Add CSRF token to FormData
            formData.append('date', date);
            formData.append('amount', totalAmount.toFixed(2));
            formData.append('gratuity', totalGratuity.toFixed(2));
            formData.append('cash_made', totalCash.toFixed(2));
            formData.append('hours_worked', totalHours.toFixed(2));
            formData.append('note', combinedNote);

            if(saveNewShiftBtn) saveNewShiftBtn.disabled = true;

            fetch(url, {
                method: 'POST',
                body: formData, // CSRF token is now part of formData
                headers: {
                    // 'X-CSRFToken': csrfToken, // No longer needed here if in FormData
                    'X-Requested-With': 'XMLHttpRequest',
                },
            })
            .then(response => {
                if (!response.ok) {
                    if (response.status === 400) {
                        return response.json().then(data => { throw { validationErrors: data.errors }; });
                    }
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    addNewShiftModal.classList.add('hidden'); // Close new shift modal
                    closeEditModal(); // This closes edit modal and clears originalEditTipData
                    location.reload();
                } else {
                    alert(data.message || 'An unexpected error occurred while saving new shift data.');
                }
            })
            .catch(error => {
                console.error('Error submitting new shift data:', error);
                alert(error.validationErrors ? `Please correct errors: ${JSON.stringify(error.validationErrors)}` : 'Could not save new shift data. Please try again.');
            })
            .finally(() => {
                if(saveNewShiftBtn) saveNewShiftBtn.disabled = false;
            });
        });
    }

    // --- Get Confirm Delete Modal Elements ---
    const confirmDeleteModal = document.getElementById('confirmDeleteModal');
    const closeConfirmDeleteModalBtn = document.getElementById('closeConfirmDeleteModalBtn');
    const cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    const confirmDeleteUrlInput = document.getElementById('confirmDeleteUrl');

    // --- Function to open the Confirm Delete Modal ---
    function openConfirmDeleteModal(url) {
        if (!confirmDeleteModal || !confirmDeleteUrlInput) return;
        confirmDeleteUrlInput.value = url;
        confirmDeleteModal.classList.remove('hidden');
    }

    // --- Function to close the Confirm Delete Modal ---
    function closeConfirmDeleteModal() {
        if (!confirmDeleteModal || !confirmDeleteUrlInput) return;
        confirmDeleteModal.classList.add('hidden');
        confirmDeleteUrlInput.value = '';
    }

    // --- Event listeners for closing the Confirm Delete modal ---
    if (closeConfirmDeleteModalBtn) {
        closeConfirmDeleteModalBtn.addEventListener('click', closeConfirmDeleteModal);
    }
    if (cancelDeleteBtn) {
        cancelDeleteBtn.addEventListener('click', closeConfirmDeleteModal);
    }
    if (confirmDeleteModal) {
        confirmDeleteModal.addEventListener('click', (event) => {
            if (event.target === confirmDeleteModal) {
                closeConfirmDeleteModal();
            }
        });
    }

    // --- Handle Delete Tip Link Click (Opens Confirmation Modal) ---
    if (deleteTipLink) {
        deleteTipLink.addEventListener('click', (event) => {
            event.preventDefault(); // Prevent navigating away
            const url = deleteTipLink.href; // Get URL set by openEditModal
            if (url && url !== '#') { // Check if URL is valid
                openConfirmDeleteModal(url);
            } else {
                console.error('Could not get valid URL from delete link.');
                alert('Error preparing deletion. Please try opening the edit modal again.');
            }
        });
    } else {
        console.error('Delete tip link not found.');
    }

    // --- Handle Actual Deletion from Confirmation Modal ---
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', () => {
            const url = confirmDeleteUrlInput.value;
            // Get CSRF token from the *edit* form as it's likely available
            const csrfTokenInput = editTipForm.querySelector('input[name="csrfmiddlewaretoken"]');

            if (!url) {
                console.error('No delete URL found in confirmation modal.');
                alert('Error: Could not determine which tip to delete.');
                closeConfirmDeleteModal();
                return;
            }
            if (!csrfTokenInput) {
                console.error('CSRF token input not found in edit form for deletion!');
                alert('Error: Could not delete tip. Security token missing.');
                closeConfirmDeleteModal();
                return;
            }
            const csrfToken = csrfTokenInput.value;

            confirmDeleteBtn.disabled = true;
            confirmDeleteBtn.textContent = 'Deleting...';

            fetch(url, {
                method: 'DELETE', // Use DELETE method for deletion
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json' // Expect JSON response
                },
            })
            .then(response => {
                if (!response.ok) {
                    // Try to parse error message from JSON response
                    return response.json().then(errData => {
                        throw new Error(errData.message || `HTTP error! status: ${response.status}`);
                    }).catch(() => {
                        // Fallback if response is not JSON or has no message
                        throw new Error(`HTTP error! status: ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    closeConfirmDeleteModal();
                    closeEditModal(); // Close the edit modal too
                    location.reload(); // Reload to reflect deletion
                } else {
                    console.error('Server indicated deletion failure:', data);
                    alert(data.message || 'An unexpected error occurred while deleting.');
                }
            })
            .catch(error => {
                console.error('Fetch failed completely during delete:', error);
                alert(`Could not delete tip: ${error.message}`);
            })
            .finally(() => {
                 // Ensure button is re-enabled and text reset even if modal closed early
                 confirmDeleteBtn.disabled = false;
                 confirmDeleteBtn.textContent = 'Delete Tip';
                 // Ensure modal is closed if still open
                 if (confirmDeleteModal && !confirmDeleteModal.classList.contains('hidden')) {
                     closeConfirmDeleteModal();
                 }
            });
        });
    } else {
        console.error('Confirm delete button not found.');
    }

    // --- Event Delegation on Calendar Grid (Handles BOTH Add and Edit) ---
    const calendarGrid = document.querySelector('.grid.grid-cols-7.sm\\:grid-cols-7');
    if (calendarGrid) {
        calendarGrid.addEventListener('click', (event) => {
            const addButton = event.target.closest('.add-tip-button');
            const editButton = event.target.closest('.edit-tip-button');

            if (addButton) {
                event.preventDefault(); // Prevent default link navigation
                const date = addButton.dataset.date;
                if (date) {
                    openModal(date); // Open the Add Tip modal
                } else {
                    console.error('Could not find date on add button.');
                }
            } else if (editButton) {
                event.preventDefault(); // Prevent default link navigation
                const tipId = editButton.dataset.tipId;
                if (tipId) {
                    // Fetch tip data for the edit modal
                    fetch(`/edit-tip/${tipId}/`, { // Use the same URL pattern as the form action
                        method: 'GET', // Use GET to fetch data
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest', // Indicate AJAX request
                            'Accept': 'application/json' // Expect JSON response
                        }
                    })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`HTTP error! status: ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(data => {
                        // IMPORTANT: Ensure your view returns JSON like: {'tip': {'id': ..., 'amount': ..., 'cash_made': ..., 'hours_worked': ...}}
                        if (data.tip) {
                            openEditModal(data.tip); // Open the Edit Tip modal with fetched data
                        } else {
                            console.error('Tip data not found in response:', data);
                            alert('Error: Could not load tip details.');
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching tip data:', error);
                        alert('Error: Could not load tip details. Please try again.');
                    });
                } else {
                    console.error('Could not find tip ID on edit button.');
                }
            }
        });
    } else {
        console.error('Calendar grid container not found for event delegation.');
    }

    // --- Get Pay Cycle Modal Elements ---
    const payCycleModal = document.getElementById('editPayCycleModal');
    const openPayCycleBtn = document.getElementById('openPayCycleModalBtn');
    const closePayCycleBtn = document.getElementById('closePayCycleModalBtn');
    const cancelPayCycleBtn = document.getElementById('cancelPayCycleModalBtn');
    const payCycleForm = document.getElementById('editPayCycleForm');
    const payCycleStartDateInput = document.getElementById('payCycleStartDate');

    // --- Function to open the Pay Cycle Modal ---
    function openPayCycleModal() {
        if (!payCycleModal) return;
        payCycleModal.classList.remove('hidden');
        if (payCycleStartDateInput) payCycleStartDateInput.focus();
    }

    // --- Function to close the Pay Cycle Modal ---
    function closePayCycleModal() {
        if (!payCycleModal) return;
        payCycleModal.classList.add('hidden');
    }

    // --- Event Listeners for Pay Cycle Modal ---
    if (openPayCycleBtn) {
        openPayCycleBtn.addEventListener('click', (event) => {
            event.preventDefault(); // Prevent any default button action
            openPayCycleModal();
        });
    } else {
        console.error('Open Pay Cycle Modal button not found.');
    }

    if (closePayCycleBtn) {
        closePayCycleBtn.addEventListener('click', closePayCycleModal);
    }
    if (cancelPayCycleBtn) {
        cancelPayCycleBtn.addEventListener('click', closePayCycleModal);
    }
    if (payCycleModal) {
        payCycleModal.addEventListener('click', (event) => {
            if (event.target === payCycleModal) {
                closePayCycleModal();
            }
        });
    }

    // --- Handle Pay Cycle Form Submission via AJAX ---
    if (payCycleForm) {
        payCycleForm.addEventListener('submit', (event) => {
            event.preventDefault();

            const formData = new FormData(payCycleForm);
            const url = payCycleForm.action;
            const csrfTokenInput = payCycleForm.querySelector('input[name="csrfmiddlewaretoken"]');

            if (!csrfTokenInput) {
                console.error('CSRF token input not found in pay cycle form!');
                alert('Error: Could not submit form. Security token missing.');
                return;
            }
            const csrfToken = csrfTokenInput.value;

            const submitButton = payCycleForm.querySelector('button[type="submit"]');
            if (submitButton) submitButton.disabled = true;

            fetch(url, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json'
                },
            })
            .then(response => {
                if (!response.ok) {
                    if (response.status === 400) {
                        return response.json().then(data => {
                            // Handle potential validation errors from the backend
                            throw { validationErrors: data.errors || {'_error': ['Validation failed. Please check the fields.']} };
                        });
                    }
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    closePayCycleModal();
                    location.reload(); // Reload to update paycheck estimate
                } else {
                    alert(data.message || 'An unexpected error occurred.');
                    console.error('Server indicated failure:', data);
                }
            })
            .catch(error => {
                console.error('Error submitting pay cycle form:', error);
                if (error.validationErrors) {
                    let errorMessages = "Please correct the following errors:\n";
                    for (const field in error.validationErrors) {
                        const prefix = field === '_error' ? '' : `${field}: `; // Handle non-field errors
                        errorMessages += `\n${prefix}${error.validationErrors[field].join(', ')}`;
                    }
                    alert(errorMessages);
                } else {
                    alert('Could not save pay cycle settings. Please check your connection and try again.');
                }
            })
            .finally(() => {
                if (submitButton) submitButton.disabled = false;
            });
        });
    } else {
        console.error('Edit pay cycle form not found.');
    }
    // --- END OF PAY CYCLE MODAL JS ---

    // Close modals on Escape key press
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            if (modal && !modal.classList.contains('hidden')) {
                closeModal();
            }
            if (editModal && !editModal.classList.contains('hidden')) {
                closeEditModal();
            }
            if (confirmDeleteModal && !confirmDeleteModal.classList.contains('hidden')) {
                closeConfirmDeleteModal();
            }
            if (payCycleModal && !payCycleModal.classList.contains('hidden')) {
                closePayCycleModal();
            }
            if (addNewShiftModal && !addNewShiftModal.classList.contains('hidden')) {
                closeAddNewShiftModal(); 
            }
        }
    });

  });