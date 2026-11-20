'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const root = path.resolve(__dirname, '..');
let files = {};
const sandbox = {
    module: {exports: {}}, __dirname: path.join(root, 'plugin'),
    require: name => name === 'fs-extra' ? {
        readFileSync(filename) {
            if (!(filename in files)) throw Error('missing');
            return files[filename];
        }
    } : name === 'kew' ? {} : require(name)
};
vm.runInNewContext(fs.readFileSync(path.join(root, 'plugin/index.js'), 'utf8'), sandbox);
const controller = new sandbox.module.exports({coreCommand: {}, logger: {}});
const rule = '/etc/modprobe.d/vinyltron-matrix.conf';
const state = '/data/configuration/user_interface/vinyltron/pwm-setup.json';
const report = '/run/vinyltron/pwm.json';
const boot = '/proc/sys/kernel/random/boot_id';
function fixture(mode, extra = {}) {
    files = {
        [rule]: 'blacklist snd_bcm2835\ninstall snd_bcm2835 /bin/false\n',
        [boot]: 'boot-one', '/proc/modules': '',
        '/proc/42/stat': '42 (python process) ' + ['S', ...Array(18).fill('0'), '1234'].join(' '),
        [report]: JSON.stringify({pid: 42, boot_id: 'boot-one', start_ticks: '1234', mode, reason: 'test', ...extra})
    };
}
fixture('hardware');
assert.match(controller._pwmStatusText(), /Hardware PWM active/);
fixture('hardware', {start_ticks: 'old-process'});
assert.match(controller._pwmStatusText(), /unavailable/);
fixture('hardware', {boot_id: 'old-boot'});
assert.match(controller._pwmStatusText(), /unavailable/);
fixture('software');
assert.match(controller._pwmStatusText(), /Software PWM active/);
fixture('waiting');
files['/proc/modules'] = 'snd_bcm2835 24576 3 - Live';
assert.match(controller._pwmStatusText(), /Reboot required/);
delete files[rule];
assert.match(controller._pwmStatusText(), /reinstall\/update/);
fixture('waiting');
assert.match(controller._pwmStatusText(), /Waiting for display initialization/);
files[state] = JSON.stringify({conflict: 'Onboard audio selected'});
assert.match(controller._pwmStatusText(), /Audio conflict: Onboard audio selected/);
fixture('waiting');
files[state] = JSON.stringify({changed: true, boot_id: 'boot-one'});
assert.match(controller._pwmStatusText(), /Reboot required/);
fixture('hardware');
delete files[rule];
assert.match(controller._pwmStatusText(), /protection missing/);
console.log('10 PWM status checks passed, including stale reports, conflicts, and reboot guidance.');
