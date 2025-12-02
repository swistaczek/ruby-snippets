/**
 * Interactive search, filter, and copy functionality for Ruby & Rails Patterns
 */

(function() {
  'use strict';

  // State
  let currentCategory = 'all';
  let currentSource = 'all';
  let currentSearchTerm = '';

  // DOM elements
  const searchBox = document.getElementById('searchBox');
  const categoryFilters = document.getElementById('categoryFilters');
  const sourceFilters = document.getElementById('sourceFilters');
  const resultsCount = document.getElementById('resultsCount');
  const patterns = document.querySelectorAll('.pattern');

  /**
   * Filter patterns based on search term, category, and source
   */
  function filterPatterns() {
    let visibleCount = 0;
    const searchLower = currentSearchTerm.toLowerCase();

    patterns.forEach(pattern => {
      const category = pattern.getAttribute('data-category');
      const source = pattern.getAttribute('data-source');
      const name = pattern.getAttribute('data-name') || '';
      const keywords = pattern.getAttribute('data-keywords') || '';
      const description = pattern.querySelector('p')?.textContent.toLowerCase() || '';

      // Check category filter
      const categoryMatch = currentCategory === 'all' || category === currentCategory;

      // Check source filter
      const sourceMatch = currentSource === 'all' || source === currentSource;

      // Check search term (matches name, description, or keywords)
      const searchMatch = !searchLower ||
        name.includes(searchLower) ||
        description.includes(searchLower) ||
        keywords.includes(searchLower);

      // Show/hide pattern
      if (categoryMatch && sourceMatch && searchMatch) {
        pattern.setAttribute('data-hidden', 'false');
        visibleCount++;
      } else {
        pattern.setAttribute('data-hidden', 'true');
      }
    });

    // Update results count
    updateResultsCount(visibleCount);
  }

  /**
   * Update the results count display
   */
  function updateResultsCount(count) {
    const total = patterns.length;
    if (currentSearchTerm || currentCategory !== 'all' || currentSource !== 'all') {
      resultsCount.textContent = `${count} of ${total} patterns`;
    } else {
      resultsCount.textContent = `${total} patterns`;
    }
  }

  /**
   * Handle search input
   */
  function handleSearch(event) {
    currentSearchTerm = event.target.value;
    filterPatterns();
  }

  /**
   * Handle category filter click
   */
  function handleCategoryClick(event) {
    if (!event.target.classList.contains('filter-btn')) return;

    // Update active button
    document.querySelectorAll('.filter-btn').forEach(btn => {
      btn.classList.remove('active');
    });
    event.target.classList.add('active');

    // Update current category
    currentCategory = event.target.getAttribute('data-category');
    filterPatterns();
  }

  /**
   * Handle source filter click
   */
  function handleSourceClick(event) {
    if (!event.target.classList.contains('source-btn')) return;

    // Update active button
    document.querySelectorAll('.source-btn').forEach(btn => {
      btn.classList.remove('active');
    });
    event.target.classList.add('active');

    // Update current source
    currentSource = event.target.getAttribute('data-source');
    filterPatterns();
  }

  /**
   * Copy code to clipboard
   */
  window.copyCode = function(button) {
    const pre = button.parentElement;
    const code = pre.querySelector('code');
    const text = code.textContent;

    // Copy to clipboard
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => {
        showCopyFeedback(button);
      }).catch(err => {
        console.error('Failed to copy:', err);
        fallbackCopy(text, button);
      });
    } else {
      fallbackCopy(text, button);
    }
  };

  /**
   * Fallback copy method for older browsers
   */
  function fallbackCopy(text, button) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();

    try {
      document.execCommand('copy');
      showCopyFeedback(button);
    } catch (err) {
      console.error('Fallback copy failed:', err);
    }

    document.body.removeChild(textarea);
  }

  /**
   * Show "Copied!" feedback on button
   */
  function showCopyFeedback(button) {
    const originalText = button.textContent;
    button.textContent = 'Copied!';
    button.classList.add('copied');

    setTimeout(() => {
      button.textContent = originalText;
      button.classList.remove('copied');
    }, 2000);
  }

  /**
   * Keyboard shortcuts
   */
  function handleKeyboard(event) {
    // Ctrl/Cmd + K to focus search
    if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
      event.preventDefault();
      searchBox.focus();
    }

    // Escape to clear search
    if (event.key === 'Escape' && document.activeElement === searchBox) {
      searchBox.value = '';
      currentSearchTerm = '';
      filterPatterns();
    }
  }

  /**
   * Initialize
   */
  function init() {
    // Event listeners
    if (searchBox) {
      searchBox.addEventListener('input', handleSearch);
    }

    if (categoryFilters) {
      categoryFilters.addEventListener('click', handleCategoryClick);
    }

    if (sourceFilters) {
      sourceFilters.addEventListener('click', handleSourceClick);
    }

    document.addEventListener('keydown', handleKeyboard);

    // Initial count
    updateResultsCount(patterns.length);

    console.log('✓ Interactive features loaded');
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
