(function() {
    const STORAGE_KEY = 'blog-player-state-v1';
    let saveTimer = null;
    let restoredForPage = false;
    let initializedForPage = false;

    function getPlayerElement() {
        return document.querySelector('.blog-live2d-player .aplayer') || document.querySelector('.blog-live2d-player');
    }

    function getTrackId() {
        const player = getPlayer();
        const audio = player && player.list && player.list.audios ? player.list.audios[player.list.index] : null;
        if (audio && audio.url) {
            return audio.url;
        }
        const el = getPlayerElement();
        return el ? el.dataset.id || '' : '';
    }

    function getPlayer() {
        return window.aplayers && window.aplayers.length ? window.aplayers[0] : null;
    }

    function initPlaylistPlayer() {
        if (initializedForPage) {
            return;
        }

        const container = getPlayerElement();
        const playlist = window.__blogPlayerPlaylist;
        if (!container || !playlist || typeof window.APlayer !== 'function') {
            return;
        }

        if (window.aplayers && window.aplayers.length) {
            initializedForPage = true;
            return;
        }

        const player = new window.APlayer({
            container,
            fixed: true,
            mini: true,
            autoplay: !!playlist.autoplay,
            mutex: !!playlist.mutex,
            theme: playlist.theme,
            listFolded: !!playlist.listFolded,
            listMaxHeight: playlist.listMaxHeight,
            audio: playlist.audio
        });

        window.aplayers = window.aplayers || [];
        window.aplayers.push(player);
        initializedForPage = true;
    }

    function saveState() {
        const player = getPlayer();
        if (!player || !player.audio) {
            return;
        }

        const payload = {
            id: getTrackId(),
            time: player.audio.currentTime || 0,
            paused: player.audio.paused
        };

        try {
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
        } catch (e) {
            console.warn('player state save failed', e);
        }
    }

    function readState() {
        try {
            const raw = sessionStorage.getItem(STORAGE_KEY);
            return raw ? JSON.parse(raw) : null;
        } catch (e) {
            console.warn('player state read failed', e);
            return null;
        }
    }

    function restoreState() {
        if (restoredForPage) {
            return;
        }

        const saved = readState();
        const player = getPlayer();
        if (!saved || !player || !player.audio) {
            return;
        }
        if (saved.id && saved.id !== getTrackId()) {
            return;
        }

        const resume = function() {
            try {
                if (saved.time > 0) {
                    player.audio.currentTime = saved.time;
                }
            } catch (e) {
                console.warn('player seek failed', e);
            }

            if (saved.paused === false) {
                const result = player.play ? player.play() : player.audio.play();
                if (result && typeof result.catch === 'function') {
                    result.catch(() => {});
                }
            }

            restoredForPage = true;
        };

        if (player.audio.readyState >= 1) {
            resume();
        } else {
            player.audio.addEventListener('loadedmetadata', resume, { once: true });
        }
    }

    function waitForPlayerAndRestore() {
        let attempts = 0;
        const timer = window.setInterval(function() {
            attempts += 1;
            if (getPlayer()) {
                window.clearInterval(timer);
                restoreState();
            } else if (attempts > 100) {
                window.clearInterval(timer);
            }
        }, 200);
    }

    function initPersistence() {
        restoredForPage = false;
        initializedForPage = false;
        initPlaylistPlayer();
        waitForPlayerAndRestore();

        if (saveTimer) {
            window.clearInterval(saveTimer);
        }
        saveTimer = window.setInterval(saveState, 1000);
    }

    document.addEventListener('DOMContentLoaded', initPersistence);
    document.addEventListener('pjax:send', saveState);
    document.addEventListener('pjax:complete', initPersistence);
    window.addEventListener('beforeunload', saveState);
})();
