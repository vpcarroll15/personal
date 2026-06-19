/**
 * Food tracking JavaScript functionality
 */

/**
 * Get CSRF token from cookies
 * @param {string} name - Cookie name
 * @returns {string|null} - Cookie value or null
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Delete a consumption record via AJAX
 * @param {number} consumptionId - Consumption ID to delete
 */
function deleteConsumption(consumptionId) {
    if (!confirm('Delete this entry?')) {
        return;
    }

    const csrftoken = getCookie('csrftoken');

    // Create form data
    const formData = new FormData();
    formData.append('consumption_id', consumptionId);

    // Send AJAX request
    fetch('/food/delete/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
        },
        body: formData,
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Remove the row from the table
            const row = document.getElementById('consumption-' + consumptionId);
            if (row) {
                row.style.opacity = '0';
                row.style.transition = 'opacity 0.3s ease';
                setTimeout(() => {
                    row.remove();
                    // Reload page to update counter badges
                    location.reload();
                }, 300);
            }
        } else {
            alert('Error: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to delete. Please try again.');
    });
}

/**
 * Log a food consumption via AJAX
 * @param {number} foodId - Food ID to log
 * @param {number} quantity - Quantity to log (default 1.0)
 */
function logFood(foodId, quantity = 1.0) {
    const csrftoken = getCookie('csrftoken');

    // Create form data
    const formData = new FormData();
    formData.append('food_id', foodId);
    formData.append('quantity', quantity.toString());

    // Send AJAX request
    fetch('/food/log/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
        },
        body: formData,
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update the counter
            const counter = document.getElementById('counter-' + foodId);
            const currentCount = parseFloat(counter.textContent) || 0;
            const newCount = currentCount + quantity;

            // Format to remove unnecessary decimals (1.0 -> 1, 1.5 -> 1.5)
            counter.textContent = newCount % 1 === 0 ? newCount.toFixed(0) : newCount.toFixed(1);
            counter.style.display = 'flex';

            // Add pulse animation
            counter.classList.add('pulse');
            setTimeout(() => {
                counter.classList.remove('pulse');
            }, 500);

            // Reload page after a short delay to update recent consumption table
            setTimeout(() => {
                location.reload();
            }, 800);
        } else {
            alert('Error: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to log food. Please try again.');
    });
}

/* ------------------------------------------------------------------ */
/* AI calorie estimation                                              */
/* ------------------------------------------------------------------ */

/**
 * POST a FormData payload with CSRF protection and return the parsed JSON.
 * @param {string} url
 * @param {FormData} formData
 * @returns {Promise<Object>}
 */
function postForm(url, formData) {
    return fetch(url, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        body: formData,
    }).then(response => response.json());
}

/**
 * Show or hide the small status line in the estimate panel.
 * @param {string} message - Empty string hides it.
 */
function setEstimateStatus(message) {
    const el = document.getElementById('estimate-status');
    if (!el) {
        return;
    }
    el.textContent = message;
    el.style.display = message ? 'block' : 'none';
}

/**
 * Populate the confirm/edit card with an estimate and reveal it.
 * @param {Object} estimate - { description, calories, confidence, items }
 */
function showEstimate(estimate) {
    document.getElementById('confirm-description').value = estimate.description || '';
    document.getElementById('confirm-calories').value = estimate.calories || 0;

    const breakdown = document.getElementById('estimate-breakdown');
    let html = '';
    if (estimate.confidence) {
        html += '<div class="confidence">Confidence: ' + estimate.confidence + '</div>';
    }
    if (estimate.items && estimate.items.length > 0) {
        html += '<ul>';
        estimate.items.forEach(item => {
            html += '<li>' + item.name + ': ' + item.calories + ' cal</li>';
        });
        html += '</ul>';
    }
    breakdown.innerHTML = html;

    document.getElementById('estimate-card').style.display = 'block';
}

/**
 * Handle the result of an estimate request (image/text/recipe).
 * @param {Object} data - JSON response from an estimate endpoint.
 */
function handleEstimateResponse(data) {
    setEstimateStatus('');
    if (data.success) {
        showEstimate(data.estimate);
    } else {
        alert('Error: ' + (data.error || 'Could not estimate.'));
    }
}

/**
 * Estimate calories from a selected photo.
 * @param {HTMLInputElement} input - The file input.
 */
function estimateFromPhoto(input) {
    if (!input.files || input.files.length === 0) {
        return;
    }
    const formData = new FormData();
    formData.append('image', input.files[0]);
    formData.append('note', document.getElementById('text-input').value.trim());

    setEstimateStatus('Estimating from photo…');
    postForm('/food/estimate/', formData)
        .then(handleEstimateResponse)
        .catch(() => setEstimateStatus('Failed to estimate. Try again.'));
    input.value = '';
}

/**
 * Estimate calories from the free-text description.
 */
function estimateFromText() {
    const text = document.getElementById('text-input').value.trim();
    if (!text) {
        alert('Describe what you ate first.');
        return;
    }
    const formData = new FormData();
    formData.append('text', text);

    setEstimateStatus('Estimating…');
    postForm('/food/estimate/', formData)
        .then(handleEstimateResponse)
        .catch(() => setEstimateStatus('Failed to estimate. Try again.'));
}

/**
 * Estimate calories for the eaten fraction of a pasted recipe.
 */
function estimateFromRecipe() {
    const recipe = document.getElementById('recipe-input').value.trim();
    const fraction = document.getElementById('fraction-input').value;
    if (!recipe) {
        alert('Paste a recipe first.');
        return;
    }
    const formData = new FormData();
    formData.append('recipe_text', recipe);
    formData.append('fraction', fraction);

    setEstimateStatus('Estimating recipe…');
    postForm('/food/estimate-recipe/', formData)
        .then(handleEstimateResponse)
        .catch(() => setEstimateStatus('Failed to estimate. Try again.'));
}

/**
 * Save the confirmed/edited estimate as a consumption.
 */
function confirmEstimate() {
    const description = document.getElementById('confirm-description').value.trim();
    const calories = document.getElementById('confirm-calories').value;
    if (!description) {
        alert('Add a description.');
        return;
    }
    const formData = new FormData();
    formData.append('description', description);
    formData.append('calories', calories);

    postForm('/food/log-estimate/', formData)
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Error: ' + (data.error || 'Could not log.'));
            }
        })
        .catch(() => alert('Failed to log. Please try again.'));
}

/**
 * Hide the confirm/edit card without saving.
 */
function cancelEstimate() {
    document.getElementById('estimate-card').style.display = 'none';
    setEstimateStatus('');
}

/**
 * Prompt for and save a new daily calorie target.
 */
function editTarget() {
    const current = document.getElementById('target-value').textContent.trim();
    const value = prompt('Daily calorie target:', current);
    if (value === null) {
        return;
    }
    const formData = new FormData();
    formData.append('daily_calorie_target', value);

    postForm('/food/target/', formData)
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Error: ' + (data.error || 'Could not update target.'));
            }
        })
        .catch(() => alert('Failed to update target. Please try again.'));
}
