// Named feature events for PostHog. Loads on every page; track() does nothing unless posthog.js
// initialised PostHog, which it only does on the production hostname.
// Events whose outcome is decided on the server (deck, theme, image) arrive through the
// 'analytics-event' store in callbacks.py; dashboard events come from clientside callbacks there;
// the slide lightbox reports from lightbox.js. This file covers what only the browser sees:
//   press_article_opened   links tagged data-track="press_article_opened" (home page press list)
//   outbound_link_clicked  any other link to another site (LinkedIn, GitHub, nickearl.net, ...)
//   ai_agent_call_started  the ElevenLabs widget fires 'elevenlabs-convai:call' when a call starts
//   dashboard_tab_viewed   clicks on a dashboard tab that isn't already active (the component sets its
//                          own first tab on load, so a callback on active_tab would count non-visits)
(function () {
    function track(event, props) {
        if (window.posthog && window.posthog.capture) window.posthog.capture(event, props || {});
    }
    window.portfolioTrack = track;

    document.addEventListener('click', function (e) {
        // Capture phase runs before React re-renders, so 'active' still marks the previous tab
        var tab = e.target.closest && e.target.closest('#tabs-container .nav-link');
        if (tab) {
            if (!tab.classList.contains('active')) track('dashboard_tab_viewed', { tab: tab.textContent.trim() });
            return;
        }
        var link = e.target.closest && e.target.closest('a[href]');
        if (!link) return;
        if (link.dataset.track) {
            var props = {};
            try { props = JSON.parse(link.dataset.trackProps || '{}'); } catch (err) { /* keep {} */ }
            track(link.dataset.track, props);
            return;
        }
        var url;
        try { url = new URL(link.href, window.location.href); } catch (err) { return; }
        if (url.hostname && url.hostname !== window.location.hostname) {
            track('outbound_link_clicked', {
                destination: url.hostname.replace(/^www\./, ''),
                url: url.href,
                text: (link.textContent || '').trim().slice(0, 80),
            });
        }
    }, true);

    // Agent widgets live in srcdoc iframes (same origin), which load when their tab is shown.
    // 'load' doesn't bubble, so listen in the capture phase.
    document.addEventListener('load', function (e) {
        var frame = e.target;
        if (!frame || frame.tagName !== 'IFRAME' || !frame.dataset.agent) return;
        var doc;
        try { doc = frame.contentDocument; } catch (err) { return; }
        if (!doc || doc.portfolioTracked) return;
        doc.portfolioTracked = true;
        doc.addEventListener('elevenlabs-convai:call', function () {
            track('ai_agent_call_started', { agent: frame.dataset.agent });
        });
    }, true);
})();
