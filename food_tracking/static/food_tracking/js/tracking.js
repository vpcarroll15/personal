/**
 * Food tracking JavaScript functionality
 */

/**
 * Get CSRF token from cookies
 * @param {string} name - Cookie name
 * @returns {string|null} - Cookie value or null
 */
/**
 * Append the page's viewed day (set by the home template as VIEW_DATE) to a
 * write payload, so entries land on the day being viewed rather than today.
 * No-op on pages that don't set VIEW_DATE (e.g. reports).
 * @param {FormData} formData
 */
function appendViewDate(formData) {
    if (typeof VIEW_DATE !== 'undefined' && VIEW_DATE) {
        formData.append('date', VIEW_DATE);
    }
}

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
    appendViewDate(formData);

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
 * POST a FormData payload with CSRF protection. Resolves to parsed JSON on
 * success; otherwise rejects with an Error carrying a specific message (server
 * error text, a 413 "too large" hint, or a network message) so the UI can tell
 * the user what actually went wrong instead of a generic failure.
 * @param {string} url
 * @param {FormData} formData
 * @returns {Promise<Object>}
 */
async function postForm(url, formData) {
    let response;
    try {
        response = await fetch(url, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            body: formData,
        });
    } catch (e) {
        throw new Error('Network error — check your connection.');
    }

    // Read as text first: error responses (413, 500 pages) are often HTML.
    const bodyText = await response.text();
    let data = null;
    try {
        data = JSON.parse(bodyText);
    } catch (e) {
        data = null;
    }

    if (!response.ok) {
        if (data && data.error) {
            throw new Error(data.error);
        }
        if (response.status === 413) {
            throw new Error('The photo is too large for the server to accept.');
        }
        throw new Error('Server error (HTTP ' + response.status + ').');
    }

    if (!data) {
        throw new Error('Unexpected response from the server.');
    }
    return data;
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

// Photos are downscaled to this longest-edge size before upload. Full iPhone
// photos are 2-5 MB (rejected by the server's upload limit) and far larger than
// the model needs; ~1024px keeps the file small and the food clearly legible.
const MAX_IMAGE_DIMENSION = 1024;
const IMAGE_JPEG_QUALITY = 0.8;

/**
 * Downscale/re-encode an image file to a compact JPEG Blob via canvas. Also
 * normalizes formats (e.g. HEIC that slips through) to JPEG, which the backend
 * accepts.
 * @param {File} file
 * @returns {Promise<Blob>}
 */
function resizeImageFile(file) {
    return new Promise((resolve, reject) => {
        const objectUrl = URL.createObjectURL(file);
        const img = new Image();
        img.onload = () => {
            URL.revokeObjectURL(objectUrl);
            let { width, height } = img;
            if (width > MAX_IMAGE_DIMENSION || height > MAX_IMAGE_DIMENSION) {
                if (width >= height) {
                    height = Math.round((height * MAX_IMAGE_DIMENSION) / width);
                    width = MAX_IMAGE_DIMENSION;
                } else {
                    width = Math.round((width * MAX_IMAGE_DIMENSION) / height);
                    height = MAX_IMAGE_DIMENSION;
                }
            }
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            canvas.getContext('2d').drawImage(img, 0, 0, width, height);
            canvas.toBlob(
                blob => (blob ? resolve(blob) : reject(new Error('Could not process the photo.'))),
                'image/jpeg',
                IMAGE_JPEG_QUALITY
            );
        };
        img.onerror = () => {
            URL.revokeObjectURL(objectUrl);
            reject(new Error('Could not read that photo. Try a JPEG or PNG.'));
        };
        img.src = objectUrl;
    });
}

/**
 * Estimate calories from a selected photo (downscaled before upload).
 * @param {HTMLInputElement} input - The file input.
 */
function estimateFromPhoto(input) {
    if (!input.files || input.files.length === 0) {
        return;
    }
    const file = input.files[0];
    input.value = '';

    setEstimateStatus('Processing photo…');
    resizeImageFile(file)
        .then(blob => {
            const formData = new FormData();
            formData.append('image', blob, 'photo.jpg');
            formData.append('note', document.getElementById('text-input').value.trim());
            setEstimateStatus('Estimating from photo…');
            return postForm('/food/estimate/', formData);
        })
        .then(handleEstimateResponse)
        .catch(err => setEstimateStatus('Estimate failed: ' + err.message));
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
        .catch(err => setEstimateStatus('Estimate failed: ' + err.message));
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
        .catch(err => setEstimateStatus('Estimate failed: ' + err.message));
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
    appendViewDate(formData);

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
    const value = prompt('Base rate (resting calories):', current);
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

/**
 * Prompt for and save the daily goal deficit.
 */
function editGoalDeficit() {
    const current = document.getElementById('deficit-value').textContent.trim();
    const value = prompt('Goal deficit (calories/day):', current);
    if (value === null) {
        return;
    }
    const formData = new FormData();
    formData.append('goal_deficit', value);

    postForm('/food/deficit/', formData)
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Error: ' + (data.error || 'Could not update deficit.'));
            }
        })
        .catch(() => alert('Failed to update deficit. Please try again.'));
}

/**
 * Prompt for and save the viewed day's Apple Watch active (Move ring) calories.
 */
function editActiveCalories() {
    const current = document.getElementById('active-value').textContent.trim().replace('~', '');
    const value = prompt('Active Calories:', current);
    if (value === null) {
        return;
    }
    const formData = new FormData();
    formData.append('active_calories', value);
    appendViewDate(formData);

    postForm('/food/active/', formData)
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Error: ' + (data.error || 'Could not update active calories.'));
            }
        })
        .catch(() => alert('Failed to update active calories. Please try again.'));
}
