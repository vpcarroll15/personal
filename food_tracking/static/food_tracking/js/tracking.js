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
 */
function logFood(foodId) {
    const csrftoken = getCookie('csrftoken');

    // Create form data
    const formData = new FormData();
    formData.append('food_id', foodId);
    formData.append('quantity', '1.0');

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
            const currentCount = parseInt(counter.textContent) || 0;
            const newCount = currentCount + 1;

            counter.textContent = newCount;
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
