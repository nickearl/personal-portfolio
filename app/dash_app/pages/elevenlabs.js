document.addEventListener('DOMContentLoaded', function() {
    const script = document.createElement('script');
    script.src = "https://unpkg.com/@elevenlabs/convai-widget-embed";
    script.async = true;
    script.type = "text/javascript";
    document.head.appendChild(script);

    const elem = document.createElement('elevenlabs-convai');
    elem.setAttribute('agent-id', 'agent_7701kha7yzdzew5v1da6tmx3mw4s');
    document.body.appendChild(elem);
});