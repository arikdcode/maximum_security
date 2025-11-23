const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  send: (channel, data) => {
    // whitelist channels
    let validChannels = ["toMain"];
    if (validChannels.includes(channel)) {
      ipcRenderer.send(channel, data);
    }
  },
  receive: (channel, func) => {
    let validChannels = ["fromMain"];
    if (validChannels.includes(channel)) {
      // Deliberately strip event as it includes `sender`
      ipcRenderer.on(channel, (event, ...args) => func(...args));
    }
  },

  // Dedicated methods
  fetchManifest: () => ipcRenderer.invoke('fetch-manifest'),
  downloadGame: (url, version) => ipcRenderer.invoke('download-game', url, version),
  downloadGZDoom: () => ipcRenderer.invoke('download-gzdoom'),
  launchGame: (args) => ipcRenderer.invoke('launch-game', args),
  checkIWAD: () => ipcRenderer.invoke('check-iwad'),
  checkInstalledVersions: () => ipcRenderer.invoke('check-installed-versions'),
});
