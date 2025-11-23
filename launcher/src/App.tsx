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
          <h1 className="text-7xl grimdark-text mb-2 transform scale-y-110">
            MAXIMUM SECURITY
          </h1>
          <div className="h-px w-full bg-gradient-to-r from-transparent via-red-900 to-transparent my-4 opacity-50 shadow-[0_0_10px_red]"></div>
          <p className="text-gray-500 tracking-[0.5em] text-xs font-mono uppercase">Prisoner Intake System v{version}</p>
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
                  className={`relative overflow-hidden group p-3 border cursor-pointer transition-all duration-300 ${
                    selectedVersion === build.version
                      ? 'bg-zinc-800 border-red-800 shadow-[0_0_15px_rgba(139,0,0,0.3)]'
                      : 'bg-black/40 border-white/5 hover:border-red-900/50 hover:bg-black/60'
                  } ${isBusy ? 'opacity-50 pointer-events-none' : ''}`}
                >
                  {/* Selection indicator strip */}
                  {selectedVersion === build.version && (
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-red-600 to-red-900"></div>
                  )}

                  <div className="flex justify-between items-center pl-2">
                    <span className={`font-bold tracking-wide ${selectedVersion === build.version ? 'text-white' : 'text-gray-300'}`}>{build.label}</span>
                    {isInstalled(build.version) ? (
                      <span className="text-[10px] bg-emerald-900/30 text-emerald-400 px-2 py-0.5 rounded border border-emerald-800/50 uppercase tracking-wider">Ready</span>
                    ) : (
                      <span className="text-[10px] text-gray-600 uppercase tracking-wider">Available</span>
                    )}
                  </div>
                  <div className="text-[10px] mt-1 opacity-50 font-mono text-gray-400">BUILD: v{build.version}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Right Col: Info & Action */}
          <div className="flex flex-col justify-between bg-black/60 border border-white/10 rounded-sm p-6 backdrop-blur-md shadow-2xl relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-white/10 to-transparent"></div>

            <div>
              <h3 className="text-gray-500 text-[10px] uppercase tracking-[0.2em] mb-3 font-bold border-b border-white/5 pb-1">System Status</h3>
              <div className="bg-black/80 border border-white/10 p-3 font-mono text-xs text-red-500/90 mb-6 h-[80px] overflow-hidden relative shadow-inner">
                 <div className="absolute inset-0 p-3 typing-effect">
                   <span className="opacity-50 mr-2">&gt;</span>{status}<span className="animate-pulse">_</span>
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
                  className={`w-full py-4 font-black text-xl uppercase tracking-[0.2em] transition-all duration-300 border relative overflow-hidden group ${
                    isInstalled(selectedVersion)
                      ? 'bg-gradient-to-b from-zinc-800 to-black border-zinc-600 text-emerald-500 hover:text-emerald-400 hover:border-emerald-500 shadow-[0_0_10px_rgba(0,0,0,0.5)]'
                      : 'bg-gradient-to-b from-red-900 to-black border-red-700 text-red-500 hover:text-red-400 hover:border-red-500 shadow-[0_0_20px_rgba(139,0,0,0.3)]'
                  } ${isBusy ? 'opacity-50 cursor-not-allowed grayscale' : ''}`}
                >
                  <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/diagmonds-light.png')] opacity-10"></div>
                  <span className="relative z-10 drop-shadow-md">
                    {isBusy ? 'WORKING...' : (isInstalled(selectedVersion) ? 'LAUNCH PROTOCOL' : 'INITIATE INSTALL')}
                  </span>
                </button>
              )}

              <div className="mt-4 text-center text-[10px] text-gray-600 font-mono tracking-widest">
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
