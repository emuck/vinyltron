'use strict';

var libQ = require('kew');
var fs = require('fs-extra');
var exec = require('child_process').exec;
var path = require('path');

var CONFIG_TOML = '/data/configuration/user_interface/vinyltron/config.toml';
var BUNDLED_CONFIG_TOML = __dirname + '/vinyltron/config.toml';
var DEFAULT_IDLE_FOLDER = '/data/INTERNAL/Vinyltron/idle-images';
var IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'];
var SYSTEMCTL = '/usr/bin/sudo /bin/systemctl';

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
    this._ensureDaemonConfig();
    return libQ.resolve();
};

ControllerVinyltron.prototype.onStart = function() {
    return this._service('start', 'plugin start');
};

ControllerVinyltron.prototype.onStop = function() {
    return this._service('stop', 'plugin stop');
};

ControllerVinyltron.prototype.getAdditionalConf = function() {
    var self = this;
    var defer = libQ.defer();
    exec(SYSTEMCTL + ' is-active vinyltron', function(error, stdout) {
        defer.resolve({
            service_active: !error && stdout && stdout.trim() === 'active',
            config_path: CONFIG_TOML
        });
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

        // Section 1: Idle image
        var fallback_mode = self.config.get('fallback_mode') || 'single';
        var fallback_image_folder = self.config.get('fallback_image_folder') || DEFAULT_IDLE_FOLDER;
        var fallback_selected_image = self.config.get('fallback_selected_image') || '';
        var idle_options = self._idleImageOptions(fallback_image_folder);
        s[1].content[0].value = {value: fallback_mode, label: self._labelForFallbackMode(fallback_mode)};
        s[1].content[1].value = fallback_image_folder;
        s[1].content[2].options = idle_options;
        s[1].content[2].value = {
            value: fallback_selected_image,
            label: self._labelForIdleImage(fallback_selected_image, idle_options)
        };

        // Section 2: Hardware (rotation)
        var rotation = self.config.get('rotation');
        s[2].content[0].value = {value: rotation, label: rotation + '°'};

        // Section 3: Power (display_on)
        s[3].content[0].value = self.config.get('display_on');

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

ControllerVinyltron.prototype._ensureDaemonConfig = function() {
    try {
        if (fs.existsSync(CONFIG_TOML)) return;
        fs.ensureDirSync(path.dirname(CONFIG_TOML));
        fs.copySync(BUNDLED_CONFIG_TOML, CONFIG_TOML);
        this.logger.info('Vinyltron: created daemon config at ' + CONFIG_TOML);
    } catch (e) {
        this.logger.error('Vinyltron: failed to create daemon config: ' + e);
    }
};

ControllerVinyltron.prototype._service = function(action, reason) {
    var self = this;
    var defer = libQ.defer();
    var allowed = ['start', 'stop', 'restart', 'reload'];
    if (allowed.indexOf(action) === -1) {
        defer.reject(new Error('Unsupported service action: ' + action));
        return defer.promise;
    }

    exec(SYSTEMCTL + ' ' + action + ' vinyltron', function(error) {
        if (error) {
            self.logger.error('Vinyltron: service ' + action + ' failed after ' + reason + ': ' + error);
        } else {
            self.logger.info('Vinyltron: service ' + action + ' requested after ' + reason);
        }
        defer.resolve();
    });
    return defer.promise;
};

// Save idle image settings — hot via SIGHUP, no restart needed
ControllerVinyltron.prototype.saveIdle = function(data) {
    var self = this;

    var fallback_mode = data['fallback_mode'] ? data['fallback_mode']['value'] : 'single';
    var fallback_image_folder = data['fallback_image_folder'] && data['fallback_image_folder']['value'] !== undefined ? data['fallback_image_folder']['value'] : data['fallback_image_folder'];
    var fallback_selected_image = data['fallback_selected_image'] ? data['fallback_selected_image']['value'] : '';

    fallback_mode = self._validFallbackMode(fallback_mode);
    fallback_image_folder = fallback_image_folder || DEFAULT_IDLE_FOLDER;
    fallback_selected_image = self._sanitizeFilename(fallback_selected_image);

    fs.ensureDirSync(fallback_image_folder);

    self.config.set('fallback_mode', fallback_mode);
    self.config.set('fallback_image_folder', fallback_image_folder);
    self.config.set('fallback_selected_image', fallback_selected_image);

    self.logger.info('Vinyltron: saving idle settings: ' + JSON.stringify({
        fallback_mode: fallback_mode,
        fallback_image_folder: fallback_image_folder,
        fallback_selected_image: fallback_selected_image
    }));

    self._patchConfigToml({
        fallback_mode: fallback_mode,
        fallback_image_folder: fallback_image_folder,
        fallback_selected_image: fallback_selected_image
    });

    self._service('reload', 'idle settings save');

    return libQ.resolve();
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

    self._service('reload', 'display settings save');

    return libQ.resolve();
};

// Save hardware settings — requires service restart (rotation changes matrix geometry)
ControllerVinyltron.prototype.saveHardware = function(data) {
    var self = this;

    var rotation = data['rotation']['value'];
    self.config.set('rotation', rotation);
    self.logger.info('Vinyltron: saving hardware settings: ' + JSON.stringify({rotation: rotation}));
    self._patchConfigToml({rotation: rotation});

    self._service('restart', 'hardware settings save');

    return libQ.resolve();
};

// Toggle display on/off — hot via SIGHUP, no restart needed
ControllerVinyltron.prototype.toggleDisplay = function(data) {
    var self = this;

    var display_on = data['display_on'] === true || data['display_on'] === 'true';
    self.config.set('display_on', display_on);
    self.logger.info('Vinyltron: saving power setting: ' + JSON.stringify({display_on: display_on}));
    self._patchConfigToml({display_on: display_on});

    self._service('reload', 'power setting save');

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
        if (fields.fallback_image_folder !== undefined) content = this._patchTomlInSection(content, 'fallback', 'image_folder', this._tomlString(fields.fallback_image_folder), 'image');
        if (fields.fallback_mode !== undefined) content = this._patchTomlInSection(content, 'fallback', 'mode', this._tomlString(fields.fallback_mode), 'image_folder');
        if (fields.fallback_selected_image !== undefined) content = this._patchTomlInSection(content, 'fallback', 'selected_image', this._tomlString(fields.fallback_selected_image), 'mode');
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

ControllerVinyltron.prototype._idleImageOptions = function(folder) {
    var options = [];
    try {
        var files = fs.readdirSync(folder).filter(function(name) {
            var ext = path.extname(name).toLowerCase();
            return name[0] !== '.' && IMAGE_EXTENSIONS.indexOf(ext) !== -1 && fs.statSync(path.join(folder, name)).isFile();
        }).sort();
        options = files.map(function(name) {
            return {value: name, label: name};
        });
    } catch (e) {
        this.logger.warn('Vinyltron: could not scan idle image folder ' + folder + ': ' + e);
    }

    if (options.length === 0) {
        options.push({value: '', label: 'No image found'});
    }
    return options;
};

ControllerVinyltron.prototype._sanitizeFilename = function(value) {
    if (!value) return '';
    return path.basename(value.toString());
};

ControllerVinyltron.prototype._validFallbackMode = function(value) {
    if (value === 'selected' || value === 'random_folder') return value;
    return 'single';
};

ControllerVinyltron.prototype._labelForFallbackMode = function(value) {
    var labels = {
        'single': 'Built-in Idle Image',
        'selected': 'Selected Folder Image',
        'random_folder': 'Random Folder Image'
    };
    return labels[value] || labels['single'];
};

ControllerVinyltron.prototype._labelForIdleImage = function(value, options) {
    for (var i = 0; i < options.length; i++) {
        if (options[i].value === value) return options[i].label;
    }
    return value || 'No image found';
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
