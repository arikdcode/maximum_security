import { useState, useEffect } from 'react';
import bgImage from './assets/installer_bg.png';

function App() {
  const [version] = useState<string>('0.1.0'); // Launcher version
  const [manifest, setManifest] = useState<any>(null);
  const [gameStatus, setGameStatus] = useState<string>('idle'); // idle, downloading, installed
  const [progress, setProgress] = useState<number>(0);
  const [log, setLog] = useState<string>('Initializing...');

  useEffect(() => {
    // Listen for IPC messages
    window.api.receive('fromMain', (data: any) => {
      if (data.type === 'download-progress') {
        setProgress(data.percent);
        setGameStatus('downloading');
      } else if (data.type === 'status') {
        setLog(data.message);
      }
    });

    // Fetch manifest on load
    loadManifest();
  }, []);

  const loadManifest = async () => {
    try {
      setLog('Fetching manifest...');
      const data = await window.api.fetchManifest();
      setManifest(data);
      setLog('Manifest loaded.');
      // Here we would verify if game is installed
    } catch (e) {
      setLog('Failed to load manifest.');
      console.error(e);
    }
  };

  const installGame = async () => {
    if (!manifest || !manifest.game_builds || manifest.game_builds.length === 0) {
      setLog('No game builds found.');
      return;
    }

    const latest = manifest.game_builds[manifest.game_builds.length - 1];
    const url = latest.windows.url; // Assume windows for now

    setLog(`Downloading game v${latest.version}...`);
    setGameStatus('downloading');

    try {
      // 1. Download Game
      await window.api.downloadGame(url, latest.version);

      // 2. Setup GZDoom
      setLog("Checking GZDoom...");
      await window.api.downloadGZDoom();

      setGameStatus('installed');
      setLog('Ready to play.');
    } catch (e) {
      setLog('Installation failed.');
      setGameStatus('error');
      console.error(e);
    }
  };

  const launchGame = async () => {
    if (!manifest) return;
    const latest = manifest.game_builds[manifest.game_builds.length - 1];
    setLog("Launching...");
    try {
      await window.api.launchGame({ version: latest.version });
      // Maybe close launcher?
    } catch (e) {
      setLog("Launch failed.");
      console.error(e);
    }
  };

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center text-white bg-cover bg-center bg-no-repeat font-sans"
      style={{ backgroundImage: `url(${bgImage})` }}
    >
      <div className="absolute inset-0 bg-black/50 z-0"></div>

      <div className="relative z-10 text-center p-8 rounded-lg border border-white/10 bg-black/60 backdrop-blur-sm max-w-md w-full shadow-2xl">
        <h1 className="text-5xl font-extrabold mb-2 tracking-wider text-red-600 drop-shadow-[0_2px_2px_rgba(0,0,0,0.8)]">
          MAXIMUM SECURITY
        </h1>

        <div className="w-full h-px bg-gradient-to-r from-transparent via-red-600 to-transparent my-6 opacity-50"></div>

        <p className="text-gray-300 text-lg mb-4">
          LAUNCHER V{version}
        </p>

        {/* Status Display */}
        <div className="bg-black/40 rounded p-4 mb-6 border border-white/5 text-left font-mono text-sm min-h-[80px]">
           <p className="text-emerald-400">&gt; {log}</p>
        </div>

        {/* Progress Bar */}
        {gameStatus === 'downloading' && (
          <div className="mb-6">
             <div className="w-full bg-gray-800 rounded-full h-2.5 mb-1">
               <div className="bg-red-600 h-2.5 rounded-full transition-all duration-300" style={{ width: `${progress}%` }}></div>
             </div>
             <p className="text-right text-xs text-gray-400">{progress}%</p>
          </div>
        )}

        {/* Action Button */}
        <div className="space-y-4">
          {gameStatus === 'idle' && (
            <button
              onClick={installGame}
              className="w-full py-3 px-6 bg-red-700 hover:bg-red-600 text-white font-bold rounded border border-red-500 shadow-lg hover:shadow-red-900/20 transition-all uppercase tracking-widest"
            >
              Install Game
            </button>
          )}

          {gameStatus === 'installed' && (
            <button
              onClick={launchGame}
              className="w-full py-3 px-6 bg-emerald-700 hover:bg-emerald-600 text-white font-bold rounded border border-emerald-500 shadow-lg hover:shadow-emerald-900/20 transition-all uppercase tracking-widest"
            >
              Launch Game
            </button>
          )}
        </div>

        <div className="mt-10 pt-6 border-t border-white/10 text-xs text-gray-500 font-mono">
          SECURE CONNECTION // ENCRYPTED
        </div>
      </div>
    </div>
  )
}

export default App
