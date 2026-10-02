// Click-to-enlarge for deck slides (img.deck-slide). Opens an overlay with the slide, its title and an
// "n / N" counter. Prev/next buttons, arrow keys and swipes move through the deck; the close button, Esc
// or a backdrop click close it. Lives outside Dash's React tree, so re-renders never touch it.
(function () {
    var overlay, img, caption, counter, prevBtn, nextBtn, closeBtn;
    var deck = null, index = 0, lastFocus = null, touchX = null;

    function build() {
        overlay = document.createElement('div');
        overlay.className = 'lightbox';
        overlay.setAttribute('role', 'dialog');
        overlay.setAttribute('aria-modal', 'true');
        overlay.setAttribute('aria-label', 'Slide viewer');
        overlay.innerHTML =
            '<button type="button" class="lightbox-btn lightbox-close" aria-label="Close">&times;</button>' +
            '<button type="button" class="lightbox-btn lightbox-prev" aria-label="Previous slide">&#8249;</button>' +
            '<figure class="lightbox-figure"><img class="lightbox-img" alt="">' +
            '<figcaption><span class="lightbox-caption"></span><span class="lightbox-counter"></span></figcaption></figure>' +
            '<button type="button" class="lightbox-btn lightbox-next" aria-label="Next slide">&#8250;</button>';
        document.body.appendChild(overlay);
        img = overlay.querySelector('.lightbox-img');
        caption = overlay.querySelector('.lightbox-caption');
        counter = overlay.querySelector('.lightbox-counter');
        prevBtn = overlay.querySelector('.lightbox-prev');
        nextBtn = overlay.querySelector('.lightbox-next');
        closeBtn = overlay.querySelector('.lightbox-close');

        closeBtn.addEventListener('click', close);
        prevBtn.addEventListener('click', function () { show(index - 1); });
        nextBtn.addEventListener('click', function () { show(index + 1); });
        overlay.addEventListener('click', function (e) {
            if (e.target === overlay || e.target.classList.contains('lightbox-figure')) close();
        });
        overlay.addEventListener('touchstart', function (e) { touchX = e.touches[0].clientX; }, { passive: true });
        overlay.addEventListener('touchend', function (e) {
            if (touchX === null) return;
            var dx = e.changedTouches[0].clientX - touchX;
            touchX = null;
            if (Math.abs(dx) > 50) show(dx < 0 ? index + 1 : index - 1);
        });
    }

    // Re-read the deck each time: slides of a generated deck keep arriving after the viewer opens
    function slides() {
        return Array.prototype.slice.call((deck || document).querySelectorAll('img.deck-slide'));
    }

    function show(n) {
        var list = slides();
        if (!list.length) return close();
        index = (n + list.length) % list.length;
        img.src = list[index].src;
        img.alt = list[index].alt;
        caption.textContent = list[index].alt;
        counter.textContent = list.length > 1 ? (index + 1) + ' / ' + list.length : '';
        prevBtn.hidden = nextBtn.hidden = list.length < 2;
    }

    function open(slide) {
        if (!overlay) build();
        deck = slide.closest('.deck-grid');
        lastFocus = document.activeElement;
        show(slides().indexOf(slide));
        if (window.portfolioTrack) {
            // generated slides sit in render slots whose ids carry "sales-slide"; the example deck doesn't
            window.portfolioTrack('deck_slide_enlarged', {
                deck: slide.closest('[id*="sales-slide"]') ? 'generated' : 'example',
                slide: index + 1,
            });
        }
        overlay.classList.add('open');
        document.body.classList.add('lightbox-lock');
        closeBtn.focus();
    }

    function close() {
        overlay.classList.remove('open');
        document.body.classList.remove('lightbox-lock');
        img.removeAttribute('src');
        if (lastFocus && document.contains(lastFocus)) lastFocus.focus();
    }

    function isOpen() {
        return overlay && overlay.classList.contains('open');
    }

    document.addEventListener('click', function (e) {
        var slide = e.target.closest && e.target.closest('img.deck-slide');
        if (slide) open(slide);
    });

    document.addEventListener('keydown', function (e) {
        if (isOpen()) {
            if (e.key === 'Escape') { e.preventDefault(); close(); }
            else if (e.key === 'ArrowLeft') { e.preventDefault(); show(index - 1); }
            else if (e.key === 'ArrowRight') { e.preventDefault(); show(index + 1); }
            else if (e.key === 'Tab') {
                // keep focus inside the dialog
                var buttons = Array.prototype.filter.call(overlay.querySelectorAll('button'), function (b) { return !b.hidden; });
                var at = buttons.indexOf(document.activeElement);
                e.preventDefault();
                buttons[(at + (e.shiftKey ? -1 : 1) + buttons.length) % buttons.length].focus();
            }
            return;
        }
        if ((e.key === 'Enter' || e.key === ' ') && e.target.matches && e.target.matches('img.deck-slide')) {
            e.preventDefault();
            open(e.target);
        }
    });
})();
