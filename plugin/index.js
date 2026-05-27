'use strict';

var libQ = require('kew');
var fs = require('fs-extra');
var exec = require('child_process').exec;

var CONFIG_TOML = '/home/volumio/vinyltron/config.toml';

module.exports = ControllerVinyltron;

function ControllerVinyltron(context) {
    this.context = context;
    this.commandRouter = this.context.coreCommand;
    this.logger = this.context.logger;
    this.configManager = this.context.configManager;
}

ControllerVinyltron.prototype.onVolumioStart = function() {
    var configFile = this.commandRouter.pluginManager.getConfigurationFile(this.context, 'config.json');
    this.config = new (require('v-conf'))();
    this.config.loadFile(configFile);
    return libQ.resolve();
};

ControllerVinyltron.prototype.onStart = function() {
    var self = this;
    var defer = libQ.defer();
    exec('/usr/bin/sudo /bin/systemctl start vinyltron', function(error) {
        if (error) self.logger.error('Vinyltron: start failed: ' + error);
        defer.resolve();
    });
    return defer.promise;
};

ControllerVinyltron.prototype.onStop = function() {
    var self = this;
    var defer = libQ.defer();
    exec('/usr/bin/sudo /bin/systemctl stop vinyltron', function(error) {
        if (error) self.logger.error('Vinyltron: stop failed: ' + error);
        defer.resolve();
    });
    return defer.promise;
};

ControllerVinyltron.prototype.getUIConfig = function() {
    var defer = libQ.defer();
    var self = this;

    try {
        var uiconf = fs.readJsonSync(__dirname + '/UIConfig.json');
        var s = uiconf.sections;

        // Section 0: Display overlays and image tuning
        var brightness = self.config.get('brightness').toString();
        s[0].content[0].value = {value: brightness, label: brightness + '%'};
        var gamma = self.config.get('gamma');
        s[0].content[1].value = {value: gamma, label: gamma};
        var saved_progress_bar_height = self.config.get('progress_bar_height');
        var progress_bar_height = (saved_progress_bar_height === undefined || saved_progress_bar_height === null ? 0 : saved_progress_bar_height).toString();
        s[0].content[2].value = progress_bar_height;
        var progress_bar_foreground = self.config.get('progress_bar_foreground') || '255,255,255';
        s[0].content[3].value = {value: progress_bar_foreground, label: self._labelForProgressColor(progress_bar_foreground)};
        var progress_bar_background = self.config.get('progress_bar_background');
        if (progress_bar_background === undefined || progress_bar_background === null) progress_bar_background = '';
        s[0].content[4].value = {value: progress_bar_background, label: self._labelForProgressColor(progress_bar_background)};
        s[0].content[5].value = self.config.get('format_badge');
        var format_font = self.config.get('format_font') || 'tom_thumb';
        s[0].content[6].value = {value: format_font, label: self._labelForFormatFont(format_font)};
        var badge_duration = (self.config.get('badge_duration') || 10).toString();
        s[0].content[7].value = {value: badge_duration, label: badge_duration + ' seconds'};

        // Section 1: Hardware (rotation)
        var rotation = self.config.get('rotation');
        s[1].content[0].value = {value: rotation, label: rotation + '°'};

        // Section 2: Power (display_on)
        s[2].content[0].value = self.config.get('display_on');

        defer.resolve(uiconf);
    } catch (e) {
        self.logger.error('Vinyltron: getUIConfig failed: ' + e);
        defer.reject(new Error(e));
    }

    return defer.promise;
};

ControllerVinyltron.prototype.getConfigurationFiles = function() {
    return ['config.json'];
};

// Save display settings — hot via SIGHUP, no restart needed
ControllerVinyltron.prototype.saveDisplay = function(data) {
    var self = this;

    var brightness   = parseInt(data['brightness']['value']);
    var gamma        = data['gamma']['value'];
    var progress_bar_height_value = data['progress_bar_height'] && data['progress_bar_height']['value'] !== undefined ? data['progress_bar_height']['value'] : data['progress_bar_height'];
    var progress_bar_height = progress_bar_height_value !== undefined ? parseInt(progress_bar_height_value) : 0;
    var progress_bar_foreground = data['progress_bar_foreground'] ? data['progress_bar_foreground']['value'] : '255,255,255';
    var progress_bar_background = data['progress_bar_background'] ? data['progress_bar_background']['value'] : '';
    var format_badge = data['format_badge'] === true || data['format_badge'] === 'true';
    var format_font = data['format_font'] ? data['format_font']['value'] : 'tom_thumb';
    var badge_duration = data['badge_duration'] ? parseInt(data['badge_duration']['value']) : 10;
    if (isNaN(progress_bar_height)) progress_bar_height = 0;
    progress_bar_height = Math.max(0, Math.min(64, progress_bar_height));
    var progress_bar = progress_bar_height > 0;
    if (isNaN(badge_duration)) badge_duration = 10;

    self.config.set('brightness', brightness);
    self.config.set('gamma', gamma);
    self.config.set('progress_bar', progress_bar);
    self.config.set('progress_bar_height', progress_bar_height);
    self.config.set('progress_bar_foreground', progress_bar_foreground);
    self.config.set('progress_bar_background', progress_bar_background);
    self.config.set('format_badge', format_badge);
    self.config.set('format_font', format_font);
    self.config.set('badge_duration', badge_duration);

    self.logger.info('Vinyltron: saving display settings: ' + JSON.stringify({
        brightness: brightness,
        gamma: gamma,
        progress_bar: progress_bar,
        progress_bar_height: progress_bar_height,
        progress_bar_foreground: progress_bar_foreground,
        progress_bar_background: progress_bar_background,
        format_badge: format_badge,
        format_font: format_font,
        badge_duration: badge_duration
    }));

    self._patchConfigToml({brightness: brightness, gamma: gamma,
                           progress_bar: progress_bar,
                           progress_bar_height: progress_bar_height,
                           progress_bar_foreground: progress_bar_foreground,
                           progress_bar_background: progress_bar_background,
                           format_badge: format_badge,
                           format_font: format_font,
                           badge_duration: badge_duration});

    exec('/usr/bin/sudo /bin/systemctl reload vinyltron', function(error) {
        if (error) self.logger.error('Vinyltron: reload failed: ' + error);
        else self.logger.info('Vinyltron: reload requested after display settings save');
    });

    return libQ.resolve();
};

// Save hardware settings — requires service restart (rotation changes matrix geometry)
ControllerVinyltron.prototype.saveHardware = function(data) {
    var self = this;

    var rotation = data['rotation']['value'];
    self.config.set('rotation', rotation);
    self.logger.info('Vinyltron: saving hardware settings: ' + JSON.stringify({rotation: rotation}));
    self._patchConfigToml({rotation: rotation});

    exec('/usr/bin/sudo /bin/systemctl restart vinyltron', function(error) {
        if (error) self.logger.error('Vinyltron: restart failed: ' + error);
        else self.logger.info('Vinyltron: restart requested after hardware settings save');
    });

    return libQ.resolve();
};

// Toggle display on/off — hot via SIGHUP, no restart needed
ControllerVinyltron.prototype.toggleDisplay = function(data) {
    var self = this;

    var display_on = data['display_on'] === true || data['display_on'] === 'true';
    self.config.set('display_on', display_on);
    self.logger.info('Vinyltron: saving power setting: ' + JSON.stringify({display_on: display_on}));
    self._patchConfigToml({display_on: display_on});

    exec('/usr/bin/sudo /bin/systemctl reload vinyltron', function(error) {
        if (error) self.logger.error('Vinyltron: reload failed: ' + error);
        else self.logger.info('Vinyltron: reload requested after power setting save');
    });

    return libQ.resolve();
};

// Patch specific keys in config.toml without touching unmanaged values
ControllerVinyltron.prototype._patchConfigToml = function(fields) {
    var self = this;
    try {
        var content = fs.readFileSync(CONFIG_TOML, 'utf8');

        if (fields.brightness !== undefined) content = this._patchTomlInSection(content, 'display', 'brightness', fields.brightness);
        if (fields.gamma !== undefined) content = this._patchTomlInSection(content, 'display', 'gamma', fields.gamma);
        if (fields.rotation !== undefined) content = this._patchTomlInSection(content, 'display', 'rotation', parseInt(fields.rotation));
        if (fields.display_on !== undefined) content = this._patchTomlInSection(content, 'display', 'display_on', fields.display_on);
        if (fields.progress_bar !== undefined) content = this._patchTomlInSection(content, 'overlays', 'progress_bar', fields.progress_bar);
        if (fields.progress_bar_height !== undefined) content = this._patchTomlInSection(content, 'overlays', 'progress_bar_height', fields.progress_bar_height, 'progress_bar');
        if (fields.progress_bar_foreground !== undefined) content = this._patchTomlInSection(content, 'overlays', 'progress_bar_foreground', this._tomlRgb(fields.progress_bar_foreground), 'progress_bar_height');
        if (fields.progress_bar_background !== undefined) content = this._patchTomlInSection(content, 'overlays', 'progress_bar_background', this._tomlRgb(fields.progress_bar_background), 'progress_bar_foreground');
        if (fields.format_badge !== undefined) content = this._patchTomlInSection(content, 'overlays', 'format_badge', fields.format_badge, 'progress_bar_background');
        if (fields.format_font !== undefined) content = this._patchTomlInSection(content, 'overlays', 'format_font', this._tomlString(fields.format_font), 'format_badge');
        if (fields.badge_duration !== undefined) content = this._patchTomlInSection(content, 'overlays', 'badge_duration', fields.badge_duration, 'format_font');

        fs.writeFileSync(CONFIG_TOML, content, 'utf8');
        self.logger.info('Vinyltron: updated config.toml fields: ' + Object.keys(fields).join(', '));
    } catch (e) {
        self.logger.error('Vinyltron: failed to update config.toml: ' + e);
    }
};

ControllerVinyltron.prototype._patchTomlInSection = function(content, section, key, value, afterKey) {
    var line = key + ' = ' + value;
    var sectionRe = new RegExp('^\\[' + section + '\\]\\s*$', 'm');
    var sectionMatch = sectionRe.exec(content);
    if (!sectionMatch) {
        return content + '\n\n[' + section + ']\n' + line + '\n';
    }

    var sectionStart = sectionMatch.index;
    var bodyStart = sectionStart + sectionMatch[0].length;
    var nextSection = content.slice(bodyStart).search(/\n\[[^\]]+\]\s*/);
    var sectionEnd = nextSection === -1 ? content.length : bodyStart + nextSection;
    var before = content.slice(0, bodyStart);
    var body = content.slice(bodyStart, sectionEnd);
    var after = content.slice(sectionEnd);
    var keyRe = new RegExp('^(\\s*)' + key + '\\s*=.*$', 'm');

    if (keyRe.test(body)) {
        body = body.replace(keyRe, '$1' + line);
    } else if (afterKey) {
        var afterKeyRe = new RegExp('^(\\s*)' + afterKey + '\\s*=.*$', 'm');
        if (afterKeyRe.test(body)) {
            body = body.replace(afterKeyRe, function(afterLine) {
                return afterLine + '\n' + line;
            });
        } else {
            body += '\n' + line;
        }
    } else {
        body += '\n' + line;
    }

    return before + body + after;
};

ControllerVinyltron.prototype._tomlRgb = function(value) {
    if (value === undefined || value === null || value === '') return '[]';
    var parts = value.split(',').map(function(part) {
        var n = parseInt(part.trim());
        if (isNaN(n)) n = 0;
        return Math.max(0, Math.min(255, n));
    });
    while (parts.length < 3) parts.push(0);
    return '[' + parts.slice(0, 3).join(', ') + ']';
};

ControllerVinyltron.prototype._tomlString = function(value) {
    var text = (value === undefined || value === null) ? '' : value.toString();
    return '"' + text.replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '"';
};

ControllerVinyltron.prototype._labelForProgressColor = function(value) {
    var labels = {
        '': 'Album Art',
        '255,255,255': 'White',
        '255,160,0': 'Amber',
        '0,220,80': 'Green',
        '0,255,255': 'Cyan',
        '0,0,0': 'Black',
        '32,32,32': 'Dim Gray',
        '0,32,32': 'Deep Cyan',
        '32,20,0': 'Deep Amber'
    };
    return labels[value] || value;
};

ControllerVinyltron.prototype._labelForFormatFont = function(value) {
    var labels = {
        'tom_thumb': 'Tom Thumb',
        'tiny5': 'Tiny5',
        'spleen': 'Spleen 5x8'
    };
    return labels[value] || value;
};
