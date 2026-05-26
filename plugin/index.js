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

        // Display section
        var brightness = self.config.get('brightness').toString();
        s[0].content[0].value = {value: brightness, label: brightness + '%'};
        var gamma = self.config.get('gamma');
        s[0].content[1].value = {value: gamma, label: gamma};
        var rotation = self.config.get('rotation');
        s[0].content[2].value = {value: rotation, label: rotation + '°'};
        s[0].content[3].value = self.config.get('progress_bar');
        s[0].content[4].value = self.config.get('format_badge');

        // Power section
        s[1].content[0].value = self.config.get('display_on');

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

// Save display settings — requires service restart (rotation changes matrix geometry)
ControllerVinyltron.prototype.saveConfig = function(data) {
    var self = this;

    var brightness   = parseInt(data['brightness']['value']);
    var gamma        = data['gamma']['value'];
    var rotation     = data['rotation']['value'];
    var progress_bar = data['progress_bar'] === true || data['progress_bar'] === 'true';
    var format_badge = data['format_badge'] === true || data['format_badge'] === 'true';

    self.config.set('brightness', brightness);
    self.config.set('gamma', gamma);
    self.config.set('rotation', rotation);
    self.config.set('progress_bar', progress_bar);
    self.config.set('format_badge', format_badge);

    self._patchConfigToml({brightness: brightness, gamma: gamma, rotation: rotation,
                           progress_bar: progress_bar, format_badge: format_badge});

    exec('/usr/bin/sudo /bin/systemctl restart vinyltron', function(error) {
        if (error) self.logger.error('Vinyltron: restart failed: ' + error);
    });

    return libQ.resolve();
};

// Toggle display on/off — hot via SIGHUP, no restart needed
ControllerVinyltron.prototype.toggleDisplay = function(data) {
    var self = this;

    var display_on = data['display_on'] === true || data['display_on'] === 'true';
    self.config.set('display_on', display_on);
    self._patchConfigToml({display_on: display_on});

    exec('/usr/bin/sudo /bin/systemctl reload vinyltron', function(error) {
        if (error) self.logger.error('Vinyltron: reload failed: ' + error);
    });

    return libQ.resolve();
};

// Patch specific keys in config.toml without touching unmanaged values
ControllerVinyltron.prototype._patchConfigToml = function(fields) {
    var self = this;
    try {
        var content = fs.readFileSync(CONFIG_TOML, 'utf8');

        if (fields.brightness   !== undefined) content = content.replace(/^brightness\s*=.*/m,   'brightness = '   + fields.brightness);
        if (fields.gamma        !== undefined) content = content.replace(/^gamma\s*=.*/m,        'gamma = '        + fields.gamma);
        if (fields.rotation     !== undefined) content = content.replace(/^rotation\s*=.*/m,     'rotation = '     + parseInt(fields.rotation));
        if (fields.display_on   !== undefined) content = content.replace(/^display_on\s*=.*/m,   'display_on = '   + fields.display_on);
        if (fields.progress_bar !== undefined) content = content.replace(/^progress_bar\s*=.*/m, 'progress_bar = ' + fields.progress_bar);
        if (fields.format_badge !== undefined) content = content.replace(/^format_badge\s*=.*/m, 'format_badge = ' + fields.format_badge);

        fs.writeFileSync(CONFIG_TOML, content, 'utf8');
    } catch (e) {
        self.logger.error('Vinyltron: failed to update config.toml: ' + e);
    }
};
