/**
 * ==============================================================================
 * Siamul Karim Khan - Personal Academic & Professional Portfolio
 * Main JavaScript Controller
 * ==============================================================================
 * Features:
 * 1. Dark/Light theme switching with system detection and localStorage persistence.
 * 2. Mobile navigation drawer toggle with outside-click and ESC auto-close.
 * 3. Floating navigation bar with frosted glass backdrop on scroll.
 * 4. Smooth anchor navigation with dynamic navbar offset calculation.
 * 5. Active navigation highlight with viewport and edge-case tracking.
 * 6. Publication filtering by category pills and real-time search query.
 * 7. Interactive BibTeX modal & one-click copy.
 * 8. Email copy-to-clipboard with visual toast feedback.
 * 9. Volunteer photo lightbox preview modal.
 * 10. Back-to-top button visibility on scroll.
 * 11. YouTube playlist cover switcher.
 */

(function () {
  "use strict";

  // Document ready helper
  function ready(fn) {
    if (document.readyState !== "loading") {
      fn();
    } else {
      document.addEventListener("DOMContentLoaded", fn);
    }
  }

  ready(function () {
    initTheme();
    initMobileNav();
    initFloatingNav();
    initSmoothNav();
    initBackToTop();
    initActiveNavLinks();
    initPublicationFilters();
    initScholarDataHydration();
    initEmailCopy();
    initBibtexModal();
    initVolunteerLightbox();
    initYouTubeCoverSwitcher();
  });

  // ----------------------------------------------------------------------------
  // 1. Theme Switcher (Dark / Light)
  // ----------------------------------------------------------------------------
  function initTheme() {
    var themeToggleBtn = document.getElementById("theme-toggle");
    var htmlElement = document.documentElement;

    // Check saved theme or system preference
    var savedTheme = localStorage.getItem("theme");
    var systemPrefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;

    if (savedTheme) {
      htmlElement.setAttribute("data-theme", savedTheme);
    } else if (systemPrefersDark) {
      htmlElement.setAttribute("data-theme", "dark");
    } else {
      htmlElement.setAttribute("data-theme", "light");
    }

    if (themeToggleBtn) {
      themeToggleBtn.addEventListener("click", function () {
        var currentTheme = htmlElement.getAttribute("data-theme") || "light";
        var newTheme = currentTheme === "dark" ? "light" : "dark";

        htmlElement.setAttribute("data-theme", newTheme);
        localStorage.setItem("theme", newTheme);
      });
    }

    // Listen for OS system theme changes if user hasn't explicitly set a preference
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function (e) {
      if (!localStorage.getItem("theme")) {
        htmlElement.setAttribute("data-theme", e.matches ? "dark" : "light");
      }
    });
  }

  // ----------------------------------------------------------------------------
  // 2. Mobile Navigation Toggle
  // ----------------------------------------------------------------------------
  function initMobileNav() {
    var navToggle = document.getElementById("nav-toggle");
    var navMenu = document.getElementById("nav-menu");
    var navLinks = document.querySelectorAll(".nav-link");

    if (!navToggle || !navMenu) return;

    function openNav() {
      navMenu.classList.add("active");
      navToggle.setAttribute("aria-expanded", "true");
    }

    function closeNav() {
      navMenu.classList.remove("active");
      navToggle.setAttribute("aria-expanded", "false");
    }

    navToggle.addEventListener("click", function (e) {
      e.stopPropagation();
      var isExpanded = navToggle.getAttribute("aria-expanded") === "true";
      if (isExpanded) {
        closeNav();
      } else {
        openNav();
      }
    });

    // Close when clicking any nav link
    navLinks.forEach(function (link) {
      link.addEventListener("click", function () {
        closeNav();
      });
    });

    // Close when clicking outside menu
    document.addEventListener("click", function (e) {
      if (!navMenu.contains(e.target) && !navToggle.contains(e.target)) {
        closeNav();
      }
    });

    // Close on ESC key
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && navMenu.classList.contains("active")) {
        closeNav();
      }
    });

    // Auto-close on resize to desktop breakpoint (>768px)
    window.addEventListener("resize", function () {
      if (window.innerWidth > 768 && navMenu.classList.contains("active")) {
        closeNav();
      }
    }, { passive: true });
  }

  // ----------------------------------------------------------------------------
  // 3. Floating Navigation Bar Controller
  // ----------------------------------------------------------------------------
  var updateFloatingNavState = function () {};

  function initFloatingNav() {
    var navbar = document.querySelector(".navbar");
    if (!navbar) return;

    var isFloating = false;

    updateFloatingNavState = function () {
      var scrollY = window.pageYOffset || window.scrollY || document.documentElement.scrollTop || 0;
      var shouldFloat = scrollY > 20;

      if (shouldFloat !== isFloating) {
        isFloating = shouldFloat;
        if (isFloating) {
          navbar.classList.add("scrolled");
          navbar.classList.add("floating");
          navbar.classList.add("is-scrolled");
        } else {
          navbar.classList.remove("scrolled");
          navbar.classList.remove("floating");
          navbar.classList.remove("is-scrolled");
        }
      }
    };

    updateFloatingNavState();
  }

  // ----------------------------------------------------------------------------
  // 4. Smooth Anchor Navigation & Scroll Offsets
  // ----------------------------------------------------------------------------
  var navigatingTarget = null;
  var navigationClearTimer = null;
  var targetScrollY = 0;
  var determineActiveSectionRef = null;
  var cancelNavLock = null;

  function setActiveNavLink(sectionId) {
    var navLinks = document.querySelectorAll(".nav-menu .nav-link");
    var activeId = sectionId === "top" ? "about" : sectionId;
    navLinks.forEach(function (link) {
      var href = link.getAttribute("href");
      if (href === "#" + activeId) {
        link.classList.add("active");
        link.setAttribute("aria-current", "page");
      } else {
        link.classList.remove("active");
        link.removeAttribute("aria-current");
      }
    });
  }

  function scrollToSection(targetId, updateHistory) {
    var navbar = document.querySelector(".navbar");
    var targetEl = document.getElementById(targetId);
    if (!targetEl && targetId !== "top") return;

    var navHeight = navbar ? navbar.offsetHeight : 72;
    var offsetPosition = 0;

    if (targetId !== "top" && targetEl) {
      var elementPosition = targetEl.getBoundingClientRect().top;
      var currentScroll = window.pageYOffset || document.documentElement.scrollTop || 0;
      offsetPosition = elementPosition + currentScroll - (navHeight + 16);
      if (targetId === "about" && offsetPosition < 120) {
        offsetPosition = 0;
      }
    }

    var effectiveActiveId = targetId === "top" ? "about" : targetId;
    setActiveNavLink(effectiveActiveId);

    var currentY = window.pageYOffset || document.documentElement.scrollTop || 0;
    var docHeight = document.documentElement.scrollHeight;
    var winHeight = window.innerHeight;
    var maxScroll = Math.max(0, docHeight - winHeight);
    var clampedTarget = Math.max(0, Math.min(maxScroll, offsetPosition));

    var prefersReducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (navigationClearTimer) {
      clearTimeout(navigationClearTimer);
      navigationClearTimer = null;
    }

    if (prefersReducedMotion || Math.abs(currentY - clampedTarget) < 2) {
      navigatingTarget = null;
      window.scrollTo({
        top: clampedTarget,
        behavior: "auto"
      });
    } else {
      navigatingTarget = effectiveActiveId;
      targetScrollY = clampedTarget;

      // Failsafe timer: release lock after 2500ms max
      navigationClearTimer = setTimeout(function () {
        if (navigatingTarget) {
          navigatingTarget = null;
          if (typeof determineActiveSectionRef === "function") {
            determineActiveSectionRef();
          }
        }
      }, 2500);

      window.scrollTo({
        top: clampedTarget,
        behavior: "smooth"
      });
    }

    if (updateHistory && window.history && window.history.pushState) {
      window.history.pushState(null, null, "#" + targetId);
    }

    if (targetEl && targetId !== "top") {
      targetEl.setAttribute("tabindex", "-1");
      try {
        targetEl.focus({ preventScroll: true });
      } catch (err) {}
    }
  }

  function initSmoothNav() {
    var anchorLinks = document.querySelectorAll('a[href^="#"]');

    anchorLinks.forEach(function (link) {
      link.addEventListener("click", function (e) {
        var href = link.getAttribute("href");
        if (!href || href === "#") return;

        var targetId = href.slice(1);
        if (!targetId) return;

        e.preventDefault();

        // Close mobile nav drawer if open
        var navMenu = document.getElementById("nav-menu");
        var navToggle = document.getElementById("nav-toggle");
        if (navMenu && navMenu.classList.contains("active")) {
          navMenu.classList.remove("active");
          if (navToggle) {
            navToggle.setAttribute("aria-expanded", "false");
          }
        }

        scrollToSection(targetId, true);
      });
    });

    // Handle browser back/forward history navigation
    window.addEventListener("popstate", function () {
      var hash = window.location.hash;
      if (hash && hash.length > 1) {
        var targetId = hash.slice(1);
        scrollToSection(targetId, false);
      } else {
        scrollToSection("top", false);
      }
    });

    // Reset navigating lock on explicit user intervention or scroll completion
    cancelNavLock = function () {
      if (navigatingTarget) {
        navigatingTarget = null;
        if (navigationClearTimer) {
          clearTimeout(navigationClearTimer);
          navigationClearTimer = null;
        }
        if (typeof determineActiveSectionRef === "function") {
          determineActiveSectionRef();
        }
      }
    };

    window.addEventListener("wheel", cancelNavLock, { passive: true });
    window.addEventListener("touchstart", cancelNavLock, { passive: true });
    window.addEventListener("pointerdown", cancelNavLock, { passive: true });
    window.addEventListener("scrollend", cancelNavLock, { passive: true });

    window.addEventListener("keydown", function (e) {
      var scrollKeys = ["ArrowUp", "ArrowDown", "PageUp", "PageDown", "Home", "End", " "];
      if (scrollKeys.indexOf(e.key) !== -1) {
        cancelNavLock();
      }
    }, { passive: true });
  }

  // ----------------------------------------------------------------------------
  // 5. Active Nav Link on Scroll
  // ----------------------------------------------------------------------------
  function initActiveNavLinks() {
    var sections = Array.prototype.slice.call(document.querySelectorAll("section[id]"));
    var navLinks = document.querySelectorAll(".nav-menu .nav-link");
    var navbar = document.querySelector(".navbar");

    if (!sections.length || !navLinks.length) return;

    var ticking = false;
    var scrollSettledTimer = null;

    function determineActiveSection() {
      var scrollY = window.pageYOffset || window.scrollY || document.documentElement.scrollTop || 0;
      var windowHeight = window.innerHeight;
      var docHeight = document.documentElement.scrollHeight;
      var navHeight = navbar ? navbar.offsetHeight : 72;
      var atBottom = (docHeight - (windowHeight + scrollY)) <= 2;
      var atTargetY = Math.abs(scrollY - targetScrollY) <= 3;

      // If user clicked a navigation item and scroll animation is active, respect user's selection
      if (navigatingTarget) {
        var activeEl = document.getElementById(navigatingTarget);
        if (activeEl) {
          var rectActive = activeEl.getBoundingClientRect();
          var expectedTop = (navigatingTarget === "about") ? navHeight : (navHeight + 16);
          var arrived = atTargetY || atBottom || Math.abs(rectActive.top - expectedTop) <= 20;
          if (arrived) {
            navigatingTarget = null;
            if (navigationClearTimer) {
              clearTimeout(navigationClearTimer);
              navigationClearTimer = null;
            }
            setActiveNavLink(activeEl.getAttribute("id"));
            return;
          }
          return;
        }
        navigatingTarget = null;
      }

      // 1. Edge Case: Near top of page
      if (scrollY < 100) {
        setActiveNavLink("about");
        return;
      }

      // 2. Edge Case: Bottom of page or last section clearly visible near bottom
      var lastSection = sections[sections.length - 1];
      if (lastSection) {
        var lastRect = lastSection.getBoundingClientRect();
        var distanceFromBottom = docHeight - (windowHeight + scrollY);
        if (distanceFromBottom <= 250 || (lastRect.top <= navHeight + 100 && lastRect.bottom >= navHeight)) {
          setActiveNavLink(lastSection.getAttribute("id"));
          return;
        }
      }

      // 3. Focal zone detection: reading zone just below navbar
      var focalPoint = navHeight + Math.min(160, Math.floor(windowHeight * 0.25));
      for (var i = 0; i < sections.length; i++) {
        var section = sections[i];
        var rect = section.getBoundingClientRect();
        if (rect.top <= focalPoint && rect.bottom > focalPoint) {
          setActiveNavLink(section.getAttribute("id"));
          return;
        }
      }

      // 4. Fallback: Find section with greatest visible area in viewport
      var maxVisible = 0;
      var bestId = "";
      for (var j = 0; j < sections.length; j++) {
        var s = sections[j];
        var r = s.getBoundingClientRect();
        var visibleTop = Math.max(navHeight, r.top);
        var visibleBottom = Math.min(windowHeight, r.bottom);
        var visibleHeight = Math.max(0, visibleBottom - visibleTop);
        if (visibleHeight > maxVisible) {
          maxVisible = visibleHeight;
          bestId = s.getAttribute("id");
        }
      }
      if (bestId) {
        setActiveNavLink(bestId);
      }
    }

    determineActiveSectionRef = determineActiveSection;

    function onScroll() {
      // Release navigating lock if scrolling settles for > 120ms
      if (navigatingTarget) {
        if (scrollSettledTimer) clearTimeout(scrollSettledTimer);
        scrollSettledTimer = setTimeout(function () {
          if (navigatingTarget) {
            cancelNavLock();
          }
        }, 120);
      }

      if (!ticking) {
        window.requestAnimationFrame(function () {
          try {
            updateFloatingNavState();
            determineActiveSection();
            updateBackToTopState();
          } finally {
            ticking = false;
          }
        });
        ticking = true;
      }
    }

    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });

    // Initial check on load
    determineActiveSection();
  }

  // ----------------------------------------------------------------------------
  // 4. Publications Filtering & Search
  // ----------------------------------------------------------------------------
  function initPublicationFilters() {
    var filterPills = document.querySelectorAll(".pub-pill");
    var searchInput = document.getElementById("pub-search");
    var pubCards = document.querySelectorAll(".publication-card");
    var emptyState = document.getElementById("pub-empty-state");

    if (!pubCards.length) return;

    var currentCategory = "all";
    var currentQuery = "";

    function applyFilters() {
      var visibleCount = 0;
      var queryLower = currentQuery.trim().toLowerCase();

      pubCards.forEach(function (card) {
        var cardCategory = (card.getAttribute("data-category") || "").toLowerCase();
        var cardContent = (card.textContent || "").toLowerCase();

        var matchesCategory = currentCategory === "all" || cardCategory === currentCategory;
        var matchesQuery = !queryLower || cardContent.indexOf(queryLower) !== -1;

        if (matchesCategory && matchesQuery) {
          card.style.display = "flex";
          visibleCount++;
        } else {
          card.style.display = "none";
        }
      });

      if (emptyState) {
        emptyState.style.display = visibleCount === 0 ? "block" : "none";
      }
    }

    filterPills.forEach(function (pill) {
      pill.addEventListener("click", function () {
        filterPills.forEach(function (p) { p.classList.remove("active"); });
        pill.classList.add("active");
        currentCategory = (pill.getAttribute("data-filter") || "all").toLowerCase();
        applyFilters();
      });
    });

    if (searchInput) {
      searchInput.addEventListener("input", function (e) {
        currentQuery = e.target.value;
        applyFilters();
      });
    }
  }

  // ----------------------------------------------------------------------------
  // 5. Email Copy-to-Clipboard & Toast Feedback
  // ----------------------------------------------------------------------------
  function showToast(message) {
    var toast = document.getElementById("toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "toast";
      toast.className = "toast";
      document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.classList.add("show");

    setTimeout(function () {
      toast.classList.remove("show");
    }, 2800);
  }

  function initEmailCopy() {
    var copyButtons = document.querySelectorAll(".copy-email-btn");

    copyButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var email = btn.getAttribute("data-email");
        if (!email) return;

        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(email).then(function () {
            showToast("Copied " + email + " to clipboard!");
          }).catch(function () {
            fallbackCopy(email);
          });
        } else {
          fallbackCopy(email);
        }
      });
    });

    function fallbackCopy(text) {
      var textArea = document.createElement("textarea");
      textArea.value = text;
      textArea.style.position = "fixed";
      textArea.style.opacity = "0";
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand("copy");
        showToast("Copied " + text + " to clipboard!");
      } catch (err) {
        showToast("Press Ctrl+C to copy: " + text);
      }
      document.body.removeChild(textArea);
    }
  }

  // ----------------------------------------------------------------------------
  // 6. Interactive BibTeX Modal
  // ----------------------------------------------------------------------------
  function initBibtexModal() {
    var bibtexModal = document.getElementById("bibtex-modal");
    var bibtexCode = document.getElementById("bibtex-code");
    var closeBtn = document.getElementById("bibtex-modal-close");
    var copyBtn = document.getElementById("bibtex-copy-btn");
    var triggerButtons = document.querySelectorAll(".btn-bibtex");

    if (!bibtexModal || !bibtexCode) return;

    function openModal(bibtexString) {
      bibtexCode.textContent = bibtexString;
      bibtexModal.classList.add("active");
      bibtexModal.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
    }

    function closeModal() {
      bibtexModal.classList.remove("active");
      bibtexModal.setAttribute("aria-hidden", "true");
      document.body.style.overflow = "";
    }

    triggerButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var bibtex = btn.getAttribute("data-bibtex") || "";
        openModal(bibtex);
      });
    });

    if (closeBtn) {
      closeBtn.addEventListener("click", closeModal);
    }

    bibtexModal.addEventListener("click", function (e) {
      if (e.target === bibtexModal) {
        closeModal();
      }
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && bibtexModal.classList.contains("active")) {
        closeModal();
      }
    });

    if (copyBtn) {
      copyBtn.addEventListener("click", function () {
        var text = bibtexCode.textContent;
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(function () {
            showToast("BibTeX citation copied to clipboard!");
          });
        }
      });
    }
  }

  // ----------------------------------------------------------------------------
  // 7. Volunteer Photo Gallery Lightbox
  // ----------------------------------------------------------------------------
  function initVolunteerLightbox() {
    var lightboxModal = document.getElementById("lightbox-modal");
    var lightboxImg = document.getElementById("lightbox-img");
    var lightboxCaption = document.getElementById("lightbox-caption");
    var closeBtn = document.getElementById("lightbox-close");
    var galleryCards = document.querySelectorAll(".volunteer-photo-card");

    if (!lightboxModal || !lightboxImg) return;

    function openLightbox(src, alt) {
      lightboxImg.src = src;
      lightboxImg.alt = alt;
      if (lightboxCaption) {
        lightboxCaption.textContent = alt;
      }
      lightboxModal.classList.add("active");
      lightboxModal.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
    }

    function closeLightbox() {
      lightboxModal.classList.remove("active");
      lightboxModal.setAttribute("aria-hidden", "true");
      lightboxImg.src = "";
      document.body.style.overflow = "";
    }

    galleryCards.forEach(function (card) {
      card.addEventListener("click", function () {
        var img = card.querySelector("img");
        if (img) {
          openLightbox(img.getAttribute("src"), img.getAttribute("alt") || "Volunteer Photo");
        }
      });
    });

    if (closeBtn) {
      closeBtn.addEventListener("click", closeLightbox);
    }

    lightboxModal.addEventListener("click", function (e) {
      if (e.target === lightboxModal || e.target.classList.contains("lightbox-modal-content")) {
        closeLightbox();
      }
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && lightboxModal.classList.contains("active")) {
        closeLightbox();
      }
    });
  }

  // ----------------------------------------------------------------------------
  // 8. Back to Top Button
  // ----------------------------------------------------------------------------
  var updateBackToTopState = function () {};

  function initBackToTop() {
    var backToTopBtn = document.getElementById("back-to-top");
    if (!backToTopBtn) return;

    updateBackToTopState = function () {
      var scrollY = window.pageYOffset || window.scrollY || document.documentElement.scrollTop || 0;
      if (scrollY > 350) {
        backToTopBtn.classList.add("visible");
      } else {
        backToTopBtn.classList.remove("visible");
      }
    };

    backToTopBtn.addEventListener("click", function (e) {
      e.preventDefault();
      scrollToSection("about", true);
    });

    updateBackToTopState();
  }

  // ----------------------------------------------------------------------------
  // 9. YouTube Playlist Cover Switcher
  // ----------------------------------------------------------------------------
  function initYouTubeCoverSwitcher() {
    var player = document.getElementById("youtube-player");
    var buttons = document.querySelectorAll(".yt-cover-btn");
    if (!player || !buttons.length) return;

    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var vid = btn.getAttribute("data-vid");
        if (!vid) return;

        buttons.forEach(function (b) {
          b.classList.remove("active");
        });
        btn.classList.add("active");

        var newSrc = "https://www.youtube-nocookie.com/embed/" + vid + "?autoplay=1";
        player.setAttribute("src", newSrc);
      });
    });
  }

  // ----------------------------------------------------------------------------
  // Google Scholar Client-side Cache Hydration (Decoupled Architecture)
  // ----------------------------------------------------------------------------
  function initScholarDataHydration() {
    if (!window.fetch) return;
    fetch('assets/data/gs_data.json')
      .then(function (response) {
        if (!response.ok) return null;
        return response.json();
      })
      .then(function (data) {
        if (!data || !data.metrics) return;
        var m = data.metrics;
        var cElem = document.getElementById('metric-citations');
        var hElem = document.getElementById('metric-hindex');
        var iElem = document.getElementById('metric-i10index');
        var pElem = document.getElementById('metric-pubs');
        if (cElem && m.citations != null) cElem.textContent = m.citations;
        if (hElem && m.h_index != null) hElem.textContent = m.h_index;
        if (iElem && m.i10_index != null) iElem.textContent = m.i10_index;
        if (pElem && m.total_publications != null) pElem.textContent = m.total_publications;
      })
      .catch(function () {
        // Silent fallback to pre-rendered HTML values
      });
  }

})();