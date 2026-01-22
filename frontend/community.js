// Community Map Portal - Main JavaScript
// API integration for backend

// API configuration
const API_BASE_URL = '/api';

// State management
let currentPage = 1;
const mapsPerPage = 6;
let filteredMaps = [];
let totalMaps = 0;
let totalPages = 0;
let currentUser = null;
let authToken = null;
let isLoading = false;
let showingMyMaps = false;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    loadAuthState();
    initializeEventListeners();
    loadMaps();
    updateNavigation();
    checkForPendingMapUpload();
});

// Initialize all event listeners
function initializeEventListeners() {
    // Search and filters
    document.getElementById('searchBtn').addEventListener('click', handleSearch);
    document.getElementById('searchInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') handleSearch();
    });

    document.getElementById('terrainFilter').addEventListener('change', applyFilters);
    document.getElementById('sizeFilter').addEventListener('change', applyFilters);
    document.getElementById('playersFilter').addEventListener('change', applyFilters);
    document.getElementById('sortBy').addEventListener('change', applyFilters);
    document.getElementById('resetFiltersBtn').addEventListener('click', resetFilters);

    // Pagination
    document.getElementById('prevPageBtn').addEventListener('click', () => changePage(-1));
    document.getElementById('nextPageBtn').addEventListener('click', () => changePage(1));

    // Navigation
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', handleNavigation);
    });

    // Authentication
    document.getElementById('loginBtn').addEventListener('click', () => showAuthModal('login'));
    document.getElementById('registerBtn').addEventListener('click', () => showAuthModal('register'));
    document.getElementById('closeModalBtn').addEventListener('click', hideAuthModal);
    document.getElementById('authForm').addEventListener('submit', handleAuth);
    document.getElementById('switchAuthModeBtn').addEventListener('click', switchAuthMode);

    // Upload form
    document.getElementById('uploadForm').addEventListener('submit', handleUpload);
    document.getElementById('cancelUploadBtn').addEventListener('click', () => showSection('browse'));

    // Map detail
    document.getElementById('backToGridBtn').addEventListener('click', () => showSection('browse'));

    // Close modal on outside click
    document.getElementById('authModal').addEventListener('click', function(e) {
        if (e.target === this) hideAuthModal();
    });
}

// Load and display maps from API
async function loadMaps() {
    if (isLoading) return;

    isLoading = true;
    showLoading();

    try {
        const response = await fetchMapsFromAPI();
        filteredMaps = response.items;
        totalMaps = response.total;
        totalPages = response.total_pages;

        displayMaps(filteredMaps);
        updateMapCount();
        updatePagination();
    } catch (error) {
        showError('Failed to load maps. Please try again later.');
        console.error('Error loading maps:', error);
    } finally {
        isLoading = false;
    }
}

// Fetch maps from API with filters
async function fetchMapsFromAPI() {
    const searchTerm = document.getElementById('searchInput').value;
    const terrainFilter = document.getElementById('terrainFilter').value;
    const sizeFilter = document.getElementById('sizeFilter').value;
    const playersFilter = document.getElementById('playersFilter').value;
    const sortBy = document.getElementById('sortBy').value;

    // Build query parameters
    const params = new URLSearchParams({
        page: currentPage,
        limit: mapsPerPage
    });

    // Add search term if provided
    if (searchTerm) {
        params.append('search', searchTerm);
    }

    // Add filters if set
    if (terrainFilter) {
        params.append('terrain_type', terrainFilter);
    }

    if (sizeFilter) {
        params.append('size', sizeFilter);
    }

    if (playersFilter) {
        params.append('player_count', playersFilter);
    }

    // Add creator_id filter if showing "My Maps"
    if (showingMyMaps && currentUser) {
        params.append('creator_id', currentUser.id);
    }

    // Map sort UI values to API values
    const sortMapping = {
        'newest': 'created_at',
        'rating': 'rating',
        'downloads': 'downloads',
        'name': 'name'
    };

    params.append('sort_by', sortMapping[sortBy] || 'created_at');
    params.append('sort_order', 'desc');

    const response = await fetch(`${API_BASE_URL}/maps?${params.toString()}`);

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    // Transform API data to match frontend format
    const items = data.items.map(map => ({
        id: map.id,
        name: map.name,
        description: map.description || '',
        terrain: map.terrain_type,
        size: map.size,
        players: map.player_count,
        creator: map.creator?.username || map.author || 'Unknown',
        rating: map.average_rating || 0,
        downloads: map.download_count || 0,
        createdAt: map.created_at,
        tags: [], // Tags not in API yet
        preview: map.preview_image_path ? `/uploads/${map.preview_image_path}` : null
    }));

    return {
        items,
        total: data.total,
        page: data.page,
        page_size: data.page_size,
        total_pages: data.total_pages
    };
}

// Display maps in the grid
function displayMaps(maps) {
    const grid = document.getElementById('mapsGrid');

    if (maps.length === 0) {
        grid.innerHTML = `
            <div class="loading">
                <p>No maps found matching your criteria.</p>
                <button onclick="resetFilters()" class="reset-btn" style="margin-top: 15px;">Reset Filters</button>
            </div>
        `;
        return;
    }

    grid.innerHTML = maps.map(map => createMapCard(map)).join('');

    // Add click handlers to map cards
    document.querySelectorAll('.map-card').forEach(card => {
        card.addEventListener('click', function() {
            const mapId = parseInt(this.dataset.mapId);
            showMapDetail(mapId);
        });
    });
}

// Create a map card HTML element
function createMapCard(map) {
    const sizeLabel = getSizeLabel(map.size);
    const stars = createStarRating(map.rating);

    return `
        <div class="map-card" data-map-id="${map.id}">
            <div class="map-preview">
                ${map.preview ?
                    `<img src="${map.preview}" alt="${map.name}">` :
                    `<span class="map-preview-placeholder">🗺️</span>`
                }
            </div>
            <div class="map-info">
                <h3 class="map-title">${escapeHtml(map.name)}</h3>
                <div class="map-meta">
                    <span class="map-meta-item">🏔️ ${capitalizeFirst(map.terrain)}</span>
                    <span class="map-meta-item">📐 ${sizeLabel}</span>
                    <span class="map-meta-item">👥 ${map.players} Players</span>
                </div>
                <div class="map-stats">
                    <div class="map-rating">
                        <span>⭐ ${stars}</span>
                        <span>${map.rating.toFixed(1)}</span>
                    </div>
                    <div class="map-downloads">
                        <span>📥 ${formatNumber(map.downloads)}</span>
                    </div>
                </div>
                <div class="map-creator">
                    by ${escapeHtml(map.creator)}
                </div>
            </div>
        </div>
    `;
}

// Show map detail view
async function showMapDetail(mapId) {
    try {
        const response = await fetch(`${API_BASE_URL}/maps/${mapId}`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const map = await response.json();

        const detailContent = document.getElementById('mapDetailContent');
        const sizeLabel = getSizeLabel(map.size);
        const stars = createStarRating(map.average_rating || 0);

        detailContent.innerHTML = `
            <div class="map-detail-header">
                <h1 style="color: #ffd700; margin-bottom: 10px;">${escapeHtml(map.name)}</h1>
                <div style="display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 20px;">
                    <span>⭐ ${stars} (${(map.average_rating || 0).toFixed(1)}) - ${map.rating_count || 0} ratings</span>
                    <span>📥 ${formatNumber(map.download_count || 0)} downloads</span>
                    <span>📅 ${new Date(map.created_at).toLocaleDateString()}</span>
                </div>
            </div>

            <div class="map-detail-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 30px;">
                <div>
                    <div class="map-preview" style="height: 400px; margin-bottom: 20px;">
                        ${map.preview_image_path ?
                            `<img src="/uploads/${map.preview_image_path}" alt="${map.name}" style="width: 100%; height: 100%; object-fit: cover;">` :
                            `<span class="map-preview-placeholder" style="font-size: 80px;">🗺️</span>`
                        }
                    </div>
                    <button onclick="downloadMap(${map.id})" class="submit-btn" style="width: 100%; margin-bottom: 20px;">📥 Download Map</button>

                    <div style="background: rgba(255, 255, 255, 0.1); padding: 20px; border-radius: 10px;">
                        <h3 style="color: #ffd700; margin-bottom: 15px;">Rate this Map</h3>
                        <div id="ratingSection">
                            <div id="userRating" class="user-rating-stars" style="font-size: 32px; cursor: pointer; display: flex; gap: 5px;">
                                ${createInteractiveStars(0, map.id)}
                            </div>
                            <div id="ratingMessage" style="margin-top: 10px; font-size: 14px; opacity: 0.8;"></div>
                        </div>
                    </div>
                </div>

                <div>
                    <h3 style="color: #ffd700; margin-bottom: 15px;">Map Information</h3>
                    <div style="background: rgba(255, 255, 255, 0.1); padding: 20px; border-radius: 10px;">
                        <div style="margin-bottom: 15px;">
                            <strong style="color: #ffd700;">Terrain:</strong> ${capitalizeFirst(map.terrain_type)}
                        </div>
                        <div style="margin-bottom: 15px;">
                            <strong style="color: #ffd700;">Size:</strong> ${sizeLabel}
                        </div>
                        <div style="margin-bottom: 15px;">
                            <strong style="color: #ffd700;">Players:</strong> ${map.player_count}
                        </div>
                        <div style="margin-bottom: 15px;">
                            <strong style="color: #ffd700;">Creator:</strong> ${escapeHtml(map.creator?.username || map.author || 'Unknown')}
                        </div>
                        <div style="margin-bottom: 15px;">
                            <strong style="color: #ffd700;">Version:</strong> ${escapeHtml(map.version)}
                        </div>
                    </div>

                    <h3 style="color: #ffd700; margin: 25px 0 15px 0;">Description</h3>
                    <p style="line-height: 1.6; opacity: 0.9;">${escapeHtml(map.description || 'No description provided.')}</p>
                </div>
            </div>

            <div class="comments-section" style="background: rgba(0, 0, 0, 0.2); padding: 30px; border-radius: 10px;">
                <h2 style="color: #ffd700; margin-bottom: 20px;">Comments</h2>
                <div id="commentsContainer">
                    <div class="loading">
                        <p>Loading comments...</p>
                    </div>
                </div>
            </div>
        `;

        // Initialize rating stars interaction
        initializeRatingStars(map.id);

        // Load comments
        loadComments(map.id);

        // Load user's existing rating if logged in
        if (currentUser) {
            loadUserRating(map.id);
        }

        showSection('detail');
    } catch (error) {
        showError('Failed to load map details. Please try again later.');
        console.error('Error loading map details:', error);
    }
}

// Download map
function downloadMap(mapId) {
    window.location.href = `${API_BASE_URL}/maps/${mapId}/download`;
}

// =============================================================================
// Rating Functions
// =============================================================================

// Create interactive star rating HTML
function createInteractiveStars(userRating, mapId) {
    let starsHtml = '';
    for (let i = 1; i <= 5; i++) {
        const isFilled = i <= userRating;
        starsHtml += `<span class="star" data-rating="${i}" data-map-id="${mapId}" style="color: ${isFilled ? '#ffd700' : '#666'}; transition: color 0.2s;">★</span>`;
    }
    return starsHtml;
}

// Initialize rating stars click handlers
function initializeRatingStars(mapId) {
    const starsContainer = document.getElementById('userRating');
    if (!starsContainer) return;

    const stars = starsContainer.querySelectorAll('.star');

    stars.forEach(star => {
        // Hover effect
        star.addEventListener('mouseenter', function() {
            const rating = parseInt(this.dataset.rating);
            highlightStars(stars, rating);
        });

        // Reset on mouse leave
        star.addEventListener('mouseleave', function() {
            const currentRating = parseInt(starsContainer.dataset.currentRating || 0);
            highlightStars(stars, currentRating);
        });

        // Click to submit rating
        star.addEventListener('click', function() {
            const rating = parseInt(this.dataset.rating);
            submitRating(mapId, rating);
        });
    });

    // Set initial rating
    starsContainer.dataset.currentRating = 0;
}

// Highlight stars up to the given rating
function highlightStars(stars, rating) {
    stars.forEach(star => {
        const starRating = parseInt(star.dataset.rating);
        star.style.color = starRating <= rating ? '#ffd700' : '#666';
    });
}

// Submit rating to API
async function submitRating(mapId, rating) {
    if (!currentUser) {
        // Store pending action
        localStorage.setItem('pendingSection', 'detail');
        showAuthModal('login');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/maps/${mapId}/ratings`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ rating })
        });

        if (!response.ok) {
            // If unauthorized, try to refresh auth or show login
            if (response.status === 401) {
                clearAuthState();
                updateNavigation();
                localStorage.setItem('pendingSection', 'detail');
                showAuthModal('login');
                return;
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Update UI
        const starsContainer = document.getElementById('userRating');
        if (starsContainer) {
            starsContainer.dataset.currentRating = rating;
            highlightStars(starsContainer.querySelectorAll('.star'), rating);
        }

        const messageEl = document.getElementById('ratingMessage');
        if (messageEl) {
            messageEl.textContent = `You rated this map ${rating} star${rating !== 1 ? 's' : ''}!`;
            messageEl.style.color = '#4caf50';
        }

        showNotification('Rating submitted successfully!');

        // Refresh map details to update average rating
        setTimeout(() => showMapDetail(mapId), 500);
    } catch (error) {
        const messageEl = document.getElementById('ratingMessage');
        if (messageEl) {
            messageEl.textContent = 'Failed to submit rating. Please try again.';
            messageEl.style.color = '#ff6b6b';
        }
        showNotification('Failed to submit rating');
        console.error('Error submitting rating:', error);
    }
}

// Load user's existing rating for a map
async function loadUserRating(mapId) {
    try {
        // We need to get the user's rating from the ratings endpoint
        // For now, we'll skip this as the API doesn't provide a direct endpoint
        // The rating will be fetched when the user rates the map
    } catch (error) {
        console.error('Error loading user rating:', error);
    }
}

// =============================================================================
// Comment Functions
// =============================================================================

// Load comments for a map
async function loadComments(mapId) {
    const container = document.getElementById('commentsContainer');
    if (!container) return;

    try {
        const response = await fetch(`${API_BASE_URL}/maps/${mapId}/comments?limit=50`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const comments = await response.json();
        displayComments(comments, mapId);
    } catch (error) {
        container.innerHTML = `
            <div style="color: #ff6b6b;">
                <p>Failed to load comments. Please try again later.</p>
            </div>
        `;
        console.error('Error loading comments:', error);
    }
}

// Display comments
function displayComments(comments, mapId) {
    const container = document.getElementById('commentsContainer');
    if (!container) return;

    if (comments.length === 0) {
        container.innerHTML = `
            <p style="opacity: 0.7;">No comments yet. Be the first to comment!</p>
            ${createCommentForm(mapId)}
        `;
        return;
    }

    const commentsHtml = comments.map(comment => createCommentHtml(comment, mapId)).join('');

    container.innerHTML = `
        <div class="comments-list">
            ${commentsHtml}
        </div>
        ${createCommentForm(mapId)}
    `;

    // Add event listeners for edit/delete buttons
    attachCommentEventListeners(mapId);
}

// Create HTML for a single comment
function createCommentHtml(comment, mapId) {
    const isOwner = currentUser && comment.user_id === currentUser.id;
    const date = new Date(comment.created_at).toLocaleDateString();

    return `
        <div class="comment" data-comment-id="${comment.id}" style="background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 8px; margin-bottom: 15px;">
            <div class="comment-header" style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                <div>
                    <strong style="color: #ffd700;">${escapeHtml(comment.author?.username || 'Unknown')}</strong>
                    <span style="opacity: 0.6; font-size: 12px; margin-left: 10px;">${date}</span>
                </div>
                ${isOwner ? `
                    <div class="comment-actions">
                        <button class="edit-comment-btn" data-comment-id="${comment.id}" style="background: none; border: none; color: #4a90e2; cursor: pointer; margin-right: 10px;">Edit</button>
                        <button class="delete-comment-btn" data-comment-id="${comment.id}" style="background: none; border: none; color: #ff6b6b; cursor: pointer;">Delete</button>
                    </div>
                ` : ''}
            </div>
            <div class="comment-content" id="comment-content-${comment.id}" style="line-height: 1.5;">
                ${escapeHtml(comment.content)}
            </div>
            ${isOwner ? `
                <div class="comment-edit-form" id="comment-edit-form-${comment.id}" style="display: none; margin-top: 10px;">
                    <textarea class="edit-comment-textarea form-textarea" rows="3" style="width: 100%; background: rgba(255, 255, 255, 0.1); color: white; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 5px; padding: 10px;">${escapeHtml(comment.content)}</textarea>
                    <div style="margin-top: 10px;">
                        <button class="save-comment-btn" data-comment-id="${comment.id}" class="submit-btn" style="margin-right: 10px;">Save</button>
                        <button class="cancel-edit-btn" data-comment-id="${comment.id}" class="cancel-btn">Cancel</button>
                    </div>
                </div>
            ` : ''}
        </div>
    `;
}

// Create comment submission form
function createCommentForm(mapId) {
    return `
        <div class="comment-form-container" style="margin-top: 30px;">
            <h3 style="color: #ffd700; margin-bottom: 15px;">${currentUser ? 'Add a Comment' : 'Login to Comment'}</h3>
            ${currentUser ? `
                <form id="commentForm" class="comment-form" style="background: rgba(255, 255, 255, 0.1); padding: 20px; border-radius: 10px;">
                    <div class="form-group">
                        <textarea
                            id="commentText"
                            class="form-textarea"
                            rows="4"
                            placeholder="Share your thoughts about this map..."
                            required
                            style="width: 100%; background: rgba(255, 255, 255, 0.1); color: white; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 5px; padding: 10px;"
                        ></textarea>
                    </div>
                    <button type="submit" class="submit-btn">💬 Post Comment</button>
                </form>
            ` : `
                <p style="opacity: 0.7;">You need to be logged in to post comments.</p>
                <button onclick="showAuthModal('login')" class="auth-btn" style="margin-top: 10px;">Login to Comment</button>
            `}
        </div>
    `;
}

// Attach event listeners for comment actions
function attachCommentEventListeners(mapId) {
    // Comment form submission
    const commentForm = document.getElementById('commentForm');
    if (commentForm) {
        commentForm.addEventListener('submit', (e) => {
            e.preventDefault();
            submitComment(mapId);
        });
    }

    // Edit buttons
    document.querySelectorAll('.edit-comment-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const commentId = this.dataset.commentId;
            showEditForm(commentId);
        });
    });

    // Delete buttons
    document.querySelectorAll('.delete-comment-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const commentId = this.dataset.commentId;
            if (confirm('Are you sure you want to delete this comment?')) {
                deleteComment(mapId, commentId);
            }
        });
    });

    // Save edit buttons
    document.querySelectorAll('.save-comment-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const commentId = this.dataset.commentId;
            saveEditedComment(mapId, commentId);
        });
    });

    // Cancel edit buttons
    document.querySelectorAll('.cancel-edit-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const commentId = this.dataset.commentId;
            hideEditForm(commentId);
        });
    });
}

// Submit a new comment
async function submitComment(mapId) {
    if (!currentUser) {
        localStorage.setItem('pendingSection', 'detail');
        showAuthModal('login');
        return;
    }

    const text = document.getElementById('commentText').value.trim();

    if (!text) {
        showNotification('Please enter a comment');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/maps/${mapId}/comments`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ content: text })
        });

        if (!response.ok) {
            if (response.status === 401) {
                clearAuthState();
                updateNavigation();
                localStorage.setItem('pendingSection', 'detail');
                showAuthModal('login');
                return;
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        showNotification('Comment posted successfully!');
        loadComments(mapId);
    } catch (error) {
        showNotification('Failed to post comment');
        console.error('Error submitting comment:', error);
    }
}

// Show edit form for a comment
function showEditForm(commentId) {
    const editForm = document.getElementById(`comment-edit-form-${commentId}`);
    const contentDiv = document.getElementById(`comment-content-${commentId}`);

    if (editForm && contentDiv) {
        editForm.style.display = 'block';
        contentDiv.style.display = 'none';
    }
}

// Hide edit form for a comment
function hideEditForm(commentId) {
    const editForm = document.getElementById(`comment-edit-form-${commentId}`);
    const contentDiv = document.getElementById(`comment-content-${commentId}`);

    if (editForm && contentDiv) {
        editForm.style.display = 'none';
        contentDiv.style.display = 'block';
    }
}

// Save edited comment
async function saveEditedComment(mapId, commentId) {
    const textarea = document.querySelector(`#comment-edit-form-${commentId} .edit-comment-textarea`);
    const newContent = textarea.value.trim();

    if (!newContent) {
        showNotification('Comment cannot be empty');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/maps/${mapId}/comments/${commentId}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify({ content: newContent })
        });

        if (!response.ok) {
            if (response.status === 401) {
                clearAuthState();
                updateNavigation();
                showNotification('Session expired. Please login again.');
                return;
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        showNotification('Comment updated successfully!');
        loadComments(mapId);
    } catch (error) {
        showNotification('Failed to update comment');
        console.error('Error updating comment:', error);
    }
}

// Delete a comment
async function deleteComment(mapId, commentId) {
    try {
        const response = await fetch(`${API_BASE_URL}/maps/${mapId}/comments/${commentId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            if (response.status === 401) {
                clearAuthState();
                updateNavigation();
                showNotification('Session expired. Please login again.');
                return;
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        showNotification('Comment deleted successfully!');
        loadComments(mapId);
    } catch (error) {
        showNotification('Failed to delete comment');
        console.error('Error deleting comment:', error);
    }
}

// Search functionality - trigger API fetch
async function handleSearch() {
    currentPage = 1;
    await loadMaps();
}

// Apply all filters - trigger API fetch
async function applyFilters() {
    currentPage = 1;
    await loadMaps();
}

// Reset all filters
async function resetFilters() {
    document.getElementById('searchInput').value = '';
    document.getElementById('terrainFilter').value = '';
    document.getElementById('sizeFilter').value = '';
    document.getElementById('playersFilter').value = '';
    document.getElementById('sortBy').value = 'newest';

    currentPage = 1;
    await loadMaps();
}

// Pagination
async function changePage(direction) {
    const newPage = currentPage + direction;

    if (newPage >= 1 && newPage <= totalPages) {
        currentPage = newPage;
        await loadMaps();
        // Scroll to top of maps section
        document.querySelector('.maps-section').scrollIntoView({ behavior: 'smooth' });
    }
}

function updatePagination() {
    const pageInfo = document.getElementById('pageInfo');
    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');

    pageInfo.textContent = `Page ${currentPage} of ${totalPages || 1}`;
    prevBtn.disabled = currentPage <= 1;
    nextBtn.disabled = currentPage >= totalPages;
}

function updateMapCount() {
    document.getElementById('mapCount').textContent = totalMaps;
    // Update section title based on view mode
    const sectionTitle = document.querySelector('.maps-section h2');
    if (sectionTitle) {
        sectionTitle.textContent = showingMyMaps ? 'My Maps' : 'Community Maps';
    }
}

// UI Helper functions
function showLoading() {
    const grid = document.getElementById('mapsGrid');
    grid.innerHTML = `
        <div class="loading">
            <p>Loading maps...</p>
        </div>
    `;
}

function showError(message) {
    const grid = document.getElementById('mapsGrid');
    grid.innerHTML = `
        <div class="loading" style="color: #ff6b6b;">
            <p>${escapeHtml(message)}</p>
            <button onclick="loadMaps()" class="reset-btn" style="margin-top: 15px;">Retry</button>
        </div>
    `;
}

// Navigation
function handleNavigation(e) {
    e.preventDefault();
    const section = e.target.getAttribute('href').substring(1);

    // Update active link
    document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
    e.target.classList.add('active');

    showSection(section);
}

function showSection(section) {
    const mapsSection = document.querySelector('.maps-section');
    const uploadSection = document.getElementById('uploadSection');
    const detailSection = document.getElementById('mapDetailSection');

    // Hide all sections
    mapsSection.classList.add('hidden');
    uploadSection.classList.add('hidden');
    detailSection.classList.add('hidden');

    // Show selected section
    switch (section) {
        case 'browse':
            showingMyMaps = false;
            mapsSection.classList.remove('hidden');
            loadMaps();
            break;
        case 'upload':
            showingMyMaps = false;
            if (!currentUser) {
                localStorage.setItem('pendingSection', 'upload');
                showAuthModal('login');
                return;
            }
            uploadSection.classList.remove('hidden');
            // Pre-fill form with map generator metadata if available
            preFillUploadForm();
            break;
        case 'my-maps':
            if (!currentUser) {
                localStorage.setItem('pendingSection', 'my-maps');
                showAuthModal('login');
                return;
            }
            showingMyMaps = true;
            // Reset to first page when switching to My Maps
            currentPage = 1;
            mapsSection.classList.remove('hidden');
            loadMaps();
            break;
        case 'detail':
            showingMyMaps = false;
            detailSection.classList.remove('hidden');
            break;
    }
}

function updateNavigation() {
    // Update navigation based on auth state
    const authSection = document.querySelector('.auth-section');

    if (currentUser) {
        authSection.innerHTML = `
            <span style="color: #ffd700; font-weight: 500;">Welcome, ${escapeHtml(currentUser.username)}</span>
            <button id="logoutBtn" class="auth-btn secondary">Logout</button>
        `;
        // Add event listener to new logout button
        document.getElementById('logoutBtn').addEventListener('click', handleLogout);
    } else {
        authSection.innerHTML = `
            <button id="loginBtn" class="auth-btn">Login</button>
            <button id="registerBtn" class="auth-btn secondary">Register</button>
        `;
        // Add event listeners to new auth buttons
        document.getElementById('loginBtn').addEventListener('click', () => showAuthModal('login'));
        document.getElementById('registerBtn').addEventListener('click', () => showAuthModal('register'));
    }
}

// =============================================================================
// Authentication State Management
// =============================================================================

// Load authentication state from localStorage
function loadAuthState() {
    const storedToken = localStorage.getItem('authToken');
    const storedUser = localStorage.getItem('currentUser');

    if (storedToken && storedUser) {
        try {
            authToken = storedToken;
            currentUser = JSON.parse(storedUser);
        } catch (error) {
            // Clear invalid stored data
            clearAuthState();
        }
    }
}

// Save authentication state to localStorage
function saveAuthState(token, user) {
    authToken = token;
    currentUser = user;
    localStorage.setItem('authToken', token);
    localStorage.setItem('currentUser', JSON.stringify(user));
}

// Clear authentication state from localStorage
function clearAuthState() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
}

// Get Authorization header for API requests
function getAuthHeaders(contentType = 'application/json') {
    const headers = {};

    if (contentType) {
        headers['Content-Type'] = contentType;
    }

    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }

    return headers;
}

// =============================================================================
// Authentication UI Functions
// =============================================================================

function showAuthModal(mode) {
    const modal = document.getElementById('authModal');
    const title = document.getElementById('authModalTitle');
    const registerFields = document.getElementById('registerFields');
    const switchBtn = document.getElementById('switchAuthModeBtn');
    const emailLabel = document.getElementById('emailLabel');
    const emailHint = document.getElementById('emailHint');
    const submitBtn = document.querySelector('#authForm .submit-btn');

    modal.classList.remove('hidden');

    if (mode === 'login') {
        title.textContent = 'Login';
        registerFields.classList.add('hidden');
        switchBtn.textContent = 'Need an account? Register';
        emailLabel.textContent = 'Username or Email *';
        emailHint.style.display = 'block';
        emailHint.textContent = 'Enter your username or email address';
        submitBtn.textContent = 'Login';

        // Update form field requirements
        document.getElementById('authUsername').removeAttribute('required');
        document.getElementById('authEmail').placeholder = 'username or email@example.com';
    } else {
        title.textContent = 'Register';
        registerFields.classList.remove('hidden');
        switchBtn.textContent = 'Already have an account? Login';
        emailLabel.textContent = 'Email *';
        emailHint.style.display = 'none';
        submitBtn.textContent = 'Register';

        // Update form field requirements
        document.getElementById('authUsername').setAttribute('required', 'true');
        document.getElementById('authEmail').placeholder = 'your@email.com';
    }
}

function hideAuthModal() {
    document.getElementById('authModal').classList.add('hidden');
    document.getElementById('authForm').reset();

    // Clear any error messages
    const authMessage = document.getElementById('authMessage');
    if (authMessage) {
        authMessage.remove();
    }
}

function switchAuthMode() {
    const title = document.getElementById('authModalTitle');
    const registerFields = document.getElementById('registerFields');
    const switchBtn = document.getElementById('switchAuthModeBtn');
    const emailLabel = document.getElementById('emailLabel');
    const emailHint = document.getElementById('emailHint');
    const submitBtn = document.querySelector('#authForm .submit-btn');

    if (title.textContent === 'Login') {
        title.textContent = 'Register';
        registerFields.classList.remove('hidden');
        switchBtn.textContent = 'Already have an account? Login';
        emailLabel.textContent = 'Email *';
        emailHint.style.display = 'none';
        submitBtn.textContent = 'Register';

        document.getElementById('authUsername').setAttribute('required', 'true');
        document.getElementById('authEmail').placeholder = 'your@email.com';
    } else {
        title.textContent = 'Login';
        registerFields.classList.add('hidden');
        switchBtn.textContent = 'Need an account? Register';
        emailLabel.textContent = 'Username or Email *';
        emailHint.style.display = 'block';
        emailHint.textContent = 'Enter your username or email address';
        submitBtn.textContent = 'Login';

        document.getElementById('authUsername').removeAttribute('required');
        document.getElementById('authEmail').placeholder = 'username or email@example.com';
    }
}

async function handleAuth(e) {
    e.preventDefault();

    const isRegister = document.getElementById('authModalTitle').textContent === 'Register';
    const emailField = document.getElementById('authEmail').value;
    const password = document.getElementById('authPassword').value;

    // Clear previous error messages
    const existingMessage = document.getElementById('authMessage');
    if (existingMessage) {
        existingMessage.remove();
    }

    try {
        if (isRegister) {
            // Registration
            const username = document.getElementById('authUsername').value;

            if (!username || !emailField || !password) {
                showAuthError('Please fill in all required fields');
                return;
            }

            if (username.length < 3) {
                showAuthError('Username must be at least 3 characters long');
                return;
            }

            if (password.length < 8) {
                showAuthError('Password must be at least 8 characters long');
                return;
            }

            const response = await fetch(`${API_BASE_URL}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: username,
                    email: emailField,
                    password: password
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Registration failed' }));
                throw new Error(errorData.detail || 'Registration failed');
            }

            const data = await response.json();

            // Save auth state
            saveAuthState(data.access_token, data.user);

            hideAuthModal();
            updateNavigation();

            // Show success message
            showNotification('Registration successful! Welcome to BAR Community Maps!');

            // If user was trying to access a protected section, show it now
            const pendingSection = localStorage.getItem('pendingSection');
            if (pendingSection) {
                localStorage.removeItem('pendingSection');
                showSection(pendingSection);
            }
        } else {
            // Login - emailField can be username or email
            const username = emailField; // Backend accepts either username or email

            if (!username || !password) {
                showAuthError('Please fill in all required fields');
                return;
            }

            const response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Login failed' }));
                throw new Error(errorData.detail || 'Invalid credentials');
            }

            const data = await response.json();

            // Save auth state
            saveAuthState(data.access_token, data.user);

            hideAuthModal();
            updateNavigation();

            // Show success message
            showNotification(`Welcome back, ${data.user.username}!`);

            // If user was trying to access a protected section, show it now
            const pendingSection = localStorage.getItem('pendingSection');
            if (pendingSection) {
                localStorage.removeItem('pendingSection');
                showSection(pendingSection);
            }
        }
    } catch (error) {
        showAuthError(error.message || 'Authentication failed. Please try again.');
        console.error('Authentication error:', error);
    }
}

function showAuthError(message) {
    const modalBody = document.querySelector('.modal-body');

    // Remove existing error message
    const existingMessage = document.getElementById('authMessage');
    if (existingMessage) {
        existingMessage.remove();
    }

    // Add new error message
    const errorDiv = document.createElement('div');
    errorDiv.id = 'authMessage';
    errorDiv.style.cssText = `
        background: rgba(255, 107, 107, 0.2);
        border: 1px solid rgba(255, 107, 107, 0.5);
        color: #ff6b6b;
        padding: 10px 15px;
        border-radius: 5px;
        margin-bottom: 15px;
        text-align: center;
    `;
    errorDiv.textContent = message;

    modalBody.insertBefore(errorDiv, modalBody.firstChild);
}

function handleLogout() {
    clearAuthState();
    updateNavigation();
    showNotification('Logged out successfully');

    // Go back to browse section
    showSection('browse');
}

// Upload functionality
async function handleUpload(e) {
    e.preventDefault();

    // Check if user is logged in
    if (!currentUser) {
        showAuthModal('login');
        return;
    }

    // Get form values
    const mapName = document.getElementById('mapName').value.trim();
    const mapDescription = document.getElementById('mapDescription').value.trim();
    const mapTerrain = document.getElementById('mapTerrain').value;
    const mapSize = document.getElementById('mapSize').value;
    const mapPlayers = document.getElementById('mapPlayers').value;
    const mapTags = document.getElementById('mapTags').value.trim();
    const mapFileInput = document.getElementById('mapFile');
    const mapPreviewInput = document.getElementById('mapPreview');

    // Validate required fields
    if (!mapName || !mapDescription || !mapTerrain || !mapSize || !mapPlayers) {
        showNotification('Please fill in all required fields');
        return;
    }

    // Validate map file
    if (!mapFileInput.files || mapFileInput.files.length === 0) {
        showNotification('Please select a map file (.sd7)');
        return;
    }

    const mapFile = mapFileInput.files[0];
    if (!mapFile.name.endsWith('.sd7')) {
        showNotification('Map file must be a .sd7 file');
        return;
    }

    // Create FormData for multipart upload
    const formData = new FormData();
    formData.append('name', mapName);
    formData.append('description', mapDescription);
    formData.append('terrain_type', mapTerrain);
    formData.append('size', mapSize);
    formData.append('player_count', mapPlayers);

    // Add tags if provided
    if (mapTags) {
        const tagsArray = mapTags.split(',').map(tag => tag.trim()).filter(tag => tag);
        formData.append('tags', JSON.stringify(tagsArray));
    }

    // Add map file
    formData.append('map_file', mapFile);

    // Add preview image if provided
    if (mapPreviewInput.files && mapPreviewInput.files.length > 0) {
        const previewFile = mapPreviewInput.files[0];
        if (!previewFile.type.match('image/(png|jpeg)')) {
            showNotification('Preview image must be PNG or JPG');
            return;
        }
        formData.append('preview_image', previewFile);
    }

    // Disable submit button during upload
    const submitBtn = document.querySelector('#uploadForm .submit-btn');
    const originalBtnText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Uploading...';

    try {
        const response = await fetch(`${API_BASE_URL}/maps`, {
            method: 'POST',
            headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {},
            body: formData
        });

        if (!response.ok) {
            if (response.status === 401) {
                clearAuthState();
                updateNavigation();
                localStorage.setItem('pendingSection', 'upload');
                showAuthModal('login');
                return;
            }
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        showNotification('Map uploaded successfully!');

        // Clear pending map upload data
        localStorage.removeItem('pendingMapUpload');

        // Reset form and go back to browse
        document.getElementById('uploadForm').reset();
        showSection('browse');

        // Reload maps to show the newly uploaded map
        await loadMaps();
    } catch (error) {
        showNotification(`Upload failed: ${error.message}`);
        console.error('Error uploading map:', error);
    } finally {
        // Re-enable submit button
        submitBtn.disabled = false;
        submitBtn.textContent = originalBtnText;
    }
}

// =============================================================================
// Map Generator Integration Functions
// =============================================================================

// Check for pending map upload from map generator
function checkForPendingMapUpload() {
    const pendingData = localStorage.getItem('pendingMapUpload');

    if (!pendingData) {
        return;
    }

    try {
        const mapMetadata = JSON.parse(pendingData);

        // Check if the data is recent (within 1 hour)
        const age = Date.now() - mapMetadata.timestamp;
        if (age > 3600000) { // 1 hour in milliseconds
            localStorage.removeItem('pendingMapUpload');
            return;
        }

        // Store the metadata for later use when showing upload form
        window.pendingMapMetadata = mapMetadata;

        // Show a notification to the user
        showNotification('Map metadata from generator loaded! Click "Upload Map" to continue.');
    } catch (error) {
        console.error('Error parsing pending map upload data:', error);
        localStorage.removeItem('pendingMapUpload');
    }
}

// Pre-fill upload form with map metadata
function preFillUploadForm() {
    if (!window.pendingMapMetadata) {
        return;
    }

    const metadata = window.pendingMapMetadata;

    // Pre-fill the form fields
    if (metadata.size) {
        document.getElementById('mapSize').value = metadata.size;
    }

    if (metadata.terrainType) {
        document.getElementById('mapTerrain').value = metadata.terrainType;
    }

    if (metadata.playerCount) {
        document.getElementById('mapPlayers').value = metadata.playerCount;
    }

    // Generate a suggested name based on terrain type
    if (metadata.terrainType) {
        const terrainNames = {
            'continental': 'Continental',
            'islands': 'Islands',
            'canyon': 'Canyon',
            'hills': 'Hills',
            'flat': 'Flat'
        };
        const sizeLabels = {
            '512': 'Small',
            '1024': 'Medium',
            '2048': 'Large'
        };
        const sizeLabel = sizeLabels[metadata.size] || metadata.size;
        const terrainName = terrainNames[metadata.terrainType] || metadata.terrainType;

        const mapNameField = document.getElementById('mapName');
        if (!mapNameField.value) {
            mapNameField.value = `${terrainName} ${sizeLabel} Map`;
        }

        const mapDescField = document.getElementById('mapDescription');
        if (!mapDescField.value) {
            mapDescField.value = `A ${metadata.terrainType} terrain map for ${metadata.playerCount} players, generated with the BAR Map Generator.`;
        }
    }

    // Handle auto-generated preview image
    const pendingPreview = localStorage.getItem('pendingMapPreview');
    if (pendingPreview) {
        try {
            // Display the preview image
            const previewContainer = document.getElementById('previewContainer');
            const previewImageDisplay = document.getElementById('previewImageDisplay');
            previewImageDisplay.src = pendingPreview;
            previewContainer.style.display = 'block';

            // Convert base64 to a Blob
            const base64Data = pendingPreview.split(',')[1];
            const byteCharacters = atob(base64Data);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], { type: 'image/png' });

            // Create a File object from the Blob
            const previewFile = new File([blob], 'map_preview.png', { type: 'image/png' });

            // Create a DataTransfer to set the file input value
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(previewFile);

            // Set the file input's files
            const previewInput = document.getElementById('mapPreview');
            previewInput.files = dataTransfer.files;

            // Show notification that preview was auto-generated
            showNotification('Preview image auto-generated from map canvas!');

            // Clear the stored preview after setting it
            localStorage.removeItem('pendingMapPreview');
        } catch (error) {
            console.error('Error setting preview image:', error);
        }
    }
}

// Utility functions
function getSizeLabel(size) {
    switch (size) {
        case 512: return '512x512 (Small)';
        case 1024: return '1024x1024 (Medium)';
        case 2048: return '2048x2048 (Large)';
        default: return `${size}x${size}`;
    }
}

function createStarRating(rating) {
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;
    let stars = '★'.repeat(fullStars);
    if (hasHalfStar) stars += '½';
    return stars;
}

function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatNumber(num) {
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'k';
    }
    return num.toString();
}

function showNotification(message) {
    // Simple notification - could be enhanced with a toast notification
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: linear-gradient(45deg, #ff6b6b, #ff8e53);
        color: white;
        padding: 15px 25px;
        border-radius: 8px;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
        z-index: 2000;
        animation: slideIn 0.3s ease-out;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add CSS animations for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
