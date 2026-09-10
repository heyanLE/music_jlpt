# QA failure: legacy grammar field rendered

The candidate is not approved for delivery.

- The renderer displayed legacy `posZh` values such as `待语法审阅`.
- The accepted review content is stored in canonical `grammarStructureZh`.
- `render_video.py` has been corrected to prefer `grammarStructureZh` and use `posZh` only as a legacy fallback.
- A new explicit render authorization is required because the renderer hash changed.
