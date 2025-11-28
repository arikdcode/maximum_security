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
  const [version] = useState<string>('0.3.0'); // Launcher version
  const [manifest, setManifest] = useState<any>(null);
  const [installedVersions, setInstalledVersions] = useState<string[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<string | null>(null);
  const [status, setStatus] = useState<string>('Initializing...');
  const [progress, setProgress] = useState<number>(0);
  const [isBusy, setIsBusy] = useState<boolean>(false);

  // New state for launch controls
  const [showLaunchControls, setShowLaunchControls] = useState<boolean>(false);
  const [saveFiles, setSaveFiles] = useState<string[]>([]);
  const [selectedSave, setSelectedSave] = useState<string | null>(null);
  const [difficulty, setDifficulty] = useState<number>(2); // 2 = Hurt me plenty (default)

  useEffect(() => {
    window.api.receive('fromMain', (data: any) => {
      if (data.type === 'download-progress') {
        setProgress(data.percent);
      } else if (data.type === 'status') {
        setStatus(data.message);
      }
    });
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

      if (data && data.game_builds && data.game_builds.length > 0) {
        const latest = data.game_builds[data.game_builds.length - 1];
        setSelectedVersion(latest.version);
      }

      // Load saves
      const saves = await window.api.getSaves();
      setSaveFiles(saves);

      setStatus('Ready.');
    } catch (e) {
      setStatus('Error loading data.');
      console.error(e);
    }
  };

  const getBuildByVersion = (v: string): GameBuild | undefined => {
    return manifest?.game_builds?.find((b: GameBuild) => b.version === v);
  };

  const installGame = async () => {
    if (!selectedVersion) return;
    const build = getBuildByVersion(selectedVersion);
    if (!build) return;

    setIsBusy(true);
    setProgress(0);

    // Mock mode disabled for real local testing
    /* if (window.api.isDev) {
      setStatus("DEV: Simulating install...");
      for (let i = 0; i <= 100; i += 5) {
        setProgress(i);
        await new Promise(r => setTimeout(r, 50));
      }
      setInstalledVersions(prev => [...prev, selectedVersion]);
      setStatus("DEV: Install complete.");
      setIsBusy(false);
      return;
    } */

    try {
      setStatus("Checking GZDoom...");
      await window.api.downloadGZDoom();

      setStatus(`Downloading v${selectedVersion}...`);
      await window.api.downloadGame(build.windows.url, selectedVersion);

      const installed = await window.api.checkInstalledVersions();
      setInstalledVersions(installed);

      setStatus("Ready.");
      setIsBusy(false);
    } catch (e) {
      setStatus('Installation failed.');
      console.error(e);
      setIsBusy(false);
    }
  };

  const launchGame = async (options: any = {}) => {
    if (!selectedVersion) return;
    setIsBusy(true);
    setStatus("Launching...");

    // Mock mode disabled for real local testing
    /* if (window.api.isDev) {
      setStatus(`DEV: Launching with options: ${JSON.stringify(options)}`);
      await new Promise(r => setTimeout(r, 2000));
      setStatus("DEV: Game running...");
      setIsBusy(false);
      return;
    } */

    try {
      // Skip the pre-check, let the main process handle it (it has recovery logic)
      /* const hasIwad = await window.api.checkIWAD();
      if (!hasIwad) {
        setStatus("Error: Missing DOOM2.WAD in game folder.");
        setIsBusy(false);
        return;
      } */

      await window.api.launchGame({
        version: selectedVersion,
        ...options
      });

      setStatus("Game running...");
      setTimeout(() => {
        setStatus("Ready.");
        setIsBusy(false);
      }, 3000);
    } catch (e) {
      setStatus('Launch failed.');
      console.error(e);
      setIsBusy(false);
    }
  };

  const isInstalled = (v: string) => installedVersions.includes(v);

  // Difficulty levels: 0=Baby, 1=Easy, 2=Normal, 3=Hard, 4=Nightmare
  const difficulties = [
    { val: 0, label: "I'm too young to die" },
    { val: 1, label: "Hey, not too rough" },
    { val: 2, label: "Hurt me plenty" },
    { val: 3, label: "Ultra-Violence" },
    { val: 4, label: "Nightmare!" },
  ];

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center text-white bg-cover bg-center bg-no-repeat font-sans select-none"
      style={{ backgroundImage: `url(${bgImage})` }}
    >
      <div className="absolute inset-0 bg-black/60 z-0"></div>

      <div className="relative z-10 w-full max-w-4xl p-8">
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

          {/* Left Col: Build List & Saves */}
          <div className="flex flex-col gap-4">
            {/* Version Selector */}
            <div className="bg-black/40 border border-white/10 rounded-lg p-4 backdrop-blur-sm h-[200px] overflow-y-auto custom-scrollbar">
              <h3 className="text-gray-400 text-xs uppercase tracking-wider mb-3 font-bold">Select Version</h3>
              <div className="space-y-2">
                {manifest?.game_builds?.slice().reverse().map((build: GameBuild) => (
                  <div
                    key={build.version}
                    onClick={() => {
                      if (!isBusy) {
                        setSelectedVersion(build.version);
                        setShowLaunchControls(false);
                      }
                    }}
                    className={`relative overflow-hidden group p-3 border cursor-pointer transition-all duration-300 ${
                      selectedVersion === build.version
                        ? 'bg-zinc-800 border-red-800 shadow-[0_0_15px_rgba(139,0,0,0.3)]'
                        : 'bg-black/40 border-white/5 hover:border-red-900/50 hover:bg-black/60'
                    } ${isBusy ? 'opacity-50 pointer-events-none' : ''}`}
                  >
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

            {/* Status Panel moved to left bottom */}
            <div className="bg-black/60 border border-white/10 rounded-sm p-4 backdrop-blur-md shadow-2xl relative overflow-hidden">
               <h3 className="text-gray-500 text-[10px] uppercase tracking-[0.2em] mb-2 font-bold border-b border-white/5 pb-1">System Status</h3>
               <div className="bg-black/80 border border-white/10 p-3 font-mono text-xs text-red-500/90 h-[60px] overflow-hidden relative shadow-inner mb-2">
                  <div className="absolute inset-0 p-3 typing-effect">
                    <span className="opacity-50 mr-2">&gt;</span>{status}<span className="animate-pulse">_</span>
                  </div>
               </div>
               {isBusy && progress > 0 && (
                 <div className="w-full h-4 bg-black/80 border border-white/10 relative overflow-hidden rounded-sm shadow-inner">
                   <div className="absolute inset-0 chain-pattern-cold"></div>
                   <div
                      className="absolute inset-0 chain-pattern-hot transition-all duration-300 border-r-2 border-yellow-500"
                      style={{ width: `${progress}%` }}
                   ></div>
                 </div>
               )}
            </div>
          </div>

          {/* Right Col: Action Panel */}
          <div className="flex flex-col bg-black/60 border border-white/10 rounded-lg p-6 backdrop-blur-sm h-[450px]">
            {selectedVersion && isInstalled(selectedVersion) ? (
              <>
                {!showLaunchControls ? (
                  <div className="flex flex-col justify-center h-full space-y-4">
                    <div className="text-center mb-4">
                      <h2 className="text-2xl font-black text-red-600 uppercase tracking-widest">Ready to Deploy</h2>
                      <p className="text-gray-400 text-sm mt-2">Security clearance granted.</p>
                    </div>

                    <button
                      onClick={() => setShowLaunchControls(true)}
                      disabled={isBusy}
                      className="w-full py-6 font-black text-2xl uppercase tracking-[0.2em] transition-all duration-300 border relative overflow-hidden group bg-gradient-to-b from-red-900 to-black border-red-700 text-red-500 hover:text-red-400 hover:border-red-500 shadow-[0_0_20px_rgba(139,0,0,0.3)]"
                    >
                      <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/diagmonds-light.png')] opacity-10"></div>
                      <span className="relative z-10 drop-shadow-md">ACCESS TERMINAL</span>
                    </button>
                  </div>
                ) : (
                  <div className="flex flex-col h-full">
                    <div className="flex justify-between items-center mb-4 border-b border-white/10 pb-2">
                      <h3 className="text-red-500 text-sm uppercase tracking-widest font-bold">Launch Protocols</h3>
                      <button
                        onClick={() => setShowLaunchControls(false)}
                        className="text-xs text-gray-500 hover:text-white uppercase"
                      >
                        [ Close ]
                      </button>
                    </div>

                    <div className="grid grid-cols-1 gap-3 overflow-y-auto pr-2 custom-scrollbar flex-grow">

                      {/* Continue (Latest Save) */}
                      {saveFiles.length > 0 && (
                        <button
                          onClick={() => launchGame({ saveGame: saveFiles[0] })}
                          className="p-4 border border-emerald-900/50 bg-emerald-900/10 hover:bg-emerald-900/30 text-left group transition-all"
                        >
                          <div className="text-emerald-500 font-bold uppercase tracking-wider group-hover:text-emerald-400">Resume Operations</div>
                          <div className="text-xs text-gray-500 font-mono mt-1">Last Save: {saveFiles[0]}</div>
                        </button>
                      )}

                      {/* New Game */}
                      <div className="p-4 border border-white/10 bg-white/5">
                        <div className="text-red-500 font-bold uppercase tracking-wider mb-3">New Assignment</div>
                        <div className="space-y-2">
                          <select
                            value={difficulty}
                            onChange={(e) => setDifficulty(parseInt(e.target.value))}
                            className="w-full bg-black border border-white/20 text-gray-300 text-sm p-2 focus:outline-none focus:border-red-500 font-mono"
                          >
                            {difficulties.map(d => (
                              <option key={d.val} value={d.val}>{d.label}</option>
                            ))}
                          </select>
                          <button
                            onClick={() => launchGame({ difficulty, quickStart: true })}
                            className="w-full py-2 bg-red-900/50 hover:bg-red-800/50 border border-red-800 text-red-200 text-xs uppercase tracking-widest transition-all"
                          >
                            Start New Game
                          </button>
                        </div>
                      </div>

                      {/* Load Save */}
                      <div className="p-4 border border-white/10 bg-white/5">
                        <div className="text-gray-400 font-bold uppercase tracking-wider mb-3">Load Record</div>
                        {saveFiles.length === 0 ? (
                          <div className="text-xs text-gray-600 italic">No records found.</div>
                        ) : (
                          <div className="space-y-2">
                            <select
                              onChange={(e) => setSelectedSave(e.target.value)}
                              className="w-full bg-black border border-white/20 text-gray-300 text-sm p-2 focus:outline-none focus:border-white/40 font-mono"
                            >
                              <option value="">Select a save...</option>
                              {saveFiles.map(s => (
                                <option key={s} value={s}>{s}</option>
                              ))}
                            </select>
                            <button
                              onClick={() => selectedSave && launchGame({ saveGame: selectedSave })}
                              disabled={!selectedSave}
                              className={`w-full py-2 border text-xs uppercase tracking-widest transition-all ${selectedSave ? 'bg-white/10 hover:bg-white/20 border-white/30 text-white' : 'bg-black border-white/5 text-gray-600 cursor-not-allowed'}`}
                            >
                              Load Selected
                            </button>
                          </div>
                        )}
                      </div>

                      {/* Normal Start */}
                      <button
                        onClick={() => launchGame()}
                        className="p-3 border border-white/5 hover:border-white/20 text-gray-500 hover:text-white text-xs uppercase tracking-widest transition-all"
                      >
                        Access Main Menu (Standard Boot)
                      </button>

                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="flex flex-col justify-center h-full items-center text-center">
                {selectedVersion ? (
                  <>
                    <div className="mb-6">
                      <h2 className="text-xl font-bold text-gray-300 uppercase tracking-widest">Update Required</h2>
                      <p className="text-gray-500 text-sm mt-2">Local files missing or outdated.</p>
                      <p className="text-gray-600 text-xs mt-1 font-mono">
                        {getBuildByVersion(selectedVersion)?.windows.size_bytes
                          ? `DOWNLOAD SIZE: ${(getBuildByVersion(selectedVersion)!.windows.size_bytes / 1024 / 1024).toFixed(1)} MB`
                          : 'SIZE UNKNOWN'}
                      </p>
                    </div>
                    <button
                      onClick={installGame}
                      disabled={isBusy}
                      className={`px-8 py-4 font-bold text-lg uppercase tracking-widest transition-all rounded shadow-lg border bg-zinc-800 border-zinc-600 text-white hover:bg-zinc-700 ${isBusy ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      {isBusy ? 'INSTALLING...' : 'DOWNLOAD & INSTALL'}
                    </button>
                  </>
                ) : (
                  <div className="text-gray-600 uppercase tracking-widest text-sm">Select a version to proceed</div>
                )}
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  )
}

export default App
