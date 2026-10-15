// Ejecuta los controles reales de la página con un reproductor simulado, sin Internet.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const elements = {};
function element(id) {
  return elements[id] ||= {
    value: 0, max: 0, disabled: true, textContent: '', className: '', handlers: {},
    addEventListener(type, callback) { this.handlers[type] = callback; },
    fire(type) { this.handlers[type](); },
  };
}
let duration = 200, current = 23, state = 2, plays = 0, pauses = 0;
const seeks = [], notifications = [], intervals = new Map(), lifecycle = {};
let timerId = 0;
const context = {
  document: {getElementById: element, createElement: () => ({}), head: {appendChild() {}}},
  window: {addEventListener(type, callback) { lifecycle[type] = callback; }},
  setTimeout() {}, setInterval(callback) { intervals.set(++timerId, callback); return timerId; },
  clearInterval(id) { intervals.delete(id); },
  fetch(url, data) { notifications.push(JSON.parse(data.body)); return Promise.resolve(); },
  YT: {Player: function(id, options) {
    this.options = options;
    this.getDuration = () => duration;
    this.getCurrentTime = () => current;
    this.getPlayerState = () => state;
    this.seekTo = (seconds, ahead) => { seeks.push([seconds, ahead]); current = seconds; };
    this.playVideo = () => { plays++; state = 1; };
    this.pauseVideo = () => { pauses++; state = 2; };
  }},
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(0, 'utf8'), context);
assert.equal(element('seek').disabled, true);
context.onYouTubeIframeAPIReady();
context.window.previewPlayer.options.events.onReady();
assert.equal(element('seek').disabled, false);
assert.equal(element('elapsed').textContent, '0:23');
assert.equal(element('duration').textContent, '3:20');

element('seek').value = '75.5';
element('seek').fire('input');
assert.equal(seeks.length, 0, 'Arrastrar no debe pedir nuevos fragmentos de video');
current = 24;
for (const callback of intervals.values()) callback();
assert.equal(element('seek').value, '75.5', 'El temporizador no debe mover la barra mientras se arrastra');
assert.equal(element('elapsed').textContent, '1:15');
element('seek').fire('change');
assert.deepEqual(seeks.at(-1), [75.5, true]);
assert.equal(plays, 0, 'Adelantar en pausa no debe forzar la reproducción');
element('forward').fire('click');
assert.deepEqual(seeks.at(-1), [85.5, true]);
element('back').fire('click');
assert.deepEqual(seeks.at(-1), [75.5, true]);
context.seekToPosition(999);
assert.deepEqual(seeks.at(-1), [200, true]);
context.seekToPosition(-10);
assert.deepEqual(seeks.at(-1), [0, true]);
const count = seeks.length;
context.seekToPosition('no es un tiempo');
assert.equal(seeks.length, count);

element('toggle').fire('click');
assert.equal(plays, 1);
assert.equal(element('toggle').textContent, 'Pausar');
element('toggle').fire('click');
assert.equal(pauses, 1);
assert.equal(element('toggle').textContent, 'Reproducir');
duration = 0;
context.updateProgress();
assert.equal(element('seek').disabled, true);
assert.equal(element('forward').disabled, true);
assert.equal(element('duration').textContent, '--:--');
context.seekToPosition(10);
assert.equal(seeks.length, count);
duration = 3723; current = 3601;
context.updateProgress();
assert.equal(element('duration').textContent, '1:02:03');
assert.equal(element('elapsed').textContent, '1:00:01');
assert.equal(notifications.length, 1, 'Actualizar el tiempo no debe enviar peticiones de progreso');
context.failure(101);
for (const id of ['seek', 'toggle', 'back', 'forward']) assert.equal(element(id).disabled, true);
assert.match(element('status').textContent, /propietario/);
assert.equal(intervals.size, 0);
lifecycle.pagehide();
console.log('Controles de reproducción, desplazamiento y estados: correctos.');
