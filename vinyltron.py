#!/usr/bin/env python3
import logging
import signal
import sys
import time
from io import BytesIO
from typing import Dict, Optional

import requests
import toml
from PIL import Image

from display import Display
from volumio_client import VolumioClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler()]
)
logging.getLogger('socketio').setLevel(logging.WARNING)
logging.getLogger('engineio').setLevel(logging.WARNING)
log = logging.getLogger('vinyltron')


class Vinyltron:
    def __init__(self, config_path: str = 'config.toml'):
        self._config_path = config_path
        self._cfg = toml.load(config_path)
        self._display = Display(self._cfg)
        self._client = VolumioClient(
            host=self._cfg['volumio']['host'],
            port=self._cfg['volumio']['port'],
            on_state=self._on_state,
        )
        self._current_albumart: Optional[str] = None
        self._display_on: bool = True
        self._running = True
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGHUP, self._reload)

    def _on_state(self, state: Dict):
        if not self._display_on:
            return

        status = state.get('status', 'stop')
        albumart = state.get('albumart', '')

        if status not in ('play', 'pause'):
            log.info("Status: %s — showing fallback", status)
            self._display.show_fallback()
            self._current_albumart = None
            return

        if not albumart or albumart == self._current_albumart:
            return

        log.info("New track: %s — %s", state.get('artist'), state.get('title'))
        img = self._fetch_albumart(albumart)
        if img:
            self._display.show_image(img)
            self._current_albumart = albumart
        else:
            self._display.show_fallback()

    def _fetch_albumart(self, url: str) -> Optional[Image.Image]:
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            return Image.open(BytesIO(r.content)).convert('RGB')
        except Exception as e:
            log.warning("Failed to fetch albumart from %s: %s", url, e)
            return None

    def _shutdown(self, *_):
        log.info("Shutting down")
        self._running = False
        self._client.stop()
        self._display.clear()
        sys.exit(0)

    def _reload(self, *_):
        log.info("SIGHUP received — reloading config")
        try:
            self._cfg = toml.load(self._config_path)
            was_on = self._display_on
            self._display_on = self._cfg['display'].get('display_on', True)
            self._display.reconfigure(self._cfg)
            if not self._display_on:
                self._display.clear()
                log.info("Display off")
            elif not was_on:
                self._current_albumart = None  # force re-fetch on next state
                self._client.request_state()
                log.info("Display on")
            else:
                log.info("Config reloaded")
        except Exception as e:
            log.warning("Config reload failed: %s", e)

    def run(self):
        self._display.show_fallback()
        self._client.start()
        log.info("Vinyltron running")
        while self._running:
            time.sleep(1)


if __name__ == '__main__':
    config = sys.argv[1] if len(sys.argv) > 1 else 'config.toml'
    Vinyltron(config).run()
