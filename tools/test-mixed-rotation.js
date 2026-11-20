'use strict';
// Exercise the real controller against in-memory Volumio config/filesystem boundaries.
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const root = path.resolve(__dirname, '..');
let toml = fs.readFileSync(path.join(root, 'config.toml'), 'utf8');
const values = {};
const defaults = JSON.parse(fs.readFileSync(path.join(root, 'plugin/config.json'), 'utf8'));
Object.keys(defaults).forEach(key => { values[key] = defaults[key].value; });
const filesystem = {
    readFileSync: () => toml,
    writeFileSync: (_path, content) => { toml = content; },
    readJsonSync: filename => JSON.parse(fs.readFileSync(filename, 'utf8')),
    readdirSync: () => []
};
const kew = {
    resolve: Promise.resolve.bind(Promise),
    defer: () => {
        let resolve, reject;
        const promise = new Promise((a, b) => { resolve = a; reject = b; });
        return {promise, resolve, reject};
    }
};
const sandbox = {
    module: {exports: {}}, __dirname: path.join(root, 'plugin'),
    require: name => name === 'fs-extra' ? filesystem : name === 'kew' ? kew : require(name)
};
vm.runInNewContext(fs.readFileSync(path.join(root, 'plugin/index.js'), 'utf8'), sandbox);
const Controller = sandbox.module.exports;
const controller = new Controller({coreCommand: {}, logger: {info() {}, error(message) { throw Error(message); }}});
controller.config = {get: key => values[key], set: (key, value) => { values[key] = value; }};
let reloads = 0;
controller._service = action => { assert.equal(action, 'reload'); reloads++; };

(async () => {
    controller.saveRotation({rotation_photos: false, rotation_screensavers: {value: true},
        rotation_weather: 'false', rotation_album_art: true,
        rotation_slot_seconds: {value: '23'}, rotation_order: {value: 'sequential'}});
    assert.equal(reloads, 1);
    assert.equal(controller._tomlValue(toml, 'rotation', 'photos'), 'false');
    assert.equal(controller._tomlValue(toml, 'rotation', 'screensavers'), 'true');
    assert.equal(controller._tomlValue(toml, 'rotation', 'slot_seconds'), '23');
    assert.equal(controller._tomlValue(toml, 'rotation', 'order'), '"sequential"');
    // Read back from TOML rather than leaving values from the save in memory.
    values.rotation_slot_seconds = 999;
    controller._syncVConfFromToml();
    assert.equal(values.rotation_slot_seconds, 23);
    assert.equal(values.rotation_photos, false);
    const ui = await controller.getUIConfig();
    const rotation = ui.sections.find(section => section.id === 'section_rotation');
    assert.equal(rotation.content[0].value, false);
    assert.equal(rotation.content[1].value, true);
    assert.equal(rotation.content[4].value, '23');
    assert.equal(rotation.content[5].value.value, 'sequential');
    assert.equal(controller._validRotationSlotSeconds('0'), 5);
    assert.equal(controller._validRotationSlotSeconds('invalid'), 60);
    assert.equal(controller._validFallbackMode('mixed'), 'mixed');
    assert.equal(controller._labelForFallbackMode('mixed'), 'Mixed Rotation');
    console.log('Mixed rotation save, TOML round-trip, UI hydration, and validation passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
