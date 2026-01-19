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
            alert('Food logged successfully!');
            // Reload page to show updated recent consumption
            location.reload();
        } else {
            alert('Error: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to log food. Please try again.');
    });
}
