/* ULTRON Cloud PWA: strictly scoped Apple Shortcuts bridge.
   Pure helpers run in browser and in Node contract tests. Never start a
   model-suggested device-setting action without the user's foreground tap. */
(function (root) {
  'use strict';
  const BRIDGE_NAME = 'ULTRON Bridge';
  const ACTION_LABELS = Object.freeze({
    set_focus: 'Odak modunu değiştir',
    set_volume: 'Telefon sesini değiştir',
    set_brightness: 'Ekran parlaklığını değiştir',
    bluetooth: 'Bluetooth ayarını değiştir',
    wifi: 'Wi-Fi ayarını değiştir',
    compose_message: 'Mesaj oluştur'
  });

  function validateCommand(raw) {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
    if (raw.source !== 'ultron' || raw.version !== 1) return null;
    if (!Object.prototype.hasOwnProperty.call(ACTION_LABELS, raw.action)) return null;
    if (typeof raw.target !== 'string' || raw.target.length > 300) return null;
    if (typeof raw.value !== 'string' || raw.value.length > 1200) return null;
    if ((raw.action === 'set_brightness' || raw.action === 'set_volume') &&
        !/^(?:100|[1-9]?\d)$/.test(raw.value.trim())) return null;
    if ((raw.action === 'wifi' || raw.action === 'bluetooth') &&
        !['on', 'off'].includes(raw.value.trim().toLowerCase()) &&
        !['on', 'off'].includes(raw.target.trim().toLowerCase())) return null;
    // Reject arbitrary JSON keys, action URLs or chosen shortcut names.
    if (Object.keys(raw).some(k => !['version', 'source', 'action', 'target', 'value'].includes(k))) return null;
    return {
      version: 1, source: 'ultron', action: raw.action,
      target: raw.target, value: raw.value
    };
  }

  function fromLiveEvent(event) {
    if (!event || typeof event !== 'object') return null;
    if (event.type === 'ios_action') {
      const command = validateCommand(event.command);
      return command ? { command, label: ACTION_LABELS[command.action] } : null;
    }
    if (event.type === 'ios_shortcut') {
      if (event.shortcut_name !== BRIDGE_NAME ||
          typeof event.input !== 'string' || event.input.length > 2400) return null;
      let raw;
      try { raw = JSON.parse(event.input); } catch { return null; }
      const command = validateCommand(raw);
      return command ? { command, label: ACTION_LABELS[command.action] } : null;
    }
    return null;
  }

  function shortcutURL(command) {
    const valid = validateCommand(command);
    if (!valid) return null;
    const payload = JSON.stringify(valid);
    return 'shortcuts://run-shortcut?name=' + encodeURIComponent(BRIDGE_NAME) +
      '&input=text&text=' + encodeURIComponent(payload);
  }

  const api = Object.freeze({ BRIDGE_NAME, validateCommand, fromLiveEvent, shortcutURL });
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.ULTRONPhoneActionGuard = api;
})(typeof window !== 'undefined' ? window : globalThis);
