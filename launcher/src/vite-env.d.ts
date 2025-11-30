declare module "*.png" {
  const value: string;
  export default value;
}

interface Window {
  api: {
    fetchManifest: () => Promise<any>;
    downloadGame: (url: string, version: string) => Promise<any>;
    downloadGZDoom: () => Promise<any>;
    launchGame: (args: any) => Promise<any>;
    checkIWAD: () => Promise<boolean>;
    checkInstalledVersions: () => Promise<string[]>;
    getSaves: () => Promise<string[]>;
    getConfig: () => Promise<any>;
    saveConfig: (config: any) => Promise<any>;
    resetConfig: () => Promise<any>;
    uninstallGame: (version: string) => Promise<any>;
    receive: (channel: string, func: (...args: any[]) => void) => void;
    isDev: boolean;
  }
}
