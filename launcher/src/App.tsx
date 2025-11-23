import { useState, useEffect } from 'react';
import bgImage from './assets/installer_bg.png';

interface GameBuild {
  version: string;
  label: string;
  channel: string;
  windows: {
    url: string;
    size_bytes: number;
  }
}

function App() {
  const [version] = useState<string>('0.2.0'); // Launcher version
  const [manifest, setManifest] = useState<any>(null);
  const [installedVersions, setInstalledVersions] = useState<string[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<string | null>(null);
  const [status, setStatus] = useState<string>('Initializing...');
  const [progress, setProgress] = useState<number>(0);
  const [isBusy, setIsBusy] = useState<boolean>(false);

  useEffect(() => {
    // Listen for IPC messages
    window.api.receive('fromMain', (data: any) => {
      if (data.type === 'download-progress') {
        setProgress(data.percent);
      } else if (data.type === 'status') {
        setStatus(data.message);
      }
    });

    // Initial load
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setStatus('Checking installation...');
      const installed = await window.api.checkInstalledVersions();
      setInstalledVersions(installed);

      setStatus('Fetching manifest...');
      const data = await window.api.fetchManifest();
      setManifest(data);

      // Select latest version by default
      if (data && data.game_builds && data.game_builds.length > 0) {
        const latest = data.game_builds[data.game_builds.length - 1];
        setSelectedVersion(latest.version);
      }

      setStatus('Ready.');
    } catch (e) {
      setStatus('Error loading data.');
      console.error(e);
    }
  };

  const getBuildByVersion = (v: string): GameBuild | undefined => {
    return manifest?.game_builds?.find((b: GameBuild) => b.version === v);
  };

  const handleAction = async () => {
    if (!selectedVersion || !manifest) return;
    const build = getBuildByVersion(selectedVersion);
    if (!build) return;

    setIsBusy(true);
    setProgress(0);

    try {
      // 1. Check/Install GZDoom (Shared)
      setStatus("Checking GZDoom...");
      await window.api.downloadGZDoom();

      // 2. Install Game if needed
      if (!installedVersions.includes(selectedVersion)) {
        setStatus(`Downloading v${selectedVersion}...`);
        await window.api.downloadGame(build.windows.url, selectedVersion);

        // Refresh installed list
        const installed = await window.api.checkInstalledVersions();
        setInstalledVersions(installed);
      }

      // 3. Check IWAD
      const hasIwad = await window.api.checkIWAD();
      if (!hasIwad) {
        setStatus("Error: Missing DOOM2.WAD in game folder.");
        setIsBusy(false);
        return;
      }

      // 4. Launch
      setStatus("Launching...");
      await window.api.launchGame({ version: selectedVersion });
      setStatus("Game running...");

      // Reset after a bit
      setTimeout(() => {
        setStatus("Ready.");
        setIsBusy(false);
      }, 3000);

    } catch (e) {
      setStatus('Error occurred.');
      console.error(e);
      setIsBusy(false);
    }
  };

  const isInstalled = (v: string) => installedVersions.includes(v);

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center text-white bg-cover bg-center bg-no-repeat font-sans select-none"
      style={{ backgroundImage: `url(${bgImage})` }}
    >
      <div className="absolute inset-0 bg-black/60 z-0"></div>

      <div className="relative z-10 w-full max-w-2xl p-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-6xl font-black tracking-tighter text-red-600 drop-shadow-[0_4px_4px_rgba(0,0,0,1)]">
            MAXIMUM SECURITY
          </h1>
          <div className="h-1 w-full bg-gradient-to-r from-transparent via-red-600 to-transparent my-4 opacity-50"></div>
          <p className="text-gray-400 tracking-widest text-sm">LAUNCHER V{version}</p>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

          {/* Left Col: Build List */}
          <div className="bg-black/40 border border-white/10 rounded-lg p-4 backdrop-blur-sm h-[300px] overflow-y-auto custom-scrollbar">
            <h3 className="text-gray-400 text-xs uppercase tracking-wider mb-3 font-bold">Select Version</h3>
            <div className="space-y-2">
              {manifest?.game_builds?.slice().reverse().map((build: GameBuild) => (
                <div
                  key={build.version}
                  onClick={() => !isBusy && setSelectedVersion(build.version)}
                  className={`p-3 rounded border cursor-pointer transition-all ${
                    selectedVersion === build.version
                      ? 'bg-red-900/40 border-red-500 text-white'
                      : 'bg-black/20 border-white/5 text-gray-400 hover:bg-white/5'
                  } ${isBusy ? 'opacity-50 pointer-events-none' : ''}`}
                >
                  <div className="flex justify-between items-center">
                    <span className="font-bold">{build.label}</span>
                    {isInstalled(build.version) ? (
                      <span className="text-xs bg-emerald-900/50 text-emerald-400 px-2 py-1 rounded border border-emerald-800">INSTALLED</span>
                    ) : (
                      <span className="text-xs text-gray-600">NOT INSTALLED</span>
                    )}
                  </div>
                  <div className="text-xs mt-1 opacity-70 font-mono">v{build.version}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Right Col: Info & Action */}
          <div className="flex flex-col justify-between bg-black/40 border border-white/10 rounded-lg p-6 backdrop-blur-sm">

            <div>
              <h3 className="text-gray-400 text-xs uppercase tracking-wider mb-3 font-bold">Status</h3>
              <div className="bg-black/40 rounded p-3 border border-white/5 font-mono text-sm text-emerald-400 mb-4 h-[80px] overflow-hidden relative">
                 <div className="absolute inset-0 p-3">
                   &gt; {status}
                 </div>
              </div>

               {/* Progress Bar */}
               {isBusy && progress > 0 && (
                <div className="mb-4">
                   <div className="w-full bg-gray-800 rounded-full h-2">
                     <div className="bg-red-600 h-2 rounded-full transition-all duration-300" style={{ width: `${progress}%` }}></div>
                   </div>
                   <p className="text-right text-xs text-gray-500 mt-1 font-mono">{progress}%</p>
                </div>
              )}
            </div>

            <div>
              {selectedVersion && (
                <button
                  onClick={handleAction}
                  disabled={isBusy}
                  className={`w-full py-4 font-bold text-lg uppercase tracking-widest transition-all rounded shadow-lg border ${
                    isInstalled(selectedVersion)
                      ? 'bg-emerald-700 hover:bg-emerald-600 border-emerald-500 text-white hover:shadow-emerald-900/20'
                      : 'bg-red-700 hover:bg-red-600 border-red-500 text-white hover:shadow-red-900/20'
                  } ${isBusy ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  {isBusy ? 'Working...' : (isInstalled(selectedVersion) ? 'LAUNCH GAME' : 'INSTALL & PLAY')}
                </button>
              )}

              <div className="mt-4 text-center text-xs text-gray-600 font-mono">
                {selectedVersion && getBuildByVersion(selectedVersion)?.windows.size_bytes
                  ? `SIZE: ${(getBuildByVersion(selectedVersion)!.windows.size_bytes / 1024 / 1024).toFixed(1)} MB`
                  : 'SELECT A VERSION'}
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}

export default App
