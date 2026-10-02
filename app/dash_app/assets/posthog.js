// PostHog web analytics (Dash loads every .js file in assets/ on all pages).
// Pageviews (including Dash's in-app page changes) and page leaves, plus the named feature events in
// analytics.js. Raw click autocapture, session replay, heatmaps, web vitals and surveys are off here,
// which overrides the project's settings. persistence 'memory' sets no cookies or local storage, so no
// consent banner is needed; a full page reload counts as a new visitor. The project key is public by design.
(function () {
    var POSTHOG_KEY = 'phc_oR4CVu23N3x93JWYhevazEsyP4NihZwG5Pbggvt2LwPq';  // PostHog org "Portfolio", project "Portfolio" (642218)
    var POSTHOG_HOST = 'https://us.i.posthog.com';
    if (!POSTHOG_KEY || window.location.hostname !== 'portfolio.nickearl.net') return;

    // Official loader snippet (posthog.com/docs/libraries/js)
    !function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.crossOrigin="anonymous",p.async=!0,p.src=s.api_host.replace(".i.posthog.com","-assets.i.posthog.com")+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],Object.defineProperty(u,"toString",{configurable:!0,enumerable:!0,writable:!0,value:function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e}}),Object.defineProperty(u.people,"toString",{configurable:!0,enumerable:!0,writable:!0,value:function(){return u.toString(1)+".people (stub)"}}),o="init capture register register_once register_for_session unregister unregister_for_session getFeatureFlag getFeatureFlagResult isFeatureEnabled reloadFeatureFlags updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures on onFeatureFlags onSessionId getSurveys getActiveMatchingSurveys renderSurvey canRenderSurvey getNextSurveyStep identify setPersonProperties group resetGroups setPersonPropertiesForFlags resetPersonPropertiesForFlags setGroupPropertiesForFlags resetGroupPropertiesForFlags reset get_distinct_id getGroups get_session_id get_session_replay_url alias set_config startSessionRecording stopSessionRecording sessionRecordingStarted captureException loadToolbar get_property getSessionProperty createPersonProfile opt_in_capturing opt_out_capturing has_opted_in_capturing has_opted_out_capturing clear_opt_in_out_capturing debug".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);

    posthog.init(POSTHOG_KEY, {
        api_host: POSTHOG_HOST,
        defaults: '2026-05-30',          // includes history-based pageviews for single-page apps
        persistence: 'memory',
        person_profiles: 'identified_only',
        autocapture: false,
        disable_session_recording: true,
        enable_heatmaps: false,
        capture_dead_clicks: false,
        capture_performance: false,
        disable_surveys: true,
    });
})();
