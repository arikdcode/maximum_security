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
    receive: (channel: string, func: (...args: any[]) => void) => void;
  }
}
