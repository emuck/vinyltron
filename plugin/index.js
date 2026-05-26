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

        uiconf.sections[0].content[0].value = self.config.get('brightness');
        var gamma = self.config.get('gamma');
        uiconf.sections[0].content[1].value = {value: gamma, label: gamma};
        uiconf.sections[0].content[2].value = self.config.get('progress_bar');
        uiconf.sections[0].content[3].value = self.config.get('format_badge');

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

ControllerVinyltron.prototype.saveConfig = function(data) {
    var self = this;

    var brightness = parseInt(data['brightness']);
    var gamma = data['gamma']['value'];
    var progress_bar = data['progress_bar'] === true || data['progress_bar'] === 'true';
    var format_badge = data['format_badge'] === true || data['format_badge'] === 'true';

    self.config.set('brightness', brightness);
    self.config.set('gamma', gamma);
    self.config.set('progress_bar', progress_bar);
    self.config.set('format_badge', format_badge);

    self._updateConfigToml(brightness, gamma, progress_bar, format_badge);

    exec('/usr/bin/sudo /bin/systemctl reload vinyltron', function(error) {
        if (error) self.logger.error('Vinyltron: reload failed: ' + error);
    });

    return libQ.resolve();
};

ControllerVinyltron.prototype._updateConfigToml = function(brightness, gamma, progress_bar, format_badge) {
    var self = this;
    try {
        var content = fs.readFileSync(CONFIG_TOML, 'utf8');
        content = content.replace(/^brightness\s*=.*/m,   'brightness = ' + brightness);
        content = content.replace(/^gamma\s*=.*/m,        'gamma = ' + gamma);
        content = content.replace(/^progress_bar\s*=.*/m, 'progress_bar = ' + progress_bar);
        content = content.replace(/^format_badge\s*=.*/m, 'format_badge = ' + format_badge);
        fs.writeFileSync(CONFIG_TOML, content, 'utf8');
    } catch (e) {
        self.logger.error('Vinyltron: failed to update config.toml: ' + e);
    }
};
